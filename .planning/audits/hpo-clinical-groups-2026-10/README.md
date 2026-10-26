# HPO clinical groups v2: validation (#338)

Spec: `.planning/specs/2026-10-26-hpo-clinical-groups-v2.md`. Read-only
evaluation of the production classifier
(`backend/app/pipeline/sources/annotations/hpo.py`) on HPO release 2026-09-01.

## Reproduce

```bash
cd backend && uv run python scripts/evaluate_hpo_clinical_groups.py \
    HPO_DIR ../.planning/audits/hpo-clinical-groups-2026-10/genes_panelapp_ref.tsv \
    config/datasources.yaml
```

`HPO_DIR` holds `genes_to_phenotype.txt` and `hp.json` from
`https://github.com/obophenotype/human-phenotype-ontology/releases/download/v2026-09-01/`.
`genes_panelapp_ref.tsv` (no header): gene symbol, stored v1 primary (dev
snapshot 2026-10-26), PanelApp green kidney panels (`|`), level, NCBI gene ID;
3,209 genes with a stored classification, 360 with at least one panel group.

## Result (2026-10-26)

Information content from the `genes_to_phenotype.txt` disease corpus, as in
production, matching the spec table. The v2 row is the same with IC from
`phenotype.hpoa`; only "v1 terms, frequency x IC" moves (49.2 % with that corpus).

```
HPO release 2026-09-01: 9177 diseases (IC corpus)
Genes: 3209; with a PanelApp group: 360
Reference sizes: {'tubulopathy': 118, 'nephrolithiasis': 35, 'cakut': 76, 'glomerulopathy': 66, 'cyst_cilio': 105, 'neoplasia': 16, 'complement': 7}

| Rule | Top-1 in panel groups | Macro-F1 |
|---|---|---|
| v1 (current) | 43.9% | 0.38 |
| v1 + neoplasia, same scale | 46.1% | 0.49 |
| v2 roots, count only | 71.1% | 0.73 |
| v2 roots, IC only | 72.5% | 0.75 |
| v2 roots, frequency only | 75.0% | 0.77 |
| v2 roots, frequency x IC (this spec) | 76.4% | 0.79 |
| v1 terms, frequency x IC | 49.4% | 0.53 |

Secondary groups (>= 0.5 x primary evidence), 55 genes with >= 2 panel groups: 67/118 panel labels recovered, 10 extra
(r = 0.5, as in v0.9.0 and again now)

| Gene | Primary | Secondary | Evidence share of primary |
|---|---|---|---|
| HNF1B | cakut | cyst_cilio | cakut 1.00, cyst_cilio 0.68, glomerulopathy 0.33, nephrolithiasis 0.32, tubulopathy 0.29, neoplasia 0.18 |
| VHL | neoplasia | glomerulopathy | neoplasia 1.00, glomerulopathy 0.84, cyst_cilio 0.38 |
| FH | neoplasia | glomerulopathy | neoplasia 1.00, glomerulopathy 0.55, tubulopathy 0.28 |
| PALB2 | cakut |  | cakut 1.00, neoplasia 0.49 |
| FANCA | cakut |  | cakut 1.00 |
| TSC2 | neoplasia |  | neoplasia 1.00, cyst_cilio 0.26, glomerulopathy 0.22 |
| CFH | complement |  | complement 1.00, glomerulopathy 0.23 |
| COL4A5 | glomerulopathy |  | glomerulopathy 1.00, cyst_cilio 0.15 |
| PKD1 | cyst_cilio |  | cyst_cilio 1.00, nephrolithiasis 0.46, glomerulopathy 0.46 |
| WT1 | glomerulopathy |  | glomerulopathy 1.00, neoplasia 0.46, cakut 0.11 |
```

## Dev snapshot: stored v1 vs v2 primary (3,209 classified genes)

| Group | Stored v1 | v2 |
|---|---|---|
| complement | 261 | 63 |
| cakut | 474 | 607 |
| glomerulopathy | 78 | 210 |
| cyst_cilio | 60 | 130 |
| tubulopathy | 108 | 253 |
| nephrolithiasis | 118 | 96 |
| neoplasia | 0 | 94 |
| none | 2,110 | 1,753 |
| not in pinned genes_to_phenotype.txt | 0 | 3 |

827 genes change primary (largest moves: none to cakut 186, complement to
glomerulopathy 128, none to tubulopathy 84, none to neoplasia 52, cakut to
cyst_cilio 50); 236 genes get at least one secondary group. TRAF3IP1, PON1 and
PPARGC1A are not in the pinned file: in a run they take the JAX API fallback and
are stored without a clinical group.

PALB2: neoplasia evidence is 0.493 of cakut with IC from `genes_to_phenotype.txt`
(at or above 0.5 with `phenotype.hpoa` IC; the 0.5 cut-off is not tuned), so it
has no neoplasia secondary group. FANCA has no renal-neoplasm annotation in HPO
2026-09-01.

## Secondary cut-off (2026-10-26, after v0.9.0): 0.5 kept

Spec section "Secondary cut-off". v0.10.0 set r = 0.4 from a seeded 50/50
split (v2.1); a seed sweep showed that choice is unstable, and leave-one-out
plus a paired bootstrap show that no r in the grid beats 0.5 out of sample.
The selection rule (same-draw one-SE rule, favouring fewer secondary labels)
was chosen after these curves were known. It selects 0.5, the v0.9.0 value:
`SECONDARY_GROUP_RATIO = 0.5`, `method: hpo-freq-ic-v2`.

The backend settings must be importable; outside a configured `backend/.env`,
set dummy values (no database is used). HPO files: `genes_to_phenotype.txt` and
`hp.json` of 2026-09-01, sha256 checked against `backend/config/datasources.yaml`.

