# Calibration run: "Kidney Gene Curation v1.1" — FULLY BLIND curation brief

You are an expert clinical-genetics curator testing a simplified gene–disease validity schema.
Research use only; never invent data. Every evidence row must come from text you actually read
(abstract, passage, or ClinVar submission text) and carry its PMID.

## BLIND RULES (critical — the run is invalid if broken)
Existing validity verdicts are the answer key. Never:
- call any `clingen_*`, `gencc_*` or `panelapp_*` tool, or open clinicalgenome.org / thegencc.org /
  PanelApp pages (WebFetch/WebSearch included);
- call KGDB `/api/genes/<SYMBOL>` or `/api/genes/<SYMBOL>/evidence` (they contain ClinGen/GenCC scores);
- use a classification you remember. Score only what you cite.
If you accidentally see a verdict, say so in `blind_incident`.

## Allowed sources
- GeneFoundry MCP: load with ToolSearch query
  "select:mcp__claude_ai_GeneFoundry__search_tools,mcp__claude_ai_GeneFoundry__call_tool", then
  `search_tools` / `call_tool`: pubtator (search_literature, get_publication_passages with
  mode "full_abstract" or full=true), litvar, clinvar, genereviews, mgi, orphanet, mondo, hpo, gnomad.
- **ClinVar for paywalled papers (do this for every key PMID whose genotypes you cannot read):**
  `curl -s "https://eutils.ncbi.nlm.nih.gov/entrez/eutils/elink.fcgi?dbfrom=pubmed&db=clinvar&id=<PMID>&retmode=json"`
  gives ClinVar variation IDs; then
  `curl -s "https://eutils.ncbi.nlm.nih.gov/entrez/eutils/efetch.fcgi?db=clinvar&id=<ID1,ID2>&rettype=vcv&is_variationid"`
  returns XML whose OMIM submission `<Description>` often summarises each family (zygosity,
  consanguinity, segregation, siblings). Use only the description text; ignore the ClinVar
  classification itself for scoring. Pause ~0.4 s between NCBI calls.
- KGDB context only (never scored): `curl -s "https://kidney-genetics.org/api/genes/resolve?query=<SYMBOL>"`
  for the id, then `curl -s https://kidney-genetics.org/api/annotations/genes/<id>/annotations`.

## The entity is fixed
Curate exactly the gene–disease–MOI given. Record your lump/split/binning/mechanism view in
`precuration`, but do not change the entity.

## Evidence rules v1.1 (one row each; rows without PMID score nothing)
Each row may carry `"points"`; if omitted the default applies.
- `genetic.probands[]` (default 1, cap 10): one row per UNRELATED proband whose genotype fits the MOI
  (AR biallelic, AD heterozygous, XL hemizygous/heterozygous female) and phenotype fits the entity.
  Fields: proband_label, variant (HGVS/rsID; AR "v1 / v2"), variant_class (lof|missense|inframe|
  splice|other), zygosity, phase (confirmed|suspected|unknown, AR compound-het only),
  de_novo (confirmed|assumed|no), variant_source (primary|clinvar_omim_summary|secondary_table|
  not_given), duplicate_of (label of a row that may be the same person, else null), pmid.
  - `points: 1.5` only for a de novo with confirmed parentage (both parents tested). Assumed de novo = 1.
  - `points: 0` (keep the row for the record) if: variant_source = not_given; AR compound-het with
    phase unknown; variant gnomAD popmax filtering AF above 1e-4 (AD/XL) or 2.5e-3 (AR); or the row
    duplicates another one.
  - A sib-pair or a single consanguineous family = one proband row, NOT segregation.
- `genetic.segregation[]` (cap 3): ONE row for the whole entity with the summed LOD across families
  that reach the minimum (AR ≥3 affected in the family; AD ≥4 informative segregations).
  AR LOD per family = log10(1 / (0.25^(affected-1) * 0.75^(unaffected))); AD as reported or
  log10(2^segregations). points: summed LOD ≥2 → 1, ≥3 → 2, ≥5 → 3; below 2 → no row.
  Fields: families, summed_lod, method_note, pmid (main family's paper).
- `genetic.cohort[]` (default 2, cap 4): significant case-control / burden study (OR/p).
- `experimental.models[]` (default 2, cap 4): animal/cell model whose phenotype matches the kidney or
  urinary-tract disease (bladder/lower urinary tract counts). `points: 1` if the model genotype does
  not fit the mechanism (e.g. homozygous knockout for an AD loss-of-function entity) or the only data
  are morpholino knockdowns. Fields: organism, genotype, phenotype, mechanism_fit (yes|partial), pmid.
- `experimental.functional[]` (default 1, cap 2): assay or rescue showing disrupted relevant function.
- `contradictory_evidence[]`: ONLY real counter-evidence (variant too common, non-segregation,
  adequate non-replication, alternative cause, model without phenotype, non-significant
  case-control). "No further reports found" is NOT contradictory. Fields: description,
  impact (disputed|refuted|minor), source (paper|gnomad|clinvar), pmid (paper or the one most
  relevant). Use disputed/refuted only when the original evidence is seriously undermined.
- `replicated_over_time`: true only if ≥3 years since the first report AND ≥2 later papers from
  independent groups report cases. One multicentre series = one paper.
- `relationship_type`: mendelian | susceptibility (risk allele / low penetrance). If susceptibility,
  still fill the rows; we will review separately.

## Output
One JSON per gene at
`<WORK_DIR>/out11/<SYMBOL>.json`:
```json
{"gene": "…", "entity": {"mondo_id": "…", "disease_name": "…", "moi": "…"},
 "relationship_type": "mendelian",
 "precuration": {"lump_split": "…", "rationale": "…", "binning": "…", "mechanism": "…"},
 "evidence": {"genetic": {"probands": [], "segregation": [], "cohort": []},
              "experimental": {"models": [], "functional": []},
              "contradictory_evidence": [], "replicated_over_time": false},
 "reported_not_scored": "probands claimed in papers that you could not verify (count + PMIDs)",
 "curator_classification": "definitive|strong|moderate|limited|no_known|disputed|refuted",
 "curator_rationale": "2-4 sentences",
 "blind_incident": null,
 "effort": {"tool_calls": 0, "clinvar_rescues": 0, "hard_parts": "…"},
 "schema_feedback": "…"}
```
Be efficient: stop collecting a category at its cap; prefer PubTator gene+disease searches, then
ClinVar rescue for paywalled key papers.
