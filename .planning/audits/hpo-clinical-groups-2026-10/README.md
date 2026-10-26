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
(r = 0.5, v0.9.0; the command now prints 70/118, 12 extra)

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

## Secondary cut-off calibration (2026-10-26, after v0.9.0)

The same command also prints this table (method fixed in advance in the spec,
section "Secondary cut-off calibration"): multi-label macro-F1 over the 7
groups, prediction = primary plus groups with E >= r x E(primary), split 50/50
stratified by first panel group (seed 338). The backend settings must be
importable; outside a configured `backend/.env`, set dummy `DATABASE_URL`,
`JWT_SECRET_KEY`, `ADMIN_PASSWORD` and `POSTGRES_PASSWORD` (no database is used).

```
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

Chosen on half A: r = 0.40 (half B 0.7458, all 0.7477)
All 3209 genes, r = 0.40 vs 0.50: 89 gain and 0 lose at least one secondary group
```

`SECONDARY_GROUP_RATIO` is now 0.4 (`method: hpo-freq-ic-v2.1`). Held-out half
B does not confirm a gain over 0.5 (0.7458 vs 0.7505); half B, all 360 and the
multi-group subset peak at the grid edge 0.30. Add `--seed-sweep 100` to repeat
the half-A choice for seeds 0-99: 0.30 51, 0.35 29, 0.40 1, 0.45 10, 0.50 6,
0.55 1, 0.60 0, 0.65 1, 0.70 1. r = 0.40 is the protocol's choice for seed 338,
not a stable optimum (the optimum may be at or below 0.30); any r in 0.30-0.50
passes PALB2. A seed-independent choice would be a new maintainer decision.
The script exits 1 if its choice differs from `SECONDARY_GROUP_RATIO`. With 0.4: PALB2 cakut + neoplasia (0.493), WT1 glomerulopathy +
neoplasia (0.46), PKD1 cyst_cilio + nephrolithiasis, glomerulopathy (0.46 each);
55 multi-group genes recover 70/118 panel labels, 12 extra. FANCA stays cakut
without neoplasia: no FANCA annotation in HPO 2026-09-01 is at or below Renal
neoplasm (HP:0009726). The tables above this section are the v0.9.0 (r = 0.5)
results; the stored-v1-vs-v2 primary counts do not depend on r.
