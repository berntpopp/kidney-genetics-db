#!/usr/bin/env python3
"""
Pipeline resource benchmark script.

Monitors the uvicorn worker process while the annotation pipeline runs,
sampling RSS, VMS, CPU, and system memory every N seconds. Generates a
JSON report with per-source breakdown and VPS fitness assessment.

Requirements:
    - psutil (installed as dev dependency)
    - Running backend (make backend)
    - Admin credentials (env vars ADMIN_USERNAME / ADMIN_PASSWORD or .env)

Usage:
    cd backend && uv run python scripts/benchmark_pipeline.py
    cd backend && uv run python scripts/benchmark_pipeline.py --clear-cache --threshold-mb 3500
"""

from __future__ import annotations

import argparse
import json
import os
import shutil
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

try:
    import httpx
except ImportError:
    print("ERROR: httpx is required. Run: uv sync --group dev")
    sys.exit(1)

try:
    import psutil
except ImportError:
    print("ERROR: psutil is required. Run: uv sync --group dev")
    sys.exit(1)


def find_uvicorn_worker() -> psutil.Process | None:
    """Find the uvicorn worker process serving our app.

    Prefers the actual Python uvicorn worker over the ``uv run`` wrapper
    by selecting the candidate with the highest RSS (the wrapper is tiny).
    """
    candidates: list[psutil.Process] = []
    for proc in psutil.process_iter(["pid", "name", "cmdline"]):
        try:
            cmdline = proc.info.get("cmdline") or []
            cmdline_str = " ".join(cmdline)
            if "uvicorn" in cmdline_str and "app.main:app" in cmdline_str:
                candidates.append(proc)
        except (psutil.NoSuchProcess, psutil.AccessDenied):
            continue

    if not candidates:
        return None

    # Pick the process with the largest RSS (the real worker, not the uv wrapper)
    best = max(candidates, key=lambda p: _safe_rss(p))
    return best


def _safe_rss(proc: psutil.Process) -> int:
    """Return RSS in bytes, or 0 on error."""
    try:
        return int(proc.memory_info().rss)
    except (psutil.NoSuchProcess, psutil.AccessDenied):
        return 0


def get_auth_token(api_url: str, username: str, password: str) -> str:
    """Authenticate and return Bearer token."""
    resp = httpx.post(
        f"{api_url}/api/auth/login",
        data={"username": username, "password": password},
        timeout=60,
    )
    if resp.status_code != 200:
        print(f"ERROR: Login failed ({resp.status_code}): {resp.text}")
        sys.exit(1)
    return str(resp.json()["access_token"])


def trigger_pipeline(
    api_url: str,
    token: str,
    strategy: str = "full",
    sources: list[str] | None = None,
    force: bool = True,
) -> dict:
    """Trigger the annotation pipeline via the API."""
    params: dict[str, str | bool | list[str]] = {
        "strategy": strategy,
        "force": force,
    }
    if sources:
        params["sources"] = sources

    resp = httpx.post(
        f"{api_url}/api/annotations/pipeline/update",
        params=params,
        headers={"Authorization": f"Bearer {token}"},
        timeout=60,
    )
    if resp.status_code != 200:
        print(f"ERROR: Pipeline trigger failed ({resp.status_code}): {resp.text}")
        sys.exit(1)
    result: dict = resp.json()
    return result


def poll_pipeline_status(api_url: str) -> dict:
    """Get current pipeline status."""
    try:
        resp = httpx.get(f"{api_url}/api/annotations/pipeline/status", timeout=10)
        if resp.status_code == 200:
            result: dict = resp.json()
            return result
    except httpx.RequestError:
        pass
    return {}


def sample_process(proc: psutil.Process) -> dict | None:
    """Take a single resource sample from the worker process."""
    try:
        mem = proc.memory_info()
        cpu = proc.cpu_percent(interval=0)
        threads = proc.num_threads()
        sys_mem = psutil.virtual_memory()
        return {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "rss_mb": round(mem.rss / (1024 * 1024), 1),
            "vms_mb": round(mem.vms / (1024 * 1024), 1),
            "cpu_percent": round(cpu, 1),
            "num_threads": threads,
            "system_available_mb": round(sys_mem.available / (1024 * 1024), 1),
            "system_percent": sys_mem.percent,
        }
    except (psutil.NoSuchProcess, psutil.AccessDenied):
        return None


