# GenCC two-stage sub-score: before/after (#330)

**Development snapshot, not production.** Disposable copy of the development
database (`kgdb-snap-1026`, 2026-10-26): 5,183 scored genes, 349 with GenCC
evidence, global divisor 7. Formula: `.planning/specs/2026-10-26-gencc-two-stage.md`.

- `before`: Alembic `0005` (GenCC = MAX of classification weights).
- `after`: Alembic `0006` (two-stage, Supportive unranked for conflict).
- Each run of `backend/scripts/benchmark_clingen_gencc.py` passed its
  self-check: 5,183/5,183 genes reproduce the live `gene_scores` (tier exact).
  The snapshot was downgraded to `0005` for `before` and upgraded for `after`;
  `before_per_gene.csv` is byte-identical to `v1_before_per_gene.csv`.
- Files: `{before,after}_per_gene.csv` (`gencc_score` is the GenCC sub-score;
  `global.full.*` is production `percentage_score`/tier), `*_summary.md`,
  `*_discrepant_genes.csv` (the #282 ClinGen/GenCC exclusion benchmark at each
  revision). `v1_*` files are the first run (below).
- Numbers: `python3 -I compare.py .` (corrected) and `python3 -I compare.py . v1_`
  (v1); conflict counts: `psql -At -f conflict_breakdown.sql` (corrected) and
  `v1_conflict_breakdown.sql` (v1), run on the snapshot at `0006`.
- Stage 1 (`Q`) equals the old MAX for all 349 genes (strongest weight over
  `submissions` equals the one over `classifications`), so every change comes
  from agreement or conflict.

## Corrected run (Supportive unranked)

### GenCC sub-score change (after - before)

- up: 33, down: 53, unchanged: 263
- max increase: +0.087889; max decrease: -0.100000
- median change among changed: -0.100000
- distribution of change: -0.1000: 45, -0.0445: 7, -0.0121: 1, +0.0000: 263, +0.0277: 6, +0.0416: 1, +0.0555: 21, +0.0879: 5

### percentage_score shift (global divisor, all scored genes)

- genes changed: 86 (up 33, down 53)
- max increase: +1.2556 points; max decrease: -1.4286 points
- mean shift among changed: -0.5003 points

### Tier transitions (rows before, columns after)

| before \ after | comprehensive_support | multi_source_support | established_support | preliminary_evidence | minimal_evidence | no_evidence | total |
|---|---|---|---|---|---|---|---|
| comprehensive_support | 284 | 0 | 0 | 0 | 0 | 0 | 284 |
| multi_source_support | 0 | 156 | 1 | 0 | 0 | 0 | 157 |
| established_support | 0 | 0 | 394 | 0 | 0 | 0 | 394 |
| preliminary_evidence | 0 | 0 | 0 | 1541 | 0 | 0 | 1541 |
| minimal_evidence | 0 | 0 | 0 | 0 | 2807 | 0 | 2807 |
| no_evidence | 0 | 0 | 0 | 0 | 0 | 0 | 0 |
| total | 284 | 156 | 395 | 1541 | 2807 | 0 | 5183 |

### Top 20 genes by |GenCC sub-score change|

45 genes tie at |Δ| = 0.1 (the largest change); ties are listed alphabetically,
so these are the first 20 of them. The full list is the join of the two
`*_per_gene.csv` files.

