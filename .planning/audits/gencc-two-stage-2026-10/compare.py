#!/usr/bin/env python3
"""Compare two benchmark runs for #330.

Usage: python3 -I compare.py DIR [AFTER [BEFORE]]  (labels; default: after before)
Reads DIR/{label}_per_gene.csv; e.g. `. v1_after`, `. v010_after`, `. after v010_after`.
"""

import csv
import statistics
import sys
from collections import Counter
from pathlib import Path

TIERS = [
    "comprehensive_support",
    "multi_source_support",
    "established_support",
    "preliminary_evidence",
    "minimal_evidence",
    "no_evidence",
]
d = Path(sys.argv[1])
after_label, before_label = (sys.argv[2:] + ["after", "before"][len(sys.argv[2:]) :])[:2]


def load(label):
    with open(d / f"{label}_per_gene.csv") as f:
        return {r["hgnc_id"]: r for r in csv.DictReader(f)}


b, a = load(before_label), load(after_label)
assert b.keys() == a.keys(), "gene sets differ"
gencc = [h for h in b if b[h]["gencc_score"] != "" or a[h]["gencc_score"] != ""]
assert all(b[h]["gencc_score"] != "" and a[h]["gencc_score"] != "" for h in gencc)
dg = {h: float(a[h]["gencc_score"]) - float(b[h]["gencc_score"]) for h in gencc}
up = [v for v in dg.values() if v > 1e-12]
down = [v for v in dg.values() if v < -1e-12]
dp = {h: float(a[h]["global.full.pct"]) - float(b[h]["global.full.pct"]) for h in b}
moved = [v for v in dp.values() if abs(v) > 1e-12]

out = [f"genes scored: {len(b)}; genes with GenCC evidence: {len(gencc)}", ""]
out += [
    "## GenCC sub-score change (after - before)",
    "",
    f"- up: {len(up)}, down: {len(down)}, unchanged: {len(gencc) - len(up) - len(down)}",
    f"- max increase: {max(up, default=0):+.6f}; max decrease: {min(down, default=0):+.6f}",
    f"- median change among changed: {statistics.median(up + down):+.6f}" if up + down else "",
    "- distribution of change: "
    + ", ".join(f"{k:+.4f}: {v}" for k, v in sorted(Counter(round(x, 4) for x in dg.values()).items())),
    "",
    "## percentage_score shift (global divisor, all scored genes)",
    "",
    f"- genes changed: {len(moved)} (up {sum(v > 0 for v in moved)}, down {sum(v < 0 for v in moved)})",
    f"- max increase: {max([v for v in moved if v > 0], default=0):+.4f} points; "
    f"max decrease: {min([v for v in moved if v < 0], default=0):+.4f} points",
    f"- mean shift among changed: {statistics.mean(moved):+.4f} points" if moved else "",
    "",
    "## Tier transitions (rows before, columns after)",
    "",
    "| before \\ after | " + " | ".join(TIERS) + " | total |",
    "|---" * (len(TIERS) + 2) + "|",
]
tt = Counter((b[h]["global.full.tier"], a[h]["global.full.tier"]) for h in b)
for t in TIERS:
    out.append(
        f"| {t} | " + " | ".join(str(tt[t, u]) for u in TIERS) + f" | {sum(tt[t, u] for u in TIERS)} |"
    )
out.append("| total | " + " | ".join(str(sum(tt[t, u] for t in TIERS)) for u in TIERS) + f" | {len(b)} |")
out += [
    "",
    "## Top 20 genes by |GenCC sub-score change|",
    "",
    "| gene | GenCC classes | GenCC before | GenCC after | pct before | pct after | tier before | tier after |",
    "|---|---|---:|---:|---:|---:|---|---|",
]
for h in sorted([h for h in gencc if abs(dg[h]) > 1e-12], key=lambda h: (-round(abs(dg[h]), 9), b[h]["approved_symbol"]))[:20]:
    out.append(
        f"| {b[h]['approved_symbol']} | {b[h]['gencc_classes']} | {float(b[h]['gencc_score']):.4f} | "
        f"{float(a[h]['gencc_score']):.4f} | {b[h]['global.full.pct']} | {a[h]['global.full.pct']} | "
        f"{b[h]['global.full.tier']} | {a[h]['global.full.tier']} |"
    )
print("\n".join(out))
