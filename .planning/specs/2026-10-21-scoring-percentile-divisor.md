# Scoring: percentile rank and percentage-score divisor

- **Date:** 2026-10-21
- **Status:** Decided
- **Issues:** #337 (percentile rank), #333 (divisor)

## Decisions

1. **Percentile rank (#337): use `cume_dist()`.** `percent_rank()` is
   `(rank - 1) / (n - 1)`, so every evidence row tied at a source's minimum count
   scored 0 for that source (and the gene was `no_evidence` when no other source
   scored it). `cume_dist()` is the share of the source's evidence rows with a
   count at or below this one, in `(0, 1]`: any count-based evidence scores above
   0 and the strongest evidence still scores 1. Sources where all counts are
   equal give every row 1.0. Alembic revision `0005`.
2. **Divisor (#333): keep the global constant.** `percentage_score` stays
   `SUM(source scores) / number of active sources * 100`, not a per-gene count of
   applicable sources.

## Rationale for the constant divisor

- The score is meant to reward breadth: a gene supported by many independent
  sources should outrank one with strong support from a single source. A
  per-gene divisor would give a gene with one maximal source 100%.
- The database does not record which sources could have assessed a gene;
  absence from a source is treated as no support, not as "not applicable". A
  per-gene divisor would first need a new, curated applicability definition.
- It is the documented behaviour; tier thresholds (`>= 50`, `>= 35`, `>= 20`,
  `>= 10`, `> 0`) were set against it, and changing it would shift every tier.
- The divisor is still derived from the data
  (`COUNT(DISTINCT source_name)` over `combined_evidence_scores`), so adding a
  source changes the divisor for all genes equally (genes it supports also
  gain a numerator contribution).

## Expected effect (projection, development database, 2026-10-21)

Read-only projection of the `0005` view logic on the development database
(5,184 genes, 7 active sources; that database was still at revision `0001`, so
ClinGen uses its first classification). The same projection with
`percent_rank()` reproduced the stored `gene_scores` exactly.

| Tier | Before (`percent_rank`) | After (`cume_dist`) |
|---|---:|---:|
| comprehensive_support | 223 | 284 |
| multi_source_support | 135 | 157 |
| established_support | 264 | 394 |
| preliminary_evidence | 1,073 | 1,541 |
| minimal_evidence | 1,550 | 2,807 |
| no_evidence (score 0, has evidence) | 1,938 | 0 |

One gene has no evidence rows and has no `gene_scores` row in either case.
Production numbers must be re-measured after the migration runs there.
