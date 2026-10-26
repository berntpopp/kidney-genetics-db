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
