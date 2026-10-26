# GenCC two-stage sub-score: before/after (#330)

**Development snapshot, not production.** Disposable copies of the development
database (`kgdb-snap-1026` for v1 and v0.10.0, `kgdb-snap-1026b` for the
gene-level and Level 3 runs, 2026-10-26; same data: the `before` and v0.10.0
runs on `kgdb-snap-1026b` reproduced the earlier CSVs byte for byte after
git's LF normalization; the summaries differ only in their label line): 5,183
scored genes, 349 with GenCC evidence, global divisor 7. Formula:
`.planning/specs/2026-10-26-gencc-two-stage.md`.

- `before`: Alembic `0005` (GenCC = MAX of classification weights).
- `after`: Alembic `0008` (two-stage, DiStefano et al. 2022 conflict definition at
  Level 3: same gene, disease and mode of inheritance; current).
- `gene_level_after`: unreleased first `0008` (commit `ac4c83a`, amended away): the
  same definition over each submitter's strongest class across the whole gene. Its
  summary's label line reads `after` (generated before the rename).
- `v010_after`: Alembic `0006`/`0007` (v0.10.0: `≥ 2`-rank conflict rule, Supportive unranked).
- `v1_after`: first run of `0006` before the Supportive correction.
- Each run of `backend/scripts/benchmark_clingen_gencc.py` passed its
  self-check: 5,183/5,183 genes reproduce the live `gene_scores` (tier exact).
  On `kgdb-snap-1026b` the snapshot was upgraded `0001 → 0005` (`before`),
  `→ 0007` (`v010_after`, re-run; CSVs identical to the committed v0.10.0
  files, which were renamed rather than duplicated) and `→ 0008`
  (`gene_level_after`); for Level 3 it was downgraded to `0005` (`before`
  re-run, identical, not re-added) and upgraded to the final `0008` (`after`).
- Files: `{label}_per_gene.csv` (`gencc_score` is the GenCC sub-score;
  `global.full.*` is production `percentage_score`/tier), `{label}_summary.md`,
  `{label}_discrepant_genes.csv` (the #282 ClinGen/GenCC exclusion benchmark at
  each revision).
- Numbers: `python3 -I compare.py . [AFTER [BEFORE]]` (labels; default
  `after before`): `compare.py .` (Level 3 vs MAX), `compare.py . after v010_after`,
  `compare.py . after gene_level_after`, `compare.py . gene_level_after`,
  `compare.py . v010_after`, `compare.py . v1_after`.
  Conflict counts: `psql -At -f conflict_breakdown.sql` (Level 3 vs gene-level vs `0006`),
  `v010_conflict_breakdown.sql`, `v1_conflict_breakdown.sql`; they read only
  `gene_evidence`.
- Stage 1 (`Q`) equals the old MAX for all 349 genes (strongest weight over
  `submissions` equals the one over `classifications`), so every change comes
  from agreement or conflict.


## DiStefano Level 3 conflicts (`0008`, current)

### GenCC sub-score change (after - before)

- up: 33, down: 37, unchanged: 279
- max increase: +0.087889; max decrease: -0.100000
- median change among changed: -0.044548
- distribution of change: -0.1000: 29, -0.0445: 7, -0.0121: 1, +0.0000: 279, +0.0277: 6, +0.0416: 1, +0.0555: 21, +0.0879: 5

### percentage_score shift (global divisor, all scored genes)

- genes changed: 70 (up 33, down 37)
- max increase: +1.2556 points; max decrease: -1.4286 points
- mean shift among changed: -0.2882 points

### Tier transitions vs MAX (rows before, columns after)

| before \ after | comprehensive_support | multi_source_support | established_support | preliminary_evidence | minimal_evidence | no_evidence | total |
|---|---|---|---|---|---|---|---|
| comprehensive_support | 284 | 0 | 0 | 0 | 0 | 0 | 284 |
| multi_source_support | 0 | 156 | 1 | 0 | 0 | 0 | 157 |
| established_support | 0 | 0 | 394 | 0 | 0 | 0 | 394 |
| preliminary_evidence | 0 | 0 | 0 | 1541 | 0 | 0 | 1541 |
| minimal_evidence | 0 | 0 | 0 | 0 | 2807 | 0 | 2807 |
| no_evidence | 0 | 0 | 0 | 0 | 0 | 0 | 0 |
| total | 284 | 156 | 395 | 1541 | 2807 | 0 | 5183 |

One gene changes tier (CFD, multi_source_support to established_support, as
in v0.10.0); no gene moves up a tier.

### Top 20 genes by |GenCC sub-score change|

29 genes tie at |Δ| = 0.1 (the largest change); ties are listed alphabetically,
so these are the first 20 of them.

| gene | GenCC classes | GenCC before | GenCC after | pct before | pct after | tier before | tier after |
|---|---|---:|---:|---:|---:|---|---|
| ALG8 | Definitive;Limited;Strong | 1.0000 | 0.9000 | 78.6799 | 77.2513 | comprehensive_support | comprehensive_support |
| ANLN | Limited;Strong;Supportive | 0.8000 | 0.7000 | 60.9697 | 59.5411 | comprehensive_support | comprehensive_support |
| BICC1 | Limited;Moderate | 0.6000 | 0.5000 | 69.6493 | 68.2207 | comprehensive_support | comprehensive_support |
| BRCA1 | Definitive;Limited;Moderate;Strong | 1.0000 | 0.9000 | 52.0825 | 50.6540 | comprehensive_support | comprehensive_support |
| C4B | No Known Disease Relationship;Strong | 0.8000 | 0.7000 | 33.3297 | 31.9012 | established_support | established_support |
| C8A | Limited;Strong | 0.8000 | 0.7000 | 24.3138 | 22.8852 | established_support | established_support |
| CFD | Limited;Strong | 0.8000 | 0.7000 | 35.0749 | 33.6464 | multi_source_support | established_support |
| DSTYK | Definitive;Limited;Supportive | 1.0000 | 0.9000 | 66.4672 | 65.0386 | comprehensive_support | comprehensive_support |
| EGFR | Limited;Moderate;Strong | 0.8000 | 0.7000 | 25.6462 | 24.2176 | established_support | established_support |
| EMP2 | Limited;Strong;Supportive | 0.8000 | 0.7000 | 59.7126 | 58.2840 | comprehensive_support | comprehensive_support |
| GFRA1 | Limited;Strong | 0.8000 | 0.7000 | 30.2864 | 28.8579 | established_support | established_support |
| HAAO | Definitive;Limited;Moderate;Strong;Supportive | 1.0000 | 0.9000 | 61.5839 | 60.1554 | comprehensive_support | comprehensive_support |
| KIF3B | Limited;Moderate | 0.6000 | 0.5000 | 14.5522 | 13.1236 | preliminary_evidence | preliminary_evidence |
| KYNU | Definitive;Limited;Strong;Supportive | 1.0000 | 0.9000 | 73.2602 | 71.8317 | comprehensive_support | comprehensive_support |
| MAGI2 | Limited;Strong;Supportive | 0.8000 | 0.7000 | 67.0017 | 65.5731 | comprehensive_support | comprehensive_support |
| NADSYN1 | Limited;Moderate;Strong;Supportive | 0.8000 | 0.7000 | 42.0451 | 40.6165 | multi_source_support | multi_source_support |
| NHERF1 | Limited;Moderate;Supportive | 0.6000 | 0.5000 | 47.8303 | 46.4017 | multi_source_support | multi_source_support |
| NUP160 | Limited;Moderate;Strong;Supportive | 0.8000 | 0.7000 | 66.9614 | 65.5328 | comprehensive_support | comprehensive_support |
| NUP205 | Limited;Strong;Supportive | 0.8000 | 0.7000 | 59.5965 | 58.1679 | comprehensive_support | comprehensive_support |
| PTPRO | Limited;Strong;Supportive | 0.8000 | 0.7000 | 69.0107 | 67.5821 | comprehensive_support | comprehensive_support |

### Delta vs the v0.10.0 rule (`compare.py . after v010_after`)

- up: 17, down: 1, unchanged: 331
- max increase: +0.100000; max decrease: -0.100000
- median change among changed: +0.100000
- distribution of change: -0.1000: 1, +0.0000: 331, +0.1000: 17

- genes changed: 18 (up 17, down 1)
- max increase: +1.4286 points; max decrease: -1.4286 points
- mean shift among changed: +1.2698 points

No tier changes (every gene on the diagonal: 284, 156, 395, 1541, 2807).
All genes whose penalty changes (17 lose it, SLC2A9 gains it):

| gene | GenCC classes | GenCC before | GenCC after | pct before | pct after | tier before | tier after |
|---|---|---:|---:|---:|---:|---|---|
| CD151 | Limited;Moderate;Strong;Supportive | 0.7000 | 0.8000 | 65.0868 | 66.5154 | comprehensive_support | comprehensive_support |
| CD2AP | Definitive;Limited;Moderate;Strong;Supportive | 0.9000 | 1.0000 | 89.7962 | 91.2247 | comprehensive_support | comprehensive_support |
| CDKN1C | Definitive;Moderate;Strong | 0.9000 | 1.0000 | 59.7990 | 61.2276 | comprehensive_support | comprehensive_support |
| CEP164 | Definitive;Moderate;Strong | 0.9000 | 1.0000 | 88.0535 | 89.4820 | comprehensive_support | comprehensive_support |
| CEP83 | Definitive;Moderate;Strong;Supportive | 0.9000 | 1.0000 | 76.2278 | 77.6563 | comprehensive_support | comprehensive_support |
| GREB1L | Definitive;Limited;Moderate;Strong;Supportive | 0.9000 | 1.0000 | 64.2822 | 65.7108 | comprehensive_support | comprehensive_support |
| HS2ST1 | Limited;Strong | 0.7000 | 0.8000 | 29.0701 | 30.4987 | established_support | established_support |
| MAFB | Definitive;Moderate;Strong;Supportive | 0.9000 | 1.0000 | 62.3881 | 63.8166 | comprehensive_support | comprehensive_support |
| MUC1 | Definitive;Limited;Moderate;Supportive | 0.9000 | 1.0000 | 90.1751 | 91.6037 | comprehensive_support | comprehensive_support |
| NPHP1 | Definitive;Moderate;Strong;Supportive | 0.9000 | 1.0000 | 97.8230 | 99.2516 | comprehensive_support | comprehensive_support |
| NPHS2 | Definitive;Limited;Strong;Supportive | 0.9000 | 1.0000 | 80.4742 | 81.9027 | comprehensive_support | comprehensive_support |
| PKD2 | Definitive;Limited;Strong;Supportive | 0.9000 | 1.0000 | 95.9409 | 97.3694 | comprehensive_support | comprehensive_support |
| SLC2A9 | Limited;Moderate;Strong;Supportive | 0.8555 | 0.7555 | 74.2579 | 72.8293 | comprehensive_support | comprehensive_support |
| TBC1D1 | Limited;Strong | 0.7000 | 0.8000 | 35.5495 | 36.9781 | multi_source_support | multi_source_support |
| TBC1D32 | Definitive;Moderate | 0.9000 | 1.0000 | 40.9081 | 42.3367 | multi_source_support | multi_source_support |
| TBX18 | Limited;Moderate;Strong | 0.7555 | 0.8555 | 66.6455 | 68.0741 | comprehensive_support | comprehensive_support |
| TMEM67 | Definitive;Moderate;Strong | 0.9000 | 1.0000 | 97.7164 | 99.1450 | comprehensive_support | comprehensive_support |
| TTC21B | Definitive;Limited;Strong;Supportive | 0.9000 | 1.0000 | 92.2440 | 93.6725 | comprehensive_support | comprehensive_support |

### Delta vs the gene-level rule of `ac4c83a` (`compare.py . after gene_level_after`)

- up: 9, down: 1, unchanged: 339
- max increase: +0.100000; max decrease: -0.100000
- median change among changed: +0.100000
- distribution of change: -0.1000: 1, +0.0000: 339, +0.1000: 9

- genes changed: 10 (up 9, down 1)
- max increase: +1.4286 points; max decrease: -1.4286 points
- mean shift among changed: +1.1428 points

No tier changes. All genes whose penalty changes: 9 lose it because their only
Limited-vs-Moderate-or-stronger pair differs in mode of inheritance (CD151,
CD2AP, HS2ST1, MUC1, NPHS2, PKD2, TBX18, TTC21B) or disease term (TBC1D1);
SLC2A9 gains it (Labcorp Limited AD vs Ambry Moderate AD, previously hidden by
Labcorp's Strong AR).

| gene | GenCC classes | GenCC before | GenCC after | pct before | pct after | tier before | tier after |
|---|---|---:|---:|---:|---:|---|---|
| CD151 | Limited;Moderate;Strong;Supportive | 0.7000 | 0.8000 | 65.0868 | 66.5154 | comprehensive_support | comprehensive_support |
| CD2AP | Definitive;Limited;Moderate;Strong;Supportive | 0.9000 | 1.0000 | 89.7962 | 91.2247 | comprehensive_support | comprehensive_support |
| HS2ST1 | Limited;Strong | 0.7000 | 0.8000 | 29.0701 | 30.4987 | established_support | established_support |
| MUC1 | Definitive;Limited;Moderate;Supportive | 0.9000 | 1.0000 | 90.1751 | 91.6037 | comprehensive_support | comprehensive_support |
| NPHS2 | Definitive;Limited;Strong;Supportive | 0.9000 | 1.0000 | 80.4742 | 81.9027 | comprehensive_support | comprehensive_support |
| PKD2 | Definitive;Limited;Strong;Supportive | 0.9000 | 1.0000 | 95.9409 | 97.3694 | comprehensive_support | comprehensive_support |
| SLC2A9 | Limited;Moderate;Strong;Supportive | 0.8555 | 0.7555 | 74.2579 | 72.8293 | comprehensive_support | comprehensive_support |
| TBC1D1 | Limited;Strong | 0.7000 | 0.8000 | 35.5495 | 36.9781 | multi_source_support | multi_source_support |
| TBX18 | Limited;Moderate;Strong | 0.7555 | 0.8555 | 66.6455 | 68.0741 | comprehensive_support | comprehensive_support |
| TTC21B | Definitive;Limited;Strong;Supportive | 0.9000 | 1.0000 | 92.2440 | 93.6725 | comprehensive_support | comprehensive_support |

### Conflict breakdown (`conflict_breakdown.sql`)

- Penalized genes: 37 under `0008` Level 3 (all 37 decreases vs MAX), 45 under
  the gene-level rule (`ac4c83a`), 53 under `0006`.
- Level 3 but not gene-level: SLC2A9. Gene-level but not Level 3: CD151 CD2AP
  HS2ST1 MUC1 NPHS2 PKD2 TBC1D1 TBX18 TTC21B.
- `0006` but not Level 3: CD151 CD2AP CDKN1C CEP164 CEP83 GREB1L HS2ST1 MAFB
  MUC1 NPHP1 NPHS2 PKD2 TBC1D1 TBC1D32 TBX18 TMEM67 TTC21B. Level 3 but not
  `0006`: SLC2A9.
- Level 3 conflicts that exist only because No Known Disease Relationship is
  placed with Refuted: 1 (C4B).
- Every submission on the snapshot has a non-empty `disease_curie` and
  `moi_curie` (967/967), so the missing-key rule changes nothing here.

## Gene-level DiStefano rule (unreleased `ac4c83a`): superseded by Level 3

Same definition over each counted submitter's strongest class across the whole
gene. Numbers from `python3 -I compare.py . gene_level_after` (vs MAX):

- up: 33, down: 45, unchanged: 271
- max increase: +0.087889; max decrease: -0.100000
- median change among changed: -0.044548
- distribution of change: -0.1000: 37, -0.0445: 7, -0.0121: 1, +0.0000: 271, +0.0277: 6, +0.0416: 1, +0.0555: 21, +0.0879: 5

- genes changed: 78 (up 33, down 45)
- max increase: +1.2556 points; max decrease: -1.4286 points
- mean shift among changed: -0.4051 points

- Tier transitions: identical to Level 3 and v0.10.0 (CFD
  multi_source_support to established_support only).
- 45 penalized; vs v0.10.0, 8 genes (CDKN1C, CEP164, CEP83, GREB1L, MAFB,
  NPHP1, TBC1D32, TMEM67; Definitive vs Moderate only) gain +0.1, none lose.

## v0.10.0 (`0006`, Supportive unranked): superseded

Files `v010_*` (renamed from the unprefixed `after_*`/`conflict_breakdown.sql`
of the v0.10.0 audit; contents unchanged except the regenerated summary label
and the SQL header comment). Numbers from `python3 -I compare.py . v010_after`.

#### GenCC sub-score change (after - before)

- up: 33, down: 53, unchanged: 263
- max increase: +0.087889; max decrease: -0.100000
- median change among changed: -0.100000
- distribution of change: -0.1000: 45, -0.0445: 7, -0.0121: 1, +0.0000: 263, +0.0277: 6, +0.0416: 1, +0.0555: 21, +0.0879: 5

#### percentage_score shift (global divisor, all scored genes)

- genes changed: 86 (up 33, down 53)
- max increase: +1.2556 points; max decrease: -1.4286 points
- mean shift among changed: -0.5003 points

#### Tier transitions (rows before, columns after)

| before \ after | comprehensive_support | multi_source_support | established_support | preliminary_evidence | minimal_evidence | no_evidence | total |
|---|---|---|---|---|---|---|---|
| comprehensive_support | 284 | 0 | 0 | 0 | 0 | 0 | 284 |
| multi_source_support | 0 | 156 | 1 | 0 | 0 | 0 | 157 |
| established_support | 0 | 0 | 394 | 0 | 0 | 0 | 394 |
| preliminary_evidence | 0 | 0 | 0 | 1541 | 0 | 0 | 1541 |
| minimal_evidence | 0 | 0 | 0 | 0 | 2807 | 0 | 2807 |
| no_evidence | 0 | 0 | 0 | 0 | 0 | 0 | 0 |
| total | 284 | 156 | 395 | 1541 | 2807 | 0 | 5183 |

#### Top 20 genes by |GenCC sub-score change|

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

#### Conflict breakdown (`v010_conflict_breakdown.sql`)

- 53 genes penalized (all 53 decreases): 45 meet DiStefano et al.'s conflict
  definition (Limited/Disputed/Refuted vs Moderate/Strong/Definitive), 8 are
  Definitive vs Moderate only (stricter rule, kept in v0.10.0, dropped in `0008`), 0 involve
  only Limited or weaker classes.

## v1 (Supportive ranked): first run, superseded

Supportive had rank 3, so Strong vs Orphanet Supportive (gap 2) was a conflict.
Numbers from `python3 -I compare.py . v1_after` and `v1_conflict_breakdown.sql`:

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
  sort key, and `compare.py . v1_after` prints the corrected v1 list.

Production numbers must be re-measured after the migration runs there.
