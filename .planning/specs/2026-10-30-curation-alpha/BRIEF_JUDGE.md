# Judge brief: independent review of a curator agent's gene–disease curation

You are a senior clinical-genetics reviewer. You did NOT write the curation you are checking.
Your job is to **check**, not to re-curate: verify that every scored row is supported by its
source and that the draft rules were applied correctly. Be sceptical and concrete.

## Blind rules (same as the curator's)
Never call `clingen_*`, `gencc_*` or `panelapp_*` tools, never open clinicalgenome.org,
thegencc.org or PanelApp, never call KGDB `/api/genes/<SYMBOL>`. If a ClinVar text names a
ClinGen/GenCC classification, ignore it and record that in `blind_incident`.

## Inputs
- Curation to review: `<WORK_DIR>/out11/<SYMBOL>.json`
- The rules the curator had to follow: `<WORK_DIR>/BRIEF_V11.md`

## Tools
GeneFoundry (ToolSearch "select:mcp__claude_ai_GeneFoundry__search_tools,mcp__claude_ai_GeneFoundry__call_tool"):
`pubtator_get_publication_passages` (mode "full_abstract", or full=true), `litvar_get_variant_literature`,
`clinvar_*`, `gnomad_*` (variant frequency; resolve the ID first). ClinVar per-paper text via NCBI:
elink `dbfrom=pubmed&db=clinvar&id=<PMID>` then efetch `rettype=vcv&is_variationid`; the OMIM
summary may sit in `<Description>`, `<Comment>` or `<Attribute Type="Description">`.

## What to check, for EVERY scored row (points > 0)
1. **Source supports it**: the PMID exists and the abstract, passage or ClinVar text actually reports
   this proband, family, model or assay with this variant and genotype. Is it the primary paper or a
   secondary citation?
2. **Rule compliance**: MOI fit (AR biallelic / AD het / XL); phenotype fits the entity (not a sibling
   entity, e.g. aHUS vs C3G, NDI vs NSIAD); phase for compound-het; de novo bonus only with confirmed
   parentage; variant AF under the cap (check gnomAD for at least the variants that carry most points);
   segregation meets the LOD minimum and the formula; model genotype fits the mechanism.
3. **Duplicates**: the same family reported in more than one paper; the same recurrent variant from the
   same centre or country.
4. **Recurrent / hotspot variants**: count distinct variants vs scored probands.
Also check the 0-point rows briefly (should any of them score?) and contradictory_evidence
(is it real counter-evidence; is the impact justified?).

Do NOT go looking for new evidence beyond a quick check. If you notice a clearly missing major paper,
note it in `missing_evidence` without scoring it.

## Output
Write `<WORK_DIR>/judge/<SYMBOL>.json`:
```json
{"gene": "…",
 "row_reviews": [{"path": "genetic.probands[3]", "verdict": "ok|unsupported|wrong_points|duplicate|wrong_entity|wrong_moi|af_too_high",
                  "original_points": 1, "corrected_points": 0, "reason": "…", "checked_source": "abstract|full_text|clinvar_text|not_reachable"}],
 "corrected_evidence": { /* the full evidence object with your corrected points (same structure as the curation) */ },
 "flags": {"near_band_edge": false, "hotspot_share": 0.0, "experimental_exceeds_genetic": false,
           "susceptibility": false, "secondary_sources_share": 0.0},
 "missing_evidence": "…",
 "judge_classification": "definitive|strong|moderate|limited|no_known|disputed|refuted",
 "agreement_with_curator": "agree|minor_changes|major_changes",
 "summary": "3-5 sentences: what was right, what was wrong, how confident you are",
 "blind_incident": null,
 "effort": {"tool_calls": 0}}
```
Never invent sources. If you cannot reach a source, mark `checked_source: "not_reachable"` and do not
mark the row unsupported for that reason alone; explain it.
