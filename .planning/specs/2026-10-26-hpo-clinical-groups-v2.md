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
E(primary) (0.4 in v0.10.0, superseded; see "Secondary cut-off"). `scores[G]` = E(G) / Σ E (share of the gene's kidney-group evidence,
in [0, 1]); `evidence[G]` = E(G) raw. `method: "hpo-freq-ic-v2"` (v2.1 in v0.10.0), `hpo_release`.

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

Reference genes at the cut-off 0.5 (see "Secondary cut-off"): HNF1B cakut (+ cyst_cilio), VHL neoplasia, FH neoplasia,
PALB2 cakut (neoplasia 0.493 × primary, just below the 0.5 secondary cut-off with IC from
`genes_to_phenotype.txt`; 0.5 with IC from `phenotype.hpoa`; the cut-off was evaluated afterwards, see "Secondary cut-off"), FANCA cakut, TSC2 neoplasia, CFH complement, COL4A5
glomerulopathy, PKD1 cyst_cilio, WT1 glomerulopathy (+ neoplasia 0.46, just
below secondary). Known misses: SDHB glomerulopathy, VHL secondary
glomerulopathy (0.8).

Limits for the manuscript: one evaluation, no held-out set (the roots were set
before the first measurement and not changed after); PanelApp is a silver
standard; genes without frequency data fall back to 0.35 per term.

## Secondary cut-off (2026-10-26, after v0.9.0): 0.5 kept

Outcome: `SECONDARY_GROUP_RATIO = 0.5`, the v0.9.0 value, and `method` back to
`hpo-freq-ic-v2` (output identical to v0.9.0, so stored v2 payloads stay valid
and v2.1 payloads from v0.10.0 are recomputed). v0.10.0's 0.4 (v2.1, chosen on
a seeded 50/50 split) is superseded. Order of events, stated because each step
was decided after the previous results were known:

1. v2.1 protocol (maintainer decision on #338, fixed before the grid was
   computed; not blind to the 0.493 PALB2 and 0.46 WT1/PKD1 ratios published
   with v0.9.0): seeded 50/50 split, r chosen on half A. It chose 0.40.
2. A 100-seed sweep then showed the split's choice depends on the seed.
3. Leave-one-out and a gene-level paired bootstrap, run after the sweep, show
   that no r in the grid beats 0.5 out of sample.
4. The final selection rule (same-draw one-standard-error rule) was chosen
   **after** these curves were known. It favours parsimony (fewer secondary
   labels) and selects 0.5. It is not a pre-specified rule.

Common to all steps:

- Prediction per gene = {primary} ∪ {groups with E ≥ r × E(primary)}; truth =
  the gene's PanelApp panel groups (silver standard above).
- Metric: multi-label macro-F1 over the 7 groups (per group TP/FP/FN over
  genes, F1 = 2TP/(2TP+FP+FN), unweighted mean) on all 360 reference genes, so
  single-group genes penalise false secondaries.
- Grid r ∈ {0.30, 0.35, …, 0.70}; ties go to the larger r. 0.20 and 0.25 are
  reported as diagnostics only, never selectable.
- r is not chosen to make PALB2 pass; PALB2's ratio (0.493) is reported
  against the chosen r.

### Step 1–2: seeded split (v2.1, superseded)

Deterministic 50/50 split stratified by the gene's first panel group in
`CLINICAL_GROUP_PRIORITY` order (genes sorted by symbol within a stratum,
shuffled with `random.Random(338)`, alternately assigned to A and B); r chosen
on half A. Results (HPO 2026-09-01; half A 181 genes, half B 179, multi-group 55):

| r | Half A | Half B | All 360 | Multi-group | Reference genes with secondary |
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

Half A chose 0.40; held-out half B did not confirm it (0.7458 vs 0.7505 at
0.5). Seed sweep (`--seed-sweep 100`, seeds 0–99), half-A choice: 0.30 in 51
seeds, 0.35 in 29, 0.40 in 1, 0.45 in 10, 0.50 in 6, 0.55 in 1, 0.60 in 0, 0.65
in 1, 0.70 in 1. So 0.40 was the choice for seed 338 only, not a stable optimum.

### Step 3: leave-one-out and paired bootstrap

Leave-one-out: for each reference gene i, r_i = argmax macro-F1 on the other
359 genes; gene i is predicted with r_i. r_i: 0.30 in 353 genes, 0.35 in 7,
0.40–0.70 in 0. With one scalar parameter, leaving one gene out barely moves the
full-set argmax, so this concentration is not evidence of stability. The LOO
macro-F1 of the procedure is **0.7469**, the same as fixed 0.40 (0.7477) or
0.50 (0.7458): selecting r on the data gives no out-of-sample gain.

