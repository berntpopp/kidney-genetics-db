# Variant position statistics (linear protein and 3D) — design

Status: approved for implementation by the maintainer ("implement your rigorous core proposal",
2026-10-31). Builder: plan in `.planning/plans/2026-10-31-variant-position-statistics.md`.

## Intent

A clinical geneticist looking at a gene's protein views wants to know, with a stated null model and
honest p-values, whether pathogenic missense variation concentrates in a domain, a linear stretch
(hotspot) or a 3D neighbourhood. This supports, and never replaces, an ACMG/AMP **PM1** judgement
("mutational hot spot and/or critical and well-established functional domain without benign
variation"). Every number must be reproducible (data versions, seed, permutation count shown).

## Goals

1. **Domain enrichment** (linear): for each UniProt domain/region, are ClinVar P/LP missense variants
   over-represented relative to population missense variants?
2. **Linear hotspot scan**: which contiguous stretches are enriched, with family-wise error control
   over all windows scanned?
3. **3D clustering**: are P/LP missense residues closer together in the AlphaFold model than
   population missense residues would be?
4. **3D hotspots**: which residues sit in a spatial neighbourhood enriched for P/LP variants,
   with family-wise error control?
5. Results visible on the Protein Domains tab and the 3D tab, with methods, data versions and seed.

## Non-goals (v1)

- No automatic ACMG criterion or classification; no "PM1 met" badge.
- No mutability/trinucleotide model, no homolog aggregation (MetaDome-style), no AlphaMissense.
- No backend statistics endpoint; no MCP exposure.
- No change to the existing 2D/3D variant lists (they keep using the capped detail list).

## Anti-goals (failure even if it "works")

- A p-value without its null model, unit and correction stated next to it.
- Significance from a capped or non-random variant subset (the 200-variant detail cap).
- Results that change between reloads (unseeded randomness) or block the UI thread.
- Wording that implies clinical classification.

## Data

### Cases: ClinVar P/LP missense (ours, versioned)

The ClinVar annotation source already parses every variant of a gene; only detail lists are capped
(`_MAX_DETAIL_VARIANTS = 200`). Add an **uncapped, compact** field to the ClinVar annotation:

```json
"missense_residues": [
  {"residue": 177, "ref": "Arg",
   "counts": {"pathogenic": {"2": 2}, "likely_pathogenic": {"1": 1}, "vus": {"0": 1, "1": 2}}}
]
```

- One row per (residue, ref) with ≥1 missense variant; `counts` keyed by the existing ClinVar
  `category`, then by review-star level as a string; only non-zero keys stored. Missense = molecular consequence `missense variant` and a
  single-residue substitution HGVS (`p.Arg177Trp`, not Ter/fs/del/ext), the same rule as the 3D view.
- Unit: one ClinVar variation record (VCV) = one variant.
- Both the bulk path (`GeneAccumulator`) and the eUtils fallback (`_aggregate_variants`) produce it.
- Additive field: older annotations simply lack it; the UI then says statistics need a ClinVar
  refresh (no silent fallback to the capped list).
- Populated by re-running the ClinVar source through the pipeline API
  (`/api/annotations/pipeline/update`, source `clinvar`, `strategy=full`, `force=true`).

### Controls: gnomAD v4.1 missense (live, per gene)

Fetched in the browser from `https://gnomad.broadinstitute.org/api` (CORS `*`, verified) on first
use, cached per session like the AlphaFold model:

```graphql
query($g:String!){ gene(gene_symbol:$g, reference_genome:GRCh38){
  variants(dataset: gnomad_r4){ variant_id consequence hgvsp
    exome{ ac filters } genome{ ac filters } } } }
```

- Keep `consequence == "missense_variant"`, single-residue HGVS, and at least one of exome/genome
  with `ac > 0` and empty `filters` (PASS). Unit: one gnomAD variant (`variant_id`).
- gnomAD `hgvsp` is on the canonical transcript; rows whose reference amino acid disagrees with the
  UniProt/AlphaFold sequence are dropped and counted (as the 3D view already does).
- Overlap with ClinVar P/LP is **kept** (conservative: it biases toward the null). Stated in methods.

### Residue sequence and structure (builder check, settled as builder's calls)

- **Linear statistics never depend on AlphaFold.** Reference sequence = UniProt canonical FASTA
  (`https://rest.uniprot.org/uniprotkb/{accession}.fasta`, CORS `*`, verified), fetched once per
  session. Rationale: AlphaFold has no model for proteins > 2 700 aa (PKD1 P98161 returns `{}`,
  verified 2026-10-31), and those are central kidney genes.
- **3D statistics only on a full-length model** (`uniprotStart == 1 && uniprotEnd == length`).
  Fragments or no model: the section says "No full-length AlphaFold model for this protein, so no
  3D statistics" and the linear statistics still run. Never mix fragments.
- 3D: Cα coordinates and pLDDT (B-factor) from the AlphaFold model already loaded by the 3D tab.

### Variant quality filters (builder check, settled as builder's calls)

- **Review status**: `missense_residues` stores counts per category *and* review-star level
  (`counts: {"pathogenic": {"0": 1, "2": 3}, ...}`), so the threshold can change without a ClinVar
  re-run. Default for cases and for the B/LB count: **≥ 1 star** (criteria provided), matching
  common ClinGen/ACMG practice of discounting assertions without criteria. A "Include 0-star
  records" toggle in the Methods disclosure re-runs the statistics.
- **Reference amino-acid check for both sources**: ClinVar rows also carry `ref`; rows whose
  reference residue disagrees with the UniProt sequence are dropped and counted for ClinVar and
  gnomAD alike, and the counts are shown.
- **Transcript-mismatch guard**: if more than 10% of either source's missense rows fail the
  reference check, statistics are withheld for that gene with the reason shown (a shifted
  transcript would invent or hide hotspots).

## Statistics (engine: `frontend/src/utils/variantStats.ts`, pure, no DOM)

All tests two-sided unless stated. Case = ClinVar P/LP missense; control = gnomAD missense.

1. **Fisher's exact test** on 2×2 `[[case_in, case_out],[ctrl_in, ctrl_out]]`: two-sided p as in
   R `fisher.test` (sum of hypergeometric probabilities ≤ observed × (1 + 1e-7)); **conditional MLE
   odds ratio and exact 95% CI** (as R `fisher.test`). Must match R to 1e-6 relative.
2. **Benjamini–Hochberg** q-values across all features of a gene (match R `p.adjust(..., "BH")`).
3. **Domain enrichment**: one Fisher test per UniProt feature (all types except `Chain`), in vs out.
4. **Linear hotspot scan**: windows of `w = 15` residues, step 1, over the protein. Statistic per
   window: one-sided hypergeometric upper-tail p for cases in window given all variants in window.
   Family-wise adjusted p per window = fraction of permutations whose **minimum** window p is ≤ the
   observed window p, with `(k + 1)/(B + 1)`. Permutation: shuffle case/control labels across all
   variants (positions fixed), `B = 10 000`. Report windows with adjusted p < 0.05 merged into
   regions; for each region also report ClinVar B/LB missense count in it (PM1 "without benign").
5. **3D clustering**: eligible residues = pLDDT ≥ 70. Statistic = mean pairwise Cα distance among
   distinct case residues. Null = same label permutation restricted to variants at eligible residues;
   one-sided empirical p (observed mean distance smaller) `(k + 1)/(B + 1)`, `B = 10 000`.
   Report observed mean, null mean and 95% null interval.
6. **3D hotspots**: for each eligible residue, its neighbourhood = eligible residues with Cα within
   **10 Å**. Statistic per residue: one-sided hypergeometric upper-tail p of cases among variants in
   the neighbourhood. Family-wise adjusted p via the same min-p permutation (`B = 2 000`). Report
   residues with adjusted p < 0.05 and merge them into spatial clusters (connected within 10 Å).
7. **Reproducibility**: seeded PRNG (mulberry32), default seed `20261031`, shown in the UI;
   identical inputs + seed ⇒ identical outputs. Minimum counts: a test needs ≥ 3 cases overall,
   otherwise the UI states "too few P/LP missense variants for a meaningful test".
8. **Execution**: permutation work runs in a same-origin module Web Worker (CSP `default-src 'self'`
   allows it; no blob workers). Target < 2 s for a 600-residue protein on a laptop.

## UI and visualisations

Requested explicitly: professional, easy-to-understand charts, reviewed with the impeccable skill.
Chart rules follow the dataviz skill and DESIGN.md ("Evidence Ledger": colour only for meaning).

- **Colour**: one meaning hue, the existing ClinVar *pathogenic* colour
  (`significanceColor('pathogenic')` from `variantColors.ts`), for significant results and
  observed statistics; everything non-significant or null-model in neutral `--muted-foreground`.
  This is the emphasis form (highlight one, grey the rest); no new hues. Labels and numbers always
  in text tokens, never in the data colour. Reference/threshold lines are solid 1px hairlines with
  a text label (never dashed). Validate the pair against light and dark card surfaces with the
  dataviz `validate_palette.js` (contrast) during implementation.
- **Every chart has a table twin** and a one-sentence plain-language result above it, e.g.
  "Pathogenic missense variants are 4.4× more likely than population variants to fall in the
  POU-specific domain (95% CI 2.5–7.5; q < 0.001)." Sentences are generated from the numbers,
  never hand-written per gene, and say "not significant" plainly when q ≥ 0.05.

### Protein Domains tab, "Position statistics" section (below the plot)

1. **Domain enrichment forest table**: one row per UniProt feature: name, type, range,
   P/LP n, gnomAD n, an inline forest plot cell (point = conditional OR, 2px line = 95% CI,
   log10 x scale shared by all rows, solid hairline at OR = 1 labelled "no enrichment"; infinite or
   zero bounds drawn as an arrow at the axis edge), OR [CI] text, q. Significant rows (q < 0.05)
   use the meaning hue, others neutral. Row hover/focus shows the 2×2 counts.
2. **Hotspot scan track**: a compact track under the existing lollipop/domain plot sharing its x
   scale *and zoom*: −log10(family-wise adjusted p) per window centre as a 2px line with a 10% area
   wash; y axis capped at −log10(1/(B+1)); solid hairline at −log10(0.05) labelled "FWER 0.05".
   Significant regions drawn as a light band through both the lollipop plot and the track.
   Crosshair tooltip: window range, P/LP n, gnomAD n, adjusted p. Table twin: the hotspot-region
   list (range, P/LP n, gnomAD n, ClinVar B/LB n, adjusted p).

### 3D tab, "Spatial statistics" section (below the viewer)

1. **Clustering**: result sentence + a small histogram of the permutation null (mean pairwise Cα
   distance; neutral bars ≤ 24px, 2px gaps) with the observed value as a 2px vertical line in the
   meaning hue, labelled with its value; 95% null interval shown as a shaded span. Table twin:
   observed, null mean, null 95% interval, p, B, seed.
2. **3D hotspots**: cluster list (residues as ranges, P/LP n, gnomAD n, adjusted p); clicking a
   cluster zooms the viewer to it and filters the variant list to its residues. A third colour mode
   **"Hotspots"** tints hotspot residues in the meaning hue on a neutral chain.
- Each section has a "Methods" disclosure: null model, units, tests, correction, `B`, seed, data
  versions (ClinVar annotation date, gnomAD v4.1, AlphaFold entry/version), and the PM1 caveat:
  "Statistical support for an ACMG/AMP PM1 assessment, not a classification. Population variants are
  not benign variants. Research use."
- Loading: sections reserve their height (no layout shift); compute starts when the tab is opened.

## Evaluation (must pass before shipping)

1. Unit tests: Fisher p, conditional OR and CI, and BH against R reference values (generated with
   R 4.5 and pasted into the spec file with the R commands as comments).
2. Calibration: on ≥ 200 simulated null datasets (random labels), the family-wise false-positive
   rate of the linear scan at α = 0.05 lies within its binomial 99% interval around 0.05.
3. Power sanity: a planted hotspot (cases concentrated in 15 residues) is detected.
4. 3D: on a synthetic coordinate set with planted clustering, p < 0.01; with random labels, p is
   approximately uniform (KS test not required; mean within 0.5 ± 0.1 over 100 runs).
6. Design review: impeccable `critique` + `audit` of both sections at 360/768/1440 px in light and
   dark; no layout shift while statistics compute (stability harness CLS 0 on the structure page);
   all findings fixed or explicitly deferred.
5. Real-data report for HNF1B (and one more kidney gene) in this spec's Results section: which
   domains/regions/3D clusters are significant, compared side by side with the MetaDome intolerant
   region 123–171 (reported, not asserted).

## Left to the builder

Component structure, worker message format, exact table styling within the design system, how the
band is drawn in the D3 plot, test file layout.

## Results

(Filled after implementation.)