| gene | GenCC classes | GenCC before | GenCC after | pct before | pct after | tier before | tier after |
|---|---|---:|---:|---:|---:|---|---|
| ALG8 | Definitive;Limited;Strong | 1.0000 | 0.9000 | 78.6799 | 77.2513 | comprehensive_support | comprehensive_support |
| ANLN | Limited;Strong;Supportive | 0.8000 | 0.7000 | 60.9697 | 59.5411 | comprehensive_support | comprehensive_support |
| BICC1 | Limited;Moderate | 0.6000 | 0.5000 | 69.6493 | 68.2207 | comprehensive_support | comprehensive_support |
| BRCA1 | Definitive;Limited;Moderate;Strong | 1.0000 | 0.9000 | 52.0825 | 50.6540 | comprehensive_support | comprehensive_support |
| C4B | No Known Disease Relationship;Strong | 0.8000 | 0.7000 | 33.3297 | 31.9012 | established_support | established_support |
| C8A | Limited;Strong | 0.8000 | 0.7000 | 24.3138 | 22.8852 | established_support | established_support |
| CD151 | Limited;Moderate;Strong;Supportive | 0.8000 | 0.7000 | 66.5154 | 65.0868 | comprehensive_support | comprehensive_support |
| CD2AP | Definitive;Limited;Moderate;Strong;Supportive | 1.0000 | 0.9000 | 91.2247 | 89.7962 | comprehensive_support | comprehensive_support |
| CDKN1C | Definitive;Moderate;Strong | 1.0000 | 0.9000 | 61.2276 | 59.7990 | comprehensive_support | comprehensive_support |
| CEP164 | Definitive;Moderate;Strong | 1.0000 | 0.9000 | 89.4820 | 88.0535 | comprehensive_support | comprehensive_support |
| CEP83 | Definitive;Moderate;Strong;Supportive | 1.0000 | 0.9000 | 77.6563 | 76.2278 | comprehensive_support | comprehensive_support |
| CFD | Limited;Strong | 0.8000 | 0.7000 | 35.0749 | 33.6464 | multi_source_support | established_support |
| DSTYK | Definitive;Limited;Supportive | 1.0000 | 0.9000 | 66.4672 | 65.0386 | comprehensive_support | comprehensive_support |
| EGFR | Limited;Moderate;Strong | 0.8000 | 0.7000 | 25.6462 | 24.2176 | established_support | established_support |
| EMP2 | Limited;Strong;Supportive | 0.8000 | 0.7000 | 59.7126 | 58.2840 | comprehensive_support | comprehensive_support |
| GFRA1 | Limited;Strong | 0.8000 | 0.7000 | 30.2864 | 28.8579 | established_support | established_support |
| GREB1L | Definitive;Limited;Moderate;Strong;Supportive | 1.0000 | 0.9000 | 65.7108 | 64.2822 | comprehensive_support | comprehensive_support |
| HAAO | Definitive;Limited;Moderate;Strong;Supportive | 1.0000 | 0.9000 | 61.5839 | 60.1554 | comprehensive_support | comprehensive_support |
| HS2ST1 | Limited;Strong | 0.8000 | 0.7000 | 30.4987 | 29.0701 | established_support | established_support |
| KIF3B | Limited;Moderate | 0.6000 | 0.5000 | 14.5522 | 13.1236 | preliminary_evidence | preliminary_evidence |

One gene changes tier (CFD, multi_source_support to established_support); no
gene moves up a tier.

### Conflict breakdown (`conflict_breakdown.sql`)

- 53 genes penalized (all 53 decreases): 45 meet DiStefano et al.'s conflict
  definition (Limited/Disputed/Refuted vs Moderate/Strong/Definitive), 8 are
  Definitive vs Moderate only (stricter rule, kept; see the spec), 0 involve
  only Limited or weaker classes.

## v1 (Supportive ranked): first run, superseded

Supportive had rank 3, so Strong vs Orphanet Supportive (gap 2) was a conflict.
Numbers from `python3 -I compare.py . v1_` and `v1_conflict_breakdown.sql`:

- GenCC sub-score: up 20, down 147, unchanged 182; max increase +0.087889,
  max decrease −0.100000.
- percentage_score: 167 genes changed (up 20, down 147); max +1.2556,
  max −1.4286 points; mean among changed −1.0618 points.
- Conflicts: 147 penalized; 94 only because of a Supportive class; all 181
  Supportive submissions are from Orphanet (123 of the 147 penalized genes had
  an Orphanet Supportive submission).
- Tier transitions: comprehensive→multi_source 4, multi_source→established 2,
  established→preliminary 1; all other genes kept their tier (280, 155, 393,
  1541, 2807 on the diagonal).
- The v1 top-20 table first committed with this audit broke |Δ| = 0.1 ties by
  floating-point noise rather than alphabetically; `compare.py` now rounds the
  sort key, and `compare.py . v1_` prints the corrected v1 list.

Production numbers must be re-measured after the migration runs there.
