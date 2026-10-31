# Curation methodology: alpha drafts (2026-10-30)

Working material from the Gene Curator integration (#437, #438, #439). **Alpha**: these are draft
rules (now draft iteration 8), not versioned releases. `<WORK_DIR>` stands for the folder an agent
writes its outputs to; `<OUT_DIR>` / `<JUDGE_DIR>` for its curation and judge output folders.

- `BRIEF_CURATOR_DRAFT.md`: blind curator-agent brief (draft iteration 8: per-allele scoring,
  strict functional support, mandatory discovery steps)
- `BRIEF_JUDGE.md`: judge-agent brief (verify every row, then complete missing evidence)
- `BRIEF_ADJUDICATOR.md`: non-blind adjudicator that compares a disagreement with the ClinGen report
- `PROMPT_PRODUCTION.md`: production prompt for LLM curation in Gene Curator (GC MCP + GeneFoundry;
  adopts ClinGen first, not blind, saves via GC tools, approved #473 susceptibility rules). The
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