def get_disk_usage(base_dir: Path) -> dict[str, float]:
    """Get disk usage for pipeline cache directories in MB."""
    result = {}
    for subdir in ["data/bulk_cache", "data/string"]:
        path = base_dir / subdir
        if path.exists():
            total = sum(f.stat().st_size for f in path.rglob("*") if f.is_file())
            result[subdir] = round(total / (1024 * 1024), 1)
        else:
            result[subdir] = 0.0
    return result


def generate_report(
    samples: list[dict],
    source_timestamps: dict[str, dict],
    start_time: float,
    end_time: float,
    disk_usage: dict[str, float],
    threshold_mb: float,
) -> dict:
    """Generate the final benchmark report."""
    if not samples:
        return {"error": "No samples collected"}

    rss_values = [s["rss_mb"] for s in samples]
    vms_values = [s["vms_mb"] for s in samples]
    cpu_values = [s["cpu_percent"] for s in samples]
    avail_values = [s["system_available_mb"] for s in samples]
    thread_values = [s["num_threads"] for s in samples]

    duration_s = end_time - start_time
    peak_rss = max(rss_values)
    peak_vms = max(vms_values)
    min_available = min(avail_values)
    avg_cpu = round(sum(cpu_values) / len(cpu_values), 1)
    max_threads = max(thread_values)

    # Per-source breakdown (estimate from timeline)
    per_source = {}
    for source_name, ts_info in source_timestamps.items():
        source_start = ts_info.get("start_time")
        source_end = ts_info.get("end_time")
        if source_start and source_end:
            window_samples = [
                s for s in samples if source_start <= _iso_to_epoch(s["timestamp"]) <= source_end
            ]
            if window_samples:
                src_rss = [s["rss_mb"] for s in window_samples]
                per_source[source_name] = {
                    "peak_rss_mb": max(src_rss),
                    "rss_delta_mb": round(max(src_rss) - min(src_rss), 1),
                    "duration_s": round(source_end - source_start, 1),
                    "samples": len(window_samples),
                }

    # Warnings
    warnings = []
    if peak_rss > threshold_mb:
        warnings.append(f"Peak RSS ({peak_rss:.1f} MB) exceeds threshold ({threshold_mb} MB)")
    if min_available < 500:
        warnings.append(f"System available memory dropped to {min_available:.1f} MB (< 500 MB)")

    # VPS fitness assessment
    vps_8gb_budget_mb = 4000  # Backend gets ~4 GB on 8 GB VPS
    if peak_rss < vps_8gb_budget_mb * 0.7:
        fitness = "GOOD - well within 8-GB VPS budget"
    elif peak_rss < vps_8gb_budget_mb * 0.9:
        fitness = "MARGINAL - close to 8-GB VPS budget, monitor closely"
    else:
        fitness = "OVER BUDGET - exceeds safe limits for 8-GB VPS"

    return {
        "benchmark_version": "1.0",
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "summary": {
            "total_duration_s": round(duration_s, 1),
            "peak_rss_mb": peak_rss,
            "peak_vms_mb": peak_vms,
            "min_system_available_mb": min_available,
            "avg_cpu_percent": avg_cpu,
            "max_threads": max_threads,
            "total_samples": len(samples),
        },
        "per_source": per_source,
        "disk_usage_mb": disk_usage,
        "warnings": warnings,
        "vps_fitness": fitness,
        "threshold_mb": threshold_mb,
    }


def _iso_to_epoch(iso_str: str) -> float:
    """Convert ISO timestamp to epoch seconds."""
    dt = datetime.fromisoformat(iso_str.replace("Z", "+00:00"))
    return dt.timestamp()


def load_env_file(env_path: Path) -> dict[str, str]:
    """Load variables from a .env file."""
    env_vars: dict[str, str] = {}
    if not env_path.exists():
        return env_vars
    with open(env_path) as f:
        for line in f:
            line = line.strip()
            if not line or line.startswith("#") or "=" not in line:
                continue
            key, _, value = line.partition("=")
            # Strip surrounding quotes
            value = value.strip().strip("'\"")
            env_vars[key.strip()] = value
    return env_vars


