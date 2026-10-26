#!/usr/bin/env python3
"""ClinGen/GenCC circularity benchmark (#282). Read-only.

Recomputes gene_scores.percentage_score and evidence_tier (app/db/views.py,
materialized view ``gene_scores``) with ClinGen, GenCC or both excluded,
under two divisor policies:

- ``global``: production policy (#333) - divisor is the number of distinct
  sources in combined_evidence_scores, minus the excluded sources.
- ``per_gene``: divisor is the number of sources the gene itself has after
  exclusion (comparison only; not used in production).

The exclude-nothing/global run must reproduce the live gene_scores view for
every gene, or the script exits 1.

Usage:
    cd backend && uv run python scripts/benchmark_clingen_gencc.py \\
        [--database-url URL] [--out-dir DIR] [--label LABEL]
"""

from __future__ import annotations

import argparse
import csv
import os
import statistics
import sys
from collections import Counter, defaultdict
from pathlib import Path

import psycopg2

EPS = 1e-9  # abs tolerance on percentage_score (SQL vs Python float summation order)
TIERS = [
    "comprehensive_support",
    "multi_source_support",
    "established_support",
    "preliminary_evidence",
    "minimal_evidence",
    "no_evidence",
]
SCENARIOS = {
    "full": set(),
    "no_clingen": {"ClinGen"},
    "no_gencc": {"GenCC"},
    "no_clingen_gencc": {"ClinGen", "GenCC"},
}
POLICIES = ["global", "per_gene"]
HIGH = {"Definitive", "Strong"}

# Same CTE as gene_scores in app/db/views.py
SOURCE_SCORES_SQL = """
SELECT g.id, g.approved_symbol, g.hgnc_id, ces.source_name,
       MAX(ces.normalized_score) AS source_score
FROM genes g
INNER JOIN combined_evidence_scores ces ON g.id = ces.gene_id
GROUP BY g.id, g.approved_symbol, g.hgnc_id, ces.source_name
"""
CLASS_SQL = """
SELECT gene_id, source_name,
       COALESCE(evidence_data->'classifications', '[]'::jsonb),
       COALESCE(evidence_data->'submitters', '[]'::jsonb)
FROM gene_evidence WHERE source_name IN ('ClinGen', 'GenCC')
"""


def tier(source_count: int, pct: float) -> str:
    """Mirror of the evidence_tier CASE in gene_scores."""
    if source_count >= 4 and pct >= 50:
        return "comprehensive_support"
    if source_count >= 3 and pct >= 35:
        return "multi_source_support"
    if source_count >= 2 and pct >= 20:
        return "established_support"
    if pct >= 10:
        return "preliminary_evidence"
    if pct > 0:
        return "minimal_evidence"
    return "no_evidence"


def score(sources: dict[str, float], excluded: set[str], policy: str, n_global: int):
    kept = {s: v for s, v in sources.items() if s not in excluded}
    divisor = n_global - len(excluded) if policy == "global" else len(kept)
    pct = sum(kept.values()) / divisor * 100 if kept else 0.0
    return pct, tier(len(kept), pct)


def ranks(pcts: dict[int, float]) -> dict[int, int]:
    """Competition rank, highest score = 1, ties share the best rank."""
    out, prev, r = {}, None, 0
    for i, (gid, p) in enumerate(sorted(pcts.items(), key=lambda kv: -kv[1]), 1):
        if p != prev:
            r, prev = i, p
        out[gid] = r
    return out