```bash
cd backend && DATABASE_URL=postgresql://x:y@localhost:1/z \
    JWT_SECRET_KEY=dummy-secret-key-for-evaluation-only-0123456789 \
    ADMIN_PASSWORD=dummy POSTGRES_PASSWORD=dummy \
    uv run python scripts/evaluate_hpo_clinical_groups.py \
    HPO_DIR ../.planning/audits/hpo-clinical-groups-2026-10/genes_panelapp_ref.tsv \
    config/datasources.yaml --seed-sweep 100
```

Output (exit 0), after the tables above:

```
Secondary cut-off calibration: multi-label macro-F1, split seed 338, half A 181 genes, half B 179, multi-group 55

| r | Half A | Half B | All 360 | Multi-group | Genes with secondary |
|---|---|---|---|---|---|
| 0.30 | 0.7459 | 0.7760 | 0.7577 | 0.7834 | 102 |
| 0.35 | 0.7488 | 0.7726 | 0.7572 | 0.7763 | 90 |
| 0.40 | 0.7494 | 0.7458 | 0.7477 | 0.7642 | 83 |
| 0.45 | 0.7466 | 0.7514 | 0.7494 | 0.7642 | 80 |
| 0.50 | 0.7382 | 0.7505 | 0.7458 | 0.7570 | 62 |
| 0.55 | 0.7394 | 0.7259 | 0.7375 | 0.7373 | 50 |
| 0.60 | 0.7368 | 0.7251 | 0.7354 | 0.7336 | 43 |
| 0.65 | 0.7361 | 0.7248 | 0.7348 | 0.7256 | 38 |
| 0.70 | 0.7284 | 0.7260 | 0.7321 | 0.7143 | 32 |

Chosen on half A (seed 338, superseded by leave-one-out): r = 0.40 (half B 0.7458, all 0.7477)
Seed sweep, half-A choice over seeds 0..99: 0.30 51, 0.35 29, 0.40 1, 0.45 10, 0.50 6, 0.55 1, 0.60 0, 0.65 1, 0.70 1

Leave-one-out over 360 genes: LOO macro-F1 of the procedure 0.7469; r_i: 0.30 353, 0.35 7, 0.40 0, 0.45 0, 0.50 0, 0.55 0, 0.60 0, 0.65 0, 0.70 0

Paired bootstrap, 2000 gene resamples, seed 338; best r on all genes 0.30

| r | Macro-F1 | SE | Gap to best | SE of gap | Gap 95% CI | Best in resamples |
|---|---|---|---|---|---|---|
| 0.30 | 0.7577 | 0.0255 | 0.0000 | 0.0000 | [+0.0000, +0.0000] | 935 |
| 0.35 | 0.7572 | 0.0260 | 0.0005 | 0.0060 | [-0.0105, +0.0133] | 720 |
| 0.40 | 0.7477 | 0.0270 | 0.0099 | 0.0107 | [-0.0090, +0.0320] | 26 |
| 0.45 | 0.7494 | 0.0273 | 0.0082 | 0.0109 | [-0.0112, +0.0311] | 164 |
| 0.50 | 0.7458 | 0.0275 | 0.0119 | 0.0128 | [-0.0118, +0.0386] | 104 |
| 0.55 | 0.7375 | 0.0282 | 0.0202 | 0.0145 | [-0.0061, +0.0504] | 9 |
| 0.60 | 0.7354 | 0.0285 | 0.0223 | 0.0152 | [-0.0044, +0.0538] | 6 |
| 0.65 | 0.7348 | 0.0286 | 0.0229 | 0.0154 | [-0.0051, +0.0554] | 13 |
| 0.70 | 0.7321 | 0.0286 | 0.0256 | 0.0164 | [-0.0048, +0.0611] | 23 |

Chosen by the same-draw one-SE rule: r = 0.50; code constant 0.5. Same rule, seeds 0-4: 0.50, 0.50, 0.50, 0.50, 0.50

Sensitivity, r = 0.30 vs 0.50: 68 new reference labels, 41 not in the gene's PanelApp groups
  cakut: F1 0.711 at 0.50, 0.706 at 0.30
  cyst_cilio: F1 0.769 at 0.50, 0.856 at 0.30
  tubulopathy: F1 0.746 at 0.50, 0.743 at 0.30
  glomerulopathy: F1 0.819 at 0.50, 0.707 at 0.30
  complement: F1 0.857 at 0.50, 0.857 at 0.30
  nephrolithiasis: F1 0.529 at 0.50, 0.602 at 0.30
  neoplasia: F1 0.788 at 0.50, 0.833 at 0.30
Below the grid (not selectable): r = 0.20 macro-F1 0.7455
Below the grid (not selectable): r = 0.25 macro-F1 0.7466
All 3209 genes, r = 0.50 vs 0.40: 0 gain and 89 lose at least one secondary group; 0 primary changes
All 3209 genes, r = 0.50 vs 0.30: 0 gain and 160 lose at least one secondary group; 0 primary changes
```

The LOO F1 of the selection procedure (0.7469) equals fixed 0.40 or 0.50, and
every gap CI includes 0. At 0.30 (sensitivity analysis), HNF1B gains
glomerulopathy and nephrolithiasis (neither a PanelApp group) and still misses
tubulopathy (0.29), and 17 genes annotated to Williams syndrome (ORPHA:904)
gain the same two labels from that one disease. At 0.5: PALB2 cakut only
(neoplasia 0.493 < 0.5, a calibration consequence, not a data defect); WT1 and
PKD1 without secondary; FANCA cakut without neoplasia (no FANCA annotation in
HPO 2026-09-01 is at or below Renal neoplasm, HP:0009726). The
stored-v1-vs-v2 primary counts above do not depend on r.
