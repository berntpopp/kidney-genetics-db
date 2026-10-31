# Blind calibration against ClinGen: draft iterations 4–8 (2026-10-30/31)

**Alpha.** Agent curations are proposals for mandatory human review, not autonomous classifications.
ClinGen is a reference, not ground truth: disagreements were adjudicated (see below).

## Design
- 105 ClinGen curations (download 2026-10-30), none used in earlier pilots:
  - **dev** 35 (stratified over all classes; used for prompt iterations 4–8);
  - **anchors** 6 (PKD1, PKD2, HNF1B, COL4A5, UMOD, MUC1; regression check);
  - **held-out** 15 (stratified; never analysed before the final run);
  - **validation** 40 (all 13 remaining non-Definitive kidney-related ClinGen curations + 27 random
    unused Definitive kidney-panel curations; 8 of them off-domain, e.g. Fanconi anemia).
- Blind curator agent (`BRIEF_CURATOR_DRAFT.md` + `TOOL_POLICY.md`) → judge agent (`BRIEF_JUDGE.md`) →
  deterministic scorer (`score_draft.py`). Disagreements on dev went to a non-blind adjudicator
  (`BRIEF_ADJUDICATOR.md`) reading the ClinGen report.
- Research via GeneFoundry MCP; NCBI E-utilities only for the OMIM-submitter harvest
  (clinvar-link#119/#122) and PubMed fallback.

## Results
Exact class agreement with ClinGen (scorer on judge-corrected evidence unless noted):

| Iteration | Main change | Dev exact (n=35) | Dev within one class |
|---|---|---|---|
| 4 | baseline (flat 1 point per proband) | 15 (43%) | 25 |
| 5 | mandatory discovery (OMIM harvest, ≥3 queries, case series), rule fixes, accuracy over speed | 25 (71%) | 30 |
| 6 | XML structure, quotes per row, notes ledger, verify+complete judge | 25 (71%) | 29 |
| 7 | per-allele scoring (SOP v12), SOP experimental categories, no "≥4 genetic" house rule | 25 (71%) | 32 |
| 8 | functional support = quoted assay of that variant; count each experiment once; NMD and consanguinity downgrades | **27 (77%)** | **34** |

**Final, untouched genes (iteration 8, n=55):**

| Set | Scorer exact | Within one class | Class-balanced | Curator's own call |
|---|---|---|---|---|
| All | 44 (80%) | 85% | 59% | 37 (67%) |
| Held-out (15, stratified) | 12 (80%) | 80% | 85% | 9 (60%) |
| Kidney validation (32, mostly Definitive) | 28 (88%) | 91% | 49% | 22 (69%) |
| Off-domain (8) | 4 (50%) | 75% | 39% | 6 (75%) |
| Excluding 5 blind-incident genes (50) | 40 (80%) | 86% | 53% | – |

Anchors: 6/6 Definitive. Effort: median ~20 tool calls and ~3–4 min per gene (curator), ~2.5 min (judge).

## What drove the gains
1. **Completeness, not wording.** Telling agents to save calls made them stop at ~9 calls and under-call
   (Moderate → Limited). Mandatory discovery steps raised recall of ClinGen-scored proband papers
   53% → 68%.
2. **Per-allele scoring.** Flat 1 point per proband under-scored recessive null genes and over-scored
   missense genes; 9 of 11 adjudicated iteration-5 disagreements traced to it. Per-allele scoring
   halved the genetic-point error vs ClinGen (≈1.7 → ≈0.8 points).
3. **A strict functional-support definition.** Loose flags inflated missense points. Requiring a quoted
   assay result for the specific variant brought the flag rate after judging to 42% (ClinGen upgrades
   41% of other-variant probands). ClinGen downgrades 58% of null probands, mostly homozygotes in
   consanguineous families; the consanguinity cap fixed PDE6D.
4. **Judge.** It improves evidence quality (catches AF over cap, duplicates, wrong PMIDs, double-counted
   assays) but rarely changes the class (≈1 toward, 1 away per 35 genes).

## Remaining error pattern (untouched set)
- **Over-calls** (7 of 9 directional misses): few probands plus experimental evidence at its cap
  (DAAM2, NUP160, ABCD4, CCNQ, RAD51C, XRCC2). ClinGen expert panels down-weight these; the curator's
  own call was often closer (RAD51C, XRCC2, NUP160 correct; DAAM2 one class off).
- **Under-calls**: gain-of-function missense genes (KCNJ5) and an entity/lumping gap (LAMA5).
- **Near misses by vocabulary**: FANCM Disputed vs ClinGen Refuted; CHD1L Disputed vs Limited.

## Adjudication of dev disagreements (iteration 5, n=11)
ClinGen better 7, both defensible 3, ours better 1. ClinGen out of date: TBC1D8B (expert class
today Strong, ClinGen Moderate 2023). Questionable ClinGen evidence: ZNF423 (a scored case later
explained by an AHDC1 variant).

## Risks found
- **Blinding leaks through the literature.** 5/55 untouched genes had a gene-level ClinGen class quoted in
  recent papers, GeneReviews tables or ClinVar notes. Agents reported them; accuracy without them is
  unchanged (80%).
- **Full text.** Publisher-restricted PMC papers (AJHG, JCI, JASN, KI) are unreadable via API; scraping is
  out of policy. OMIM's ClinVar submissions are the main fallback.
- **Tool gaps** (reported upstream): no submitter-filtered ClinVar harvest (clinvar-link#122), PubTator
  ranking misses discovery papers, gnomAD gateway concurrency limits, gnomAD `chrM` and gene-variant
  filters, VEP timeouts.

## Recommendation for Gene Curator / KGDB
- Use the iteration-8 brief and scorer as the agent proposal; show the scorer class **and** the curator's
  call; flag for the human reviewer when they differ, when the total is within 1 point of a band edge,
  when experimental points exceed genetic points, or when most genetic points come from ≤2 variants.
- Per-allele scoring needs explicit per-row points in Gene Curator's point model (the agent or curator
  enters the computed points), until a native rule exists.
