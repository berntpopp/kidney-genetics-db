# Pilot: clinical diagnostics & resources section (non-scoring)

You are an expert clinical molecular geneticist (kidney genetics). For each gene–disease entity you
are given, curate a **clinical diagnostics** section a diagnostic lab or nephrologist can act on.
Research use only. Never invent transcripts, tools, PMIDs or URLs.

## Tools
- GeneFoundry MCP: load with ToolSearch query
  "select:mcp__claude_ai_GeneFoundry__search_tools,mcp__claude_ai_GeneFoundry__call_tool", then
  `search_tools` / `call_tool` (e.g. gnomad gene details/summary for canonical + MANE transcripts,
  genereviews_search_genereviews / genereviews_search_passages, pubtator_search_literature,
  pubtator_get_publication_passages, clinvar, orphanet).
- Web: load with ToolSearch query "select:WebSearch,WebFetch". Use WebSearch to discover
  resources, and **WebFetch every URL you report** to confirm it loads and is what you claim.
- KGDB context (optional): `curl -s "https://kidney-genetics.org/api/genes/resolve?query=<SYMBOL>"` gives
  the id; `curl -s https://kidney-genetics.org/api/annotations/genes/<id>/annotations` has ensembl/gnomad
  transcript fields. Do NOT use /api/genes/<SYMBOL>.

## What to curate
1. **recommended_transcript**: the MANE Select transcript (RefSeq NM_ with version AND Ensembl
   ENST with version), how you verified it (tool + field), any MANE Plus Clinical transcript, and
   any legacy transcript/numbering the literature commonly uses that differs (with a note).
2. **detectability**: technical reasons standard short-read panel/exome/genome sequencing can MISS
   disease-causing variants in this gene. For each challenge: `challenge` (vntr_repeat |
   pseudogene_segmental_duplication | gc_rich_low_coverage | cnv_whole_gene_or_exon_deletion |
   structural_variant | deep_intronic | mosaicism | other), `affected_variants` (what is missed),
   `recommended_methods` (long_read_sequencing | specialised_caller | mlpa_qpcr_array |
   long_range_pcr_sanger | snapshot_minisequencing | rna_analysis | other), named `tools`
   [{name, version_if_known, url (verified), pmid}], and `pmids` supporting the statement.
   If no special challenge is known, set `detectability: []` and `detectability_note:
   "standard short-read testing adequate (CNV calling recommended)"` or similar — do NOT invent
   problems. CNV detection for exon/whole-gene deletions counts only if they are a recognised
   major mechanism for this gene.
3. **resources**: [{`type` (patient_organization | disease_specific_variant_database |
   clinical_guideline | genereviews | registry | expert_network | other), `name`, `url`,
   `language`, `country_or_scope`, `audience` (patients | clinicians | labs), `verified`:
   {"fetched": true, "page_title_or_evidence": "…"}}]. Prefer non-commercial, stable sources:
   GeneReviews chapter, disease-specific variant databases, ERKNet / national patient
   organisations (German-language ones are welcome), recent consensus guidelines (KDIGO etc.).
   Max ~8 per entity. Include only URLs you fetched successfully and whose content matches.
   If a well-known resource is down or moved, list it under `rejected_urls` with the reason.

## Output
One JSON file per gene at
`<WORK_DIR>/diag/<SYMBOL>.json`:
```json
{"gene": "…", "entity": {"mondo_id": "…", "disease_name": "…", "moi": "…"},
 "recommended_transcript": {"mane_select_refseq": "NM_…", "mane_select_ensembl": "ENST…",
   "verified_via": "…", "mane_plus_clinical": null, "legacy_numbering_note": "…"},
 "detectability": [], "detectability_note": "…",
 "resources": [], "rejected_urls": [],
 "effort": {"tool_calls": 0, "hard_parts": "…"},
 "schema_feedback": "fields that were missing, ambiguous or hard to fill"}
```
