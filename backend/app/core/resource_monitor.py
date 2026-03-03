"""
Lightweight resource monitoring for pipeline benchmarking.

Provides RSS/CPU checkpoints with zero overhead when monitoring is unavailable.
Uses psutil when installed, falls back to /proc/self/status on Linux.
"""

from __future__ import annotations

from typing import Any

from app.core.logging import get_logger

logger = get_logger(__name__)

# Try to import psutil; if unavailable, all functions degrade gracefully
try:
    import psutil

    _HAS_PSUTIL = True
except ImportError:
    psutil = None  # type: ignore[assignment]
    _HAS_PSUTIL = False


def get_process_memory_mb() -> float | None:
    """Return current process RSS in MB.

    Uses psutil if available, falls back to parsing ``/proc/self/status``
    (works in Docker without psutil). Returns ``None`` if neither source
    is available.
    """
    if _HAS_PSUTIL:
        try:
            proc = psutil.Process()
            return float(proc.memory_info().rss) / (1024 * 1024)
        except Exception:
            pass

    # Fallback: parse /proc/self/status (Linux only)
    try:
        with open("/proc/self/status") as f:
            for line in f:
                if line.startswith("VmRSS:"):
                    # VmRSS is in kB
                    return int(line.split()[1]) / 1024
    except (FileNotFoundError, OSError, ValueError, IndexError):
        pass

    return None


def get_system_memory_mb() -> dict[str, float] | None:
    """Return system memory stats in MB.

    Returns ``{total_mb, available_mb, used_mb, percent}`` via psutil,
    or ``None`` if psutil is not installed.
    """
    if not _HAS_PSUTIL:
        return None

    try:
        mem = psutil.virtual_memory()
        return {
            "total_mb": mem.total / (1024 * 1024),
            "available_mb": mem.available / (1024 * 1024),
            "used_mb": mem.used / (1024 * 1024),
            "percent": mem.percent,
        }
    except Exception:
        return None


def log_resource_checkpoint(
    label: str,
    threshold_mb: float = 0,
    extra: dict[str, Any] | None = None,
) -> dict[str, Any] | None:
    """Log RSS and system memory at a named checkpoint.

    If RSS exceeds ``threshold_mb`` (and threshold_mb > 0), logs at WARNING.
    Returns the stats dict or ``None`` if monitoring is unavailable.

    This is a synchronous function safe to call from both sync and async contexts.
    """
    rss_mb = get_process_memory_mb()
    if rss_mb is None:
        return None

    stats: dict[str, Any] = {"label": label, "rss_mb": round(rss_mb, 1)}

    sys_mem = get_system_memory_mb()
    if sys_mem:
        stats["system_available_mb"] = round(sys_mem["available_mb"], 1)
        stats["system_percent"] = sys_mem["percent"]

    if extra:
        stats.update(extra)

    if threshold_mb > 0 and rss_mb > threshold_mb:
        logger.sync_warning(
            f"Resource checkpoint [{label}]: RSS {rss_mb:.1f} MB exceeds threshold {threshold_mb} MB",
            **stats,
        )
    else:
        logger.sync_info(f"Resource checkpoint [{label}]: RSS {rss_mb:.1f} MB", **stats)

    return stats