def stratum(cls: dict[str, set[str]]) -> str:
    cg, gc = bool(cls.get("ClinGen", set()) & HIGH), bool(cls.get("GenCC", set()) & HIGH)
    if cg and gc:
        return "high_both"
    if cg:
        return "high_clingen_only"
    if gc:
        return "high_gencc_only"
    if cls:
        return "clingen_gencc_other"
    return "neither"


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--database-url", default=os.environ.get("DATABASE_URL"))
    ap.add_argument("--out-dir", type=Path, required=True)
    ap.add_argument("--label", required=True, help="e.g. dev_snapshot_2026-10-26")
    args = ap.parse_args()
    if not args.database_url:
        ap.error("pass --database-url or set DATABASE_URL")
    url = args.database_url.replace("postgresql+psycopg2://", "postgresql://")

    conn = psycopg2.connect(url)
    conn.set_session(readonly=True)
    with conn, conn.cursor() as cur:
        cur.execute("SELECT DISTINCT source_name FROM combined_evidence_scores")
        present = {r[0] for r in cur.fetchall()}
        n_global = len(present)
        cur.execute(SOURCE_SCORES_SQL)
        genes: dict[int, dict] = {}
        for gid, sym, hgnc, src, s in cur.fetchall():
            g = genes.setdefault(gid, {"symbol": sym, "hgnc": hgnc, "src": {}})
            g["src"][src] = s
        cur.execute("SELECT gene_id, percentage_score, evidence_tier FROM gene_scores")
        live = {gid: (p, t) for gid, p, t in cur.fetchall()}
        cur.execute(CLASS_SQL)
        cls: dict[int, dict[str, set[str]]] = defaultdict(dict)
        gencc_has_clingen = gencc_has_panelapp = 0
        for gid, src, c, subs in cur.fetchall():
            cls[gid].setdefault(src, set()).update(c)
            if src == "GenCC":
                gencc_has_clingen += "ClinGen" in subs
                gencc_has_panelapp += any("PanelApp" in s for s in subs)
    conn.close()

    # Self-check: exclude-nothing global run == live view, every gene.
    bad = [gid for gid in genes if gid not in live]
    bad += [gid for gid in live if gid not in genes]
    for gid, g in genes.items():
        pct, t = score(g["src"], set(), "global", n_global)
        lp, lt = live.get(gid, (None, None))
        if lp is None or abs(pct - lp) > EPS or t != lt:
            bad.append(gid)
    print(
        f"self-check: {len(genes) - len(set(bad))}/{len(live)} genes reproduce "
        f"live gene_scores (|diff| <= {EPS}, tier exact); global divisor={n_global}"
    )
    if bad:
        print(f"SELF-CHECK FAILED for {len(set(bad))} genes, e.g. {sorted(set(bad))[:10]}")
        return 1

    res: dict[tuple[str, str], dict[int, tuple[float, str]]] = {}
    rk: dict[tuple[str, str], dict[int, int]] = {}
    for pol in POLICIES:
        for sc, ex in SCENARIOS.items():
            ex = ex & present  # only a source that exists can shrink the global divisor
            res[pol, sc] = {gid: score(g["src"], ex, pol, n_global) for gid, g in genes.items()}
            rk[pol, sc] = ranks({gid: v[0] for gid, v in res[pol, sc].items()})
    strata = {gid: stratum(cls.get(gid, {})) for gid in genes}

    args.out_dir.mkdir(parents=True, exist_ok=True)
    banner = (
        f"# {args.label}: DEV SNAPSHOT, NOT PRODUCTION; {len(genes)} scored genes; "
        f"global divisor {n_global}; generated by backend/scripts/benchmark_clingen_gencc.py"
    )
    keys = [(p, s) for p in POLICIES for s in SCENARIOS]
    with open(args.out_dir / f"{args.label}_per_gene.csv", "w", newline="") as f:
        w = csv.writer(f)
        w.writerow(
            [
                "approved_symbol",
                "hgnc_id",
                "stratum",
                "clingen_classes",
                "gencc_classes",
                "sources",
                "gencc_score",
            ]
            + [f"{p}.{s}.{c}" for p, s in keys for c in ("pct", "tier", "rank")]
        )
        for gid, g in sorted(genes.items(), key=lambda kv: kv[1]["symbol"]):
            c = cls.get(gid, {})
            row = [
                g["symbol"],
                g["hgnc"],
                strata[gid],
                ";".join(sorted(c.get("ClinGen", []))),
                ";".join(sorted(c.get("GenCC", []))),
                ";".join(sorted(g["src"])),
                g["src"].get("GenCC", ""),
            ]
            for k in keys:
                row += [f"{res[k][gid][0]:.4f}", res[k][gid][1], rk[k][gid]]
            w.writerow(row)

    lines, disc = [banner, ""], []
    order = {t: i for i, t in enumerate(TIERS)}
    for pol in POLICIES:
        base = res[pol, "full"]
        lines += [
            f"## Divisor policy: {pol}",
            "",
            "Tier distribution (all scored genes):",
            "",
            "| tier | " + " | ".join(SCENARIOS) + " |",
            "|---" * (len(SCENARIOS) + 1) + "|",
        ]
        dist = {s: Counter(t for _, t in res[pol, s].values()) for s in SCENARIOS}
        lines += [
            f"| {t} | " + " | ".join(str(dist[s][t]) for s in SCENARIOS) + " |" for t in TIERS
        ]
        lines += [
            "",
            "Change vs full (same policy):",
            "",
            "| scenario | tier down | tier up | high-ev genes | high-ev tier down | "
            "high-ev below established | median rank shift (high-ev) |",
            "|---|---|---|---|---|---|---|",
        ]
        high = [gid for gid in genes if strata[gid].startswith("high")]
        for sc in SCENARIOS:
            cur_ = res[pol, sc]
            down = [g for g in genes if order[cur_[g][1]] > order[base[g][1]]]
            up = [g for g in genes if order[cur_[g][1]] < order[base[g][1]]]
            hd = [g for g in high if g in set(down)]
            below = sum(order[cur_[g][1]] > order["established_support"] for g in high)
            shift = statistics.median(rk[pol, sc][g] - rk[pol, "full"][g] for g in high)
            lines.append(
                f"| {sc} | {len(down)} | {len(up)} | {len(high)} | {len(hd)} | "
                f"{below} | {shift:+g} |"
            )
            for g in down + up:
                disc.append(
                    [
                        pol,
                        sc,
                        genes[g]["symbol"],
                        genes[g]["hgnc"],
                        strata[g],
                        base[g][1],
                        cur_[g][1],
                        f"{base[g][0]:.4f}",
                        f"{cur_[g][0]:.4f}",
                        rk[pol, "full"][g],
                        rk[pol, sc][g],
                    ]
                )
        lines += [
            "",
            "High-evidence strata, tier counts per scenario:",
            "",
            "| stratum | scenario | " + " | ".join(TIERS) + " |",
            "|---|---" + "|---" * len(TIERS) + "|",
        ]
        for st in ("high_both", "high_clingen_only", "high_gencc_only"):
            ids = [g for g in genes if strata[g] == st]
            for sc in SCENARIOS:
                c = Counter(res[pol, sc][g][1] for g in ids)
                lines.append(
                    f"| {st} (n={len(ids)}) | {sc} | " + " | ".join(str(c[t]) for t in TIERS) + " |"
                )
        lines.append("")
    lines += [
        "## Provenance overlap",
        "",
        f"- strata: {dict(sorted(Counter(strata.values()).items()))}",
        f"- GenCC gene records listing ClinGen as submitter: {gencc_has_clingen}",
        f"- GenCC gene records listing a PanelApp submitter: {gencc_has_panelapp}",
        "",
    ]

    with open(args.out_dir / f"{args.label}_discrepant_genes.csv", "w", newline="") as f:
        w = csv.writer(f)
        w.writerow(
            [
                "policy",
                "scenario",
                "approved_symbol",
                "hgnc_id",
                "stratum",
                "full_tier",
                "scenario_tier",
                "full_pct",
                "scenario_pct",
                "full_rank",
                "scenario_rank",
            ]
        )
        w.writerows(disc)
    (args.out_dir / f"{args.label}_summary.md").write_text("\n".join(lines))
    print("\n".join(lines))
    return 0


if __name__ == "__main__":
    sys.exit(main())
