# Spec: HPO clinical groups v2 (disease-level, frequency × information content) (#338)

Status: approved 2026-10-26 and implemented for v0.9.0 (#338). Supersedes
`.planning/plans/2026-10-21-hpo-neoplasia-group.md`.

## Problem

`classification.clinical_group` feeds the gene pages, the network colouring and
the manuscript. The v1 rule (`_classify_clinical_group`, `annotations/hpo.py`)
intersects a gene's flattened HPO term set with five hand-picked terms per group
and takes the argmax of `matched / 5`. Review on 2026-10-26 found:

1. **Wrong or non-specific signature terms.** `complement` contains no complement
   term (Proteinuria, Nephrotic syndrome, Tubulointerstitial nephritis, Urethral
   obstruction, Elevated creatinine), so FH, SDHB and COL4A5 are "complement".
   `Renal cyst` is in both `cakut` and `cyst_cilio` and ties go to `cakut`.
   `glomerulopathy` holds Stage 5 CKD. Four YAML comments name the wrong term:
   HP:0000097 is FSGS (not glomerulonephritis), HP:0000099 is Glomerulonephritis
   (not glomerulosclerosis), HP:0030888 is *C3 nephritic factor positivity* (not
   C3 glomerulopathy); HP:0000787 is now labelled *Kidney stone*.
2. **One term wins.** A single matched term (score 0.2) decides the primary.
3. **Information is discarded.** `parse_bulk_file` keeps a per-gene term union
   and drops the disease and frequency columns of `genes_to_phenotype.txt`, so a
   gene where renal cell carcinoma is an occasional feature of one disease
   (HNF1B) looks identical to one where it is the defining feature (VHL).
4. **No validation.** No rule was ever measured against an independent reference.

## Method

**Data.** HPO release pinned (2026-09-01): `genes_to_phenotype.txt` (gene, term,
frequency, disease; already downloaded) and `hp.json` (ontology, new download),
both from the versioned GitHub release URL and checked against pinned sha256
digests (a mismatch deletes the cached file and fails the run); the release is
stored with every classification.

**Groups.** Each group is a small set of *root terms*, matched through the
ontology: a gene term counts for a group when it is the root or a descendant.
Roots were chosen once from the HPO hierarchy, before measuring, and were not
tuned on the reference:

| Group | Root terms |
|---|---|
| complement | HP:0005575 Hemolytic-uremic syndrome, HP:0000793 Membranoproliferative GN, HP:0004431 Reduced circulating complement, HP:0030888 C3 nephritic factor positivity |
| cakut | HP:0008678 Renal hypoplasia/aplasia, HP:0000110 Renal dysplasia, HP:0025633 Abnormal ureter morphology, HP:0000076 Vesicoureteral reflux, HP:0000126 Hydronephrosis, HP:0000085 Horseshoe kidney, HP:0000086 Ectopic kidney, HP:0010481 Urethral valve, HP:0000081 Duplicated collecting system |
| cyst_cilio | HP:0000107 Renal cyst, HP:0000090 Nephronophthisis, HP:0000113 Polycystic kidney dysplasia |
| glomerulopathy | HP:0100820 Glomerulopathy, HP:0000100 Nephrotic syndrome, HP:0000093 Proteinuria, HP:0000790 Hematuria |
| tubulopathy | HP:0000124 Renal tubular dysfunction, HP:0001947 Renal tubular acidosis, HP:0009806 Nephrogenic diabetes insipidus, HP:0000127 Renal salt wasting, HP:0003355 Aminoaciduria, HP:0000117 Renal phosphate wasting, HP:0003127 Hypocalciuria, HP:0002900 Hypokalemia, HP:0002917 Hypomagnesemia |
| nephrolithiasis | HP:0000787 Kidney stone, HP:0000121 Nephrocalcinosis |
| neoplasia | HP:0009726 Renal neoplasm |

**Evidence.** For gene *g* and group *G*:

E(g, G) = Σ over diseases *d* of *g* · Σ over matched terms *t* of *d* (most specific only) · f(d, t) · IC(t)

- IC(t) = −ln(n(t)/N): *n(t)* diseases in `genes_to_phenotype.txt` annotated to
  *t* or a descendant, *N* all diseases (9,177 in 2026-09-01). This is the
  Resnik information content: a descendant *t* of root *r* has Resnik
  similarity IC(MICA(t, r)) = IC(r) to the root, and the more specific IC(t)
  rewards specific evidence; common, unspecific terms (Proteinuria, IC 3.8)
  weigh less than specific ones (Renal cell carcinoma, IC 6.1).
- f(d, t): HPO frequency, weights as in VarLens (`hpo-scoring.config.ts`):
  obligate 1.0, very frequent 0.895, frequent 0.545, occasional 0.17, very
  rare 0.025, excluded 0 (dropped); `m/n` → (m + 0.8)/(n + 2); `x%` → x/100;
  unknown → 0.35.
- "Most specific only": a term whose descendant is also annotated to the same
  disease is not counted again.

**Labels.** `primary` = argmax E (ties: `CLINICAL_GROUP_PRIORITY`, neoplasia
last); `None` when every E is 0. `secondary` = other groups with E ≥ 0.5 ×
E(primary). `scores[G]` = E(G) / Σ E (share of the gene's kidney-group evidence,
in [0, 1]); `evidence[G]` = E(G) raw. `method: "hpo-freq-ic-v2"`, `hpo_release`.

**Failure behaviour.** The method needs both pinned files. If either cannot be
downloaded or parsed, the HPO annotation run fails before writing; stored
annotations stay as they are (no silent fallback to another method).

## Validation (dev snapshot, HPO 2026-09-01, 3,209 classified genes)

Silver standard: PanelApp green genes on kidney panels mapped to groups
(CAKUT; cystic/ciliopathy; tubulopathy; glomerular/proteinuria/Alport;
MPGN/C3G → complement; nephrocalcinosis/nephrolithiasis; three renal-cancer
panels → neoplasia). 360 genes with ≥ 1 group; a prediction is correct when the
primary is one of the gene's panel groups. Independent of HPO curation, but not
a gold standard (PanelApp lists genes, not disease mechanisms; complement has
only 7 genes).

| Rule | Top-1 in panel groups | Macro-F1 |
|---|---|---|
| v1 (current) | 43.9 % | 0.38 |
| v1 + neoplasia, same scale | 46.1 % | 0.49 |
| v2 roots, count only | 71.1 % | 0.73 |
| v2 roots, IC only | 72.5 % | 0.75 |
| v2 roots, frequency only | 75.0 % | 0.77 |
| **v2 roots, frequency × IC (this spec)** | **76.4 %** | **0.79** |
| v1 terms, frequency × IC | 49.4 % | 0.53 |

All rows use IC from `genes_to_phenotype.txt` as implemented. Most of the gain is the root terms; frequency and IC add 5 points together. IC
from `genes_to_phenotype.txt` instead of `phenotype.hpoa` gives the same
accuracy and 3,192/3,209 identical primaries. Secondary groups (55 genes with
≥ 2 panel groups): 67/118 panel labels recovered, 10 extra labels.

Reference genes: HNF1B cakut (+ cyst_cilio), VHL neoplasia, FH neoplasia,
PALB2 cakut (neoplasia 0.493 × primary, just below the 0.5 secondary cut-off with IC from
`genes_to_phenotype.txt`; 0.5 with IC from `phenotype.hpoa`; the cut-off is not tuned), FANCA cakut, TSC2 neoplasia, CFH complement, COL4A5
glomerulopathy, PKD1 cyst_cilio, WT1 glomerulopathy (+ neoplasia 0.46, just
below secondary). Known misses: SDHB glomerulopathy, VHL secondary
glomerulopathy (0.8).

Limits for the manuscript: one evaluation, no held-out set (the roots were set
before the first measurement and not changed after); PanelApp is a silver
standard; genes without frequency data fall back to 0.35 per term.

## Literature and independent checks (2026-10-26)

- Ontology-aware matching over exact term matching: Köhler et al. 2009
  (PMID:19800049) show HPO semantic-similarity search with information content
  outperforms term matching that ignores the ontology's relationships,
  especially for imprecise or noisy phenotype descriptions. Resnik IC itself:
  Resnik 1995 (IJCAI, not in PubMed). Benchmark context for phenotype-driven
  methods: Yuan et al. 2022 (PMID:35134823); LIRICAL (PMID:32755546).
- Frequency weights are the midpoints of HPO's own frequency classes, as
  defined in hp.json 2026-09-01: very frequent 80–99 % → 0.895, frequent
  30–79 % → 0.545, occasional 5–29 % → 0.17, very rare 1–4 % → 0.025; obligate
  1.0, excluded 0. HPO resource: Gargano et al. 2024 (PMID:37953324). The
  `m/n` smoothing and the 0.35 prior for unknown frequency come from VarLens
  (tuned on phenopacket-store; see VarLens spec 2026-10-14).
- Reference set: PanelApp (Martin et al. 2019, PMID:31676867).
- HNF1B vs VHL, checked in GeneReviews: 17q12 recurrent deletion (HNF1B,
  NBK401562:0008) lists structural kidney anomalies in 167/193 (87 %), cystic
  dysplasia most common, plus collecting-system anomalies and
  tubulointerstitial disease; renal cell carcinoma is not among its kidney
  features. Von Hippel-Lindau syndrome (NBK1463:0010): renal cell carcinoma in
  about 70 % by age 60 and a leading cause of mortality. v2 classifies HNF1B
  cakut (+ cyst_cilio) and VHL neoplasia, matching both.

## Changes

- `datasources.yaml`: `clinical_groups` → `root_terms` lists above (labels in
  comments checked against hp.json by a test); pinned `genes_to_phenotype` and
  `hp.json` URLs.
- `annotations/hpo.py`: `parse_bulk_file` keeps disease → term → frequency;
  ontology load + IC once per run; `_classify_clinical_group` v2. Onset and
  syndromic logic unchanged.
- API: `clinical_group` gains `secondary`, `evidence`, `method`, `hpo_release`
  (additive JSONB keys, no schema enum); `hpo_classifications_v3_` cache key.
- Frontend: neoplasia label/colour (mid-tone, ≥ 3:1 on both canvases);
  GenePhenotypes shows secondary groups and labels the score "share of kidney
  evidence".
- FAQ: one paragraph defining the method.
- `backend/scripts/evaluate_hpo_clinical_groups.py` + results in
  `.planning/audits/hpo-clinical-groups-2026-10/` (reproduces the table).
- Tests: unit (small fixture ontology), golden genes from a captured fixture,
  YAML IDs/labels, failure behaviour (no write when a file is missing).

Rollout: stored values change only after a managed HPO annotation run
(`/api/annotations/pipeline/update`, source hpo, strategy=full) and the view
refresh. Release v0.9.0 (classification semantics change).