def main() -> None:
    parser = argparse.ArgumentParser(description="Benchmark the annotation pipeline")
    parser.add_argument("--api-url", default="http://localhost:8000", help="Backend API base URL")
    parser.add_argument("--strategy", default="full", help="Pipeline strategy (default: full)")
    parser.add_argument(
        "--sources",
        nargs="*",
        default=None,
        help="Specific sources to run (default: all)",
    )
    parser.add_argument(
        "--clear-cache",
        action="store_true",
        help="Delete bulk_cache/ before running (simulates first run)",
    )
    parser.add_argument(
        "--threshold-mb",
        type=float,
        default=3500,
        help="RSS warning threshold in MB (default: 3500)",
    )
    parser.add_argument(
        "--interval",
        type=float,
        default=1.0,
        help="Sampling interval in seconds (default: 1)",
    )
    parser.add_argument(
        "--output",
        default=None,
        help="Output JSON file path (default: benchmark_report.json)",
    )
    parser.add_argument(
        "--force",
        action="store_true",
        default=True,
        help="Force pipeline update (default: true)",
    )
    args = parser.parse_args()

    backend_dir = Path(__file__).resolve().parent.parent
    output_path = Path(args.output) if args.output else backend_dir / "benchmark_report.json"

    # Load credentials from env vars or .env file
    env_file = load_env_file(backend_dir / ".env")
    username = os.environ.get("ADMIN_USERNAME") or env_file.get("ADMIN_USERNAME", "admin")
    password = os.environ.get("ADMIN_PASSWORD") or env_file.get("ADMIN_PASSWORD", "")

    if not password:
        print("ERROR: Set ADMIN_PASSWORD env var or add it to backend/.env")
        sys.exit(1)

    # Optional: clear cache
    if args.clear_cache:
        cache_dir = backend_dir / "data" / "bulk_cache"
        if cache_dir.exists():
            print(f"Clearing {cache_dir} ...")
            shutil.rmtree(cache_dir)
            print("  Cleared.")

    # Find uvicorn worker
    print("Looking for uvicorn worker process...")
    worker = find_uvicorn_worker()
    if not worker:
        print("ERROR: No uvicorn worker found. Is the backend running? (make backend)")
        sys.exit(1)
    print(f"  Found worker PID {worker.pid}")

    # Warm up cpu_percent (first call always returns 0)
    try:
        worker.cpu_percent(interval=0)
    except psutil.NoSuchProcess:
        print("ERROR: Worker process disappeared")
        sys.exit(1)

    # Authenticate
    print(f"Authenticating as '{username}' ...")
    token = get_auth_token(args.api_url, username, password)
    print("  Authenticated.")

    # Trigger pipeline
    print(f"Triggering pipeline (strategy={args.strategy}, force={args.force}) ...")
    trigger_resp = trigger_pipeline(args.api_url, token, args.strategy, args.sources, args.force)
    print(f"  Pipeline triggered: {trigger_resp.get('message', trigger_resp)}")

    # Record source update timestamps at start
    initial_status = poll_pipeline_status(args.api_url)
    source_last_update: dict[str, str | None] = {}
    for src in initial_status.get("sources", []):
        source_last_update[src["source"]] = src.get("last_update")

    # Monitoring loop
    print(f"Monitoring (interval={args.interval}s, threshold={args.threshold_mb} MB) ...")
    print("  Press Ctrl+C to stop early.\n")

    samples: list[dict] = []
    source_timestamps: dict[str, dict] = {}
    start_time = time.time()
    last_status_poll = 0.0
    status_poll_interval = 10.0
    completed_sources: set[str] = set()
    idle_since: float | None = None
    idle_threshold_s = 30.0  # Consider pipeline done if idle this long after activity

    try:
        while True:
            now = time.time()
            elapsed = now - start_time

            # Sample process
            sample = sample_process(worker)
            if sample is None:
                print("  Worker process gone — stopping.")
                break
            sample["elapsed_s"] = round(elapsed, 1)
            samples.append(sample)

            # Live output
            rss = sample["rss_mb"]
            marker = " *** OVER THRESHOLD" if rss > args.threshold_mb else ""
            sys.stdout.write(
                f"\r  [{elapsed:6.0f}s] RSS={rss:7.1f} MB  "
                f"CPU={sample['cpu_percent']:5.1f}%  "
                f"Avail={sample['system_available_mb']:7.0f} MB  "
                f"Threads={sample['num_threads']:3d}{marker}"
            )
            sys.stdout.flush()

            # Track idle state (CPU < 5% after at least one source completed)
            if completed_sources and sample["cpu_percent"] < 5.0:
                if idle_since is None:
                    idle_since = now
                elif now - idle_since >= idle_threshold_s:
                    print(
                        f"\n\n  Pipeline idle for {idle_threshold_s:.0f}s "
                        f"after {len(completed_sources)} sources — stopping."
                    )
                    break
            else:
                idle_since = None

            # Poll pipeline status periodically
            if now - last_status_poll >= status_poll_interval:
                last_status_poll = now
                status = poll_pipeline_status(args.api_url)
                for src in status.get("sources", []):
                    sname = src["source"]
                    new_ts = src.get("last_update")
                    old_ts = source_last_update.get(sname)

                    if new_ts and new_ts != old_ts and sname not in completed_sources:
                        completed_sources.add(sname)
                        end_epoch = now
                        # Record source end time
                        if sname not in source_timestamps:
                            source_timestamps[sname] = {"start_time": start_time}
                        source_timestamps[sname]["end_time"] = end_epoch
                        print(f"\n  Source '{sname}' completed at +{elapsed:.0f}s")

                # Check if all sources have been updated
                all_sources_in_status = {s["source"] for s in status.get("sources", [])}
                if all_sources_in_status and completed_sources >= all_sources_in_status:
                    print("\n\n  All sources completed!")
                    break

            time.sleep(args.interval)

    except KeyboardInterrupt:
        print("\n\n  Interrupted by user.")

    end_time = time.time()

    # Mark sources that never got a start time
    for sname in source_timestamps:
        if "start_time" not in source_timestamps[sname]:
            source_timestamps[sname]["start_time"] = start_time

    # Disk usage
    disk_usage = get_disk_usage(backend_dir)

    # Generate report
    print("\nGenerating report ...")
    report = generate_report(
        samples, source_timestamps, start_time, end_time, disk_usage, args.threshold_mb
    )

    # Write report
    with open(output_path, "w") as f:
        json.dump(report, f, indent=2)
    print(f"  Report written to: {output_path}")

    # Console summary
    s = report.get("summary", {})
    print("\n" + "=" * 60)
    print("  BENCHMARK SUMMARY")
    print("=" * 60)
    print(f"  Duration:            {s.get('total_duration_s', 0):,.1f} s")
    print(f"  Peak RSS:            {s.get('peak_rss_mb', 0):,.1f} MB")
    print(f"  Peak VMS:            {s.get('peak_vms_mb', 0):,.1f} MB")
    print(f"  Min Sys Available:   {s.get('min_system_available_mb', 0):,.1f} MB")
    print(f"  Avg CPU:             {s.get('avg_cpu_percent', 0):.1f}%")
    print(f"  Max Threads:         {s.get('max_threads', 0)}")
    print(f"  Samples:             {s.get('total_samples', 0)}")
    print()

    if report.get("per_source"):
        print("  Per-Source Breakdown:")
        for sname, info in report["per_source"].items():
            print(
                f"    {sname:20s}  peak={info['peak_rss_mb']:,.1f} MB  "
                f"delta={info['rss_delta_mb']:+,.1f} MB  "
                f"dur={info['duration_s']:.0f}s"
            )
        print()

    if report.get("disk_usage_mb"):
        print("  Disk Usage:")
        for path, mb in report["disk_usage_mb"].items():
            print(f"    {path:30s}  {mb:,.1f} MB")
        print()

    print(f"  VPS Fitness:  {report.get('vps_fitness', 'unknown')}")

    if report.get("warnings"):
        print()
        print("  WARNINGS:")
        for w in report["warnings"]:
            print(f"    - {w}")

    print("=" * 60)


if __name__ == "__main__":
    main()
