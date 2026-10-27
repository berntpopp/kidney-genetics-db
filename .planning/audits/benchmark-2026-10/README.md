# ClinGen/GenCC circularity benchmark (#282)

## Production run (2026-10-27)

Run read-only (`PGOPTIONS=-c default_transaction_read_only=on`) inside the
production backend container against the live database: release v0.13.0,
Alembic head `0011`, 5,195 scored genes, global divisor 7. Evidence last
updated 2026-10-26 for ClinGen (212 genes), GenCC (394), HPO, PanelApp and
PubTator; 2026-03-29 for DiagnosticPanels and Literature (curated uploads).
Self-check: the `full`/`global` run reproduces live `gene_scores` for every
gene (the script exits 1 otherwise).

High-evidence genes: 321 (high_both 132, high_clingen_only 35,
high_gencc_only 154). `global` divisor (production):

| scenario | genes tier down | genes tier up | high-ev tier down | high-ev below established_support | median rank shift (high-ev) |
|---|---|---|---|---|---|
| full | 0 | 0 | 0 | 18 | +0 |
| no_clingen | 31 | 924 | 29 | 21 | +0 |
| no_gencc | 117 | 877 | 81 | 40 | +33 |
| no_clingen_gencc | 98 | 1246 | 70 | 38 | +59 |

Reading: with both sources removed, 283/321 high-evidence genes stay at
`established_support` or above; 38 fall below, 15 of them to `no_evidence`
(no other source). GenCC removal moves high-evidence genes more than ClinGen
removal, as on the dev snapshot. 167 of 394 GenCC gene records list ClinGen as
a submitter and 241 a PanelApp submitter, so the sources are not independent
(limits below apply unchanged). Full tables: `production_2026-10-27_summary.md`;
per-gene and discrepant-gene CSVs carry the same label.

The sections below document the method and the earlier development-snapshot
run (2026-10-26), whose files carry the `dev_snapshot` label.

## Development snapshot run (2026-10-26)

### Dataset

- Snapshot: local dev database dump, extracted 2026-10-26; all source evidence
  last updated 2026-03-15. Migrated to Alembic head `0005` (#337 cume_dist),
  `gene_scores` refreshed before the run.
- 5,183 scored genes (rows in `gene_scores`); 7 active sources (global
  divisor 7): ClinGen, GenCC, PanelApp, DiagnosticPanels, HPO, Literature,
  PubTator.
- Inclusion: every gene in `gene_scores` (genes with at least one row in
  `combined_evidence_scores`). Identifiers: HGNC ID + approved symbol.
- No external release versions are recorded in the snapshot beyond the
  `last_updated` fields in each ClinGen/GenCC evidence record.

## Method

`backend/scripts/benchmark_clingen_gencc.py` (read-only connection) recomputes
`percentage_score` and `evidence_tier` exactly as the `gene_scores`
materialized view in `backend/app/db/views.py` does (per-source MAX of
`normalized_score`, summed, divided, times 100; same tier thresholds), then
re-runs with sources removed.

Scenarios: `full`, `no_clingen`, `no_gencc`, `no_clingen_gencc`.

Divisor policies (the issue only asks for a documented policy, so they are
named here):

- `global` — production policy (#333, `.planning/specs/2026-10-21-scoring-percentile-divisor.md`):
  divisor = number of active sources minus the excluded ones (7, 6 or 5).
  Because the divisor shrinks for every gene, many genes without
  ClinGen/GenCC move *up* a tier when those sources are removed.
- `per_gene` — divisor = number of sources the gene itself has after
  exclusion. Comparison only; not a production proposal. Its `full` column
  therefore differs from the live view.

Ranking: competition rank by `percentage_score` (highest = 1, ties share the
best rank), recomputed per scenario and policy.

"High" evidence was defined before evaluation, from the ClinGen/GenCC
`classifications` stored on each gene's evidence record:

| stratum | rule | n |
|---|---|---|
| high_both | ClinGen ∈ {Definitive, Strong} and GenCC ∈ {Definitive, Strong} | 118 |
| high_clingen_only | ClinGen high, GenCC absent or not high | 28 |
| high_gencc_only | GenCC high, ClinGen absent or not high | 139 |
| clingen_gencc_other | ClinGen/GenCC record, neither high | 91 |
| neither | no ClinGen/GenCC record | 4,807 |

Self-check: the `full`/`global` run must equal the live
`gene_scores.percentage_score` within 1e-9 (float summation order) and the
live `evidence_tier` exactly, for every gene; otherwise the script exits 1.
Result on this snapshot: **5183/5183 genes reproduce**.

### Results, dev snapshot (high-evidence = 285 genes in the three `high_*` strata)

A positive median rank shift means high-evidence genes moved DOWN the ranking
(rank 1 = highest score). The CSVs are plain (header on line 1); their file
names carry the `dev_snapshot` label.

`global` divisor (production):

| scenario | genes tier down | genes tier up | high-ev tier down | high-ev below established_support | median rank shift (high-ev) |
|---|---|---|---|---|---|
| full | 0 | 0 | 0 | 13 | +0 |
| no_clingen | 25 | 921 | 24 | 17 | +0 |
| no_gencc | 92 | 880 | 70 | 34 | +31 |
| no_clingen_gencc | 76 | 1261 | 57 | 31 | +55 |

`per_gene` divisor:

| scenario | genes tier down | genes tier up | high-ev tier down | high-ev below established_support | median rank shift (high-ev) |
|---|---|---|---|---|---|
| full | 0 | 0 | 0 | 9 | +0 |
| no_clingen | 15 | 1 | 11 | 14 | +1 |
| no_gencc | 101 | 2 | 60 | 23 | +52 |
| no_clingen_gencc | 127 | 1 | 80 | 25 | +118 |

Reading: with both sources removed under the production divisor, 254/285
high-evidence genes stay at `established_support` or above; 31 fall below,
including 12 that have no other source at all (`no_evidence`). GenCC removal
moves high-evidence genes more than ClinGen removal (more genes, broader
classification). Full tier tables per stratum: `dev_snapshot_2026-10-26_summary.md`.

## Shared provenance and limits

- GenCC aggregates submitters: 148 of 349 GenCC gene records list ClinGen as a
  submitter, and 88 list a PanelApp submitter (PanelApp is also its own
  source here). Excluding one source therefore does not remove its influence.
- ClinGen/GenCC records are kidney-filtered at ingest (ClinGen by kidney GCEP
  panel or disease keyword, GenCC by `is_kidney_related`); the filter can over-
  or under-include, so a high classification is not a guaranteed kidney
  positive and absence is not a negative. They are not an independent reference.
- Classification strata use gene-level unions of disease-level
  classifications; disease-specificity is lost.
- Kidney filtering at ingest changes with #369 (adrenal-only and non-kidney
  ClinGen matches leave after the next GenCC/ClinGen run), so later runs differ.

## Files

- `dev_snapshot_2026-10-26_per_gene.csv` — per gene: stratum,
  classifications, sources, and pct/tier/rank for every policy × scenario.
- `dev_snapshot_2026-10-26_discrepant_genes.csv` — every gene whose tier
  differs from `full` under the same policy (3,502 rows).
- `dev_snapshot_2026-10-26_summary.md` — script output (all tables).

## Reproduce

```bash
cd backend && uv run python scripts/benchmark_clingen_gencc.py \
  --database-url "$DATABASE_URL" \
  --out-dir ../.planning/audits/benchmark-2026-10 \
  --label dev_snapshot_2026-10-26
```
