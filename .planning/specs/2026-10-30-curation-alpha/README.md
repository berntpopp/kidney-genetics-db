# Curation methodology: alpha drafts (2026-10-30)

Working material from the Gene Curator integration (#437, #438, #439). **Alpha**: these are draft
rules, not versioned releases. `<WORK_DIR>` stands for the folder an agent writes its outputs to.

- `BRIEF_CURATOR_DRAFT.md`: blind curator-agent brief (draft iteration 3 rules)
- `BRIEF_JUDGE.md`: independent judge-agent brief that checks a curation row by row
- `BRIEF_DIAGNOSTICS.md`: non-scoring clinical diagnostics section (transcript, detectability, resources)
- `TOOL_POLICY.md`: GeneFoundry-first tool use, retry and fallback rules
- `point_model_draft.json`: Gene Curator point model used in the calibration (passes GC's validator)
- `simulate.py`: offline simulation of the #438 filter and the HPO-root change (expects downloaded
  hp.json, phenotype.hpoa, genes_to_phenotype.txt, the GenCC TSV and KGDB gene sources next to it)

Results and decisions live in the issues, mainly #439.