Paired bootstrap: 2,000 gene-level resamples of the 360 genes (seed 338), all r
scored on the same draws. Gap = F1(best) − F1(r) on all 360 genes, best = 0.30;
SE = bootstrap standard deviation; "best in resamples" = how often each r has
the highest F1 in a resample.

| r | Macro-F1 | SE | Gap to best | SE of gap | Gap 95 % CI | Best in resamples |
|---|---|---|---|---|---|---|
| 0.30 | 0.7577 | 0.0255 | 0.0000 | 0.0000 | [0, 0] | 935 |
| 0.35 | 0.7572 | 0.0260 | 0.0005 | 0.0060 | [−0.0105, +0.0133] | 720 |
| 0.40 | 0.7477 | 0.0270 | 0.0099 | 0.0107 | [−0.0090, +0.0320] | 26 |
| 0.45 | 0.7494 | 0.0273 | 0.0082 | 0.0109 | [−0.0112, +0.0311] | 164 |
| **0.50** | **0.7458** | 0.0275 | 0.0119 | 0.0128 | [−0.0118, +0.0386] | 104 |
| 0.55 | 0.7375 | 0.0282 | 0.0202 | 0.0145 | [−0.0061, +0.0504] | 9 |
| 0.60 | 0.7354 | 0.0285 | 0.0223 | 0.0152 | [−0.0044, +0.0538] | 6 |
| 0.65 | 0.7348 | 0.0286 | 0.0229 | 0.0154 | [−0.0051, +0.0554] | 13 |
| 0.70 | 0.7321 | 0.0286 | 0.0256 | 0.0164 | [−0.0048, +0.0611] | 23 |

Every gap CI includes 0: no r in the grid is distinguishable from 0.30 or
from 0.5. Below the grid (diagnostic, not selectable): 0.25 → 0.7466, 0.20 →
0.7455, so 0.30 is a local peak of the full-set curve, not an edge artefact.

### Step 4: selection rule (chosen after the curves were known)

Same-draw one-SE rule: the largest r whose gap to the best r is at most the
paired-bootstrap SE of that gap. 0.50: gap 0.0119 ≤ SE 0.0128 (kept); 0.55:
gap 0.0202 > 0.0145. **r = 0.50**; the same rule gives 0.50 with bootstrap
seeds 0–4. The script exits 1 if this choice differs from
`SECONDARY_GROUP_RATIO`.

### Sensitivity analysis: r = 0.30 (best full-set F1)

0.30 adds 68 secondary labels to reference genes, 41 of them not among the
gene's PanelApp groups. Per-group F1 at 0.50 → 0.30: glomerulopathy 0.819 →
0.707, cyst_cilio 0.769 → 0.856, nephrolithiasis 0.529 → 0.602, neoplasia
0.788 → 0.833, cakut 0.711 → 0.706, tubulopathy 0.746 → 0.743, complement
0.857 → 0.857. HNF1B gains glomerulopathy (0.33) and nephrolithiasis (0.32),
neither a PanelApp group of HNF1B, while its PanelApp tubulopathy (0.29) is
still missed. Of the 160 genes that gain a secondary group at 0.30, 17 are
annotated to Williams syndrome (ORPHA:904; e.g. BAZ1B, GTF2I, LIMK1, STX1A) and
all gain the same glomerulopathy + nephrolithiasis labels
from that one shared disease. The F1 gain of 0.30 thus comes with low-precision
labels and is within bootstrap noise.

### Data impact and genes

Against v0.10.0 (r = 0.4), of the 3,209 classified dev-snapshot genes 89 lose
at least one secondary group and none gains one; against 0.30, 160 lose; primary
changes 0 (primary does not depend on r). 55 multi-group genes recover 67/118
panel labels with 10 extra (70 and 12 at 0.4). PALB2 is cakut only: its
neoplasia evidence is 0.493 of cakut, below 0.5. This is a consequence of the
calibration result, not a data defect. WT1 glomerulopathy (neoplasia 0.46) and
PKD1 cyst_cilio (nephrolithiasis and glomerulopathy 0.46) have no secondary
group, as in v0.9.0. FANCA stays cakut without neoplasia: no FANCA annotation
in HPO 2026-09-01 is at or below Renal neoplasm (HP:0009726). This is an
HPO-data limit; no cut-off fixes it and annotations are not added by hand (test
gated on `HPO_RELEASE_DIR`).

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
