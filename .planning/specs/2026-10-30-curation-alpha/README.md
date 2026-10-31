# Curation methodology v1 (2026-10-31)

Working material from the Gene Curator integration (#437, #438, #439). **v1** (declared by the
maintainer 2026-10-31): `PROMPT_PRODUCTION.md` is the v1 production prompt, built on draft
iteration 8 of the rules. The `BRIEF_*` files remain the blind test harness. `<WORK_DIR>` stands for the folder an agent
writes its outputs to; `<OUT_DIR>` / `<JUDGE_DIR>` for its curation and judge output folders.

- `BRIEF_CURATOR_DRAFT.md`: blind curator-agent brief (draft iteration 8: per-allele scoring,
  strict functional support, mandatory discovery steps)
- `BRIEF_JUDGE.md`: judge-agent brief (verify every row, then complete missing evidence)
- `BRIEF_ADJUDICATOR.md`: non-blind adjudicator that compares a disagreement with the ClinGen report
- `WORKFLOW.md`: the end-to-end Gene Curator → KGDB workflow (curate, export, upload, confirm)
- `PROMPT_PRODUCTION.md`: production prompt for LLM curation in Gene Curator (GC MCP + GeneFoundry;
  records ClinGen and curates every entity in full, not blind, saves via GC tools, approved #473 susceptibility rules). The
  `BRIEF_*` files above are the blind test harness it was calibrated with.
- `BRIEF_DIAGNOSTICS.md`: non-scoring clinical diagnostics section (transcript, detectability, resources)
- `TOOL_POLICY.md`: GeneFoundry-first tool use, retry and fallback rules
- `score_draft.py`: deterministic scorer; `--it 8` is the current rule set (lower values reproduce
  earlier iterations). It expects an answer key at `key/answer_key.json` next to it (not committed).
- `RESULTS.md`: blind calibration against ClinGen (iterations 4–8, 105 genes) and recommendations
- `point_model_draft.json`: Gene Curator point model used in the iteration-3 calibration (flat
  proband points; per-allele scoring needs explicit per-row points)
- `simulate.py`: offline simulation of the #438 filter and the HPO-root change (expects downloaded
  hp.json, phenotype.hpoa, genes_to_phenotype.txt, the GenCC TSV and KGDB gene sources next to it)

Results and decisions live in the issues, mainly #439.

## Susceptibility tiers (#473, approved 2026-10-31)

Part of methodology v1. The KGDB tiers follow the ClinGen low-penetrance/risk-allele
scheme (Schmidt 2024, PMID 38054408): `Established association`, `Likely association`,
`Uncertain association` and `Refuted association`. Gene Curator class keys `established`,
`likely`, `uncertain` and `refuted` map to them on import. The point model, bands and caps are in
the approved proposal on #473; the 500-case size cut-off also applies to rare phenotypes such as
aHUS.

- **ClinGen-curated entities (2026-10-31)**: curated in full like any other entity, with ClinGen's
  class cited beside ours; a different class needs a written reason. APOL1 (ClinGen Glomerulopathy
  GCEP: Mendelian Definitive, AR) is re-curated under these rules; if it comes out as a
  susceptibility `Established association`, the maintainer confirms before publishing.
