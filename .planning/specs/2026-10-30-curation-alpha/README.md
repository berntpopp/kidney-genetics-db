# Curation methodology: alpha drafts (2026-10-30)

Working material from the Gene Curator integration (#437, #438, #439). **Alpha**: these are draft
rules (now draft iteration 8), not versioned releases. `<WORK_DIR>` stands for the folder an agent
writes its outputs to; `<OUT_DIR>` / `<JUDGE_DIR>` for its curation and judge output folders.

- `BRIEF_CURATOR_DRAFT.md`: blind curator-agent brief (draft iteration 8: per-allele scoring,
  strict functional support, mandatory discovery steps)
- `BRIEF_JUDGE.md`: judge-agent brief (verify every row, then complete missing evidence)
- `BRIEF_ADJUDICATOR.md`: non-blind adjudicator that compares a disagreement with the ClinGen report
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

Still part of the alpha methodology. The KGDB tiers follow the ClinGen low-penetrance/risk-allele
scheme (Schmidt 2024, PMID 38054408): `Established association`, `Likely association`,
`Uncertain association` and `Refuted association`. Gene Curator class keys `established`,
`likely`, `uncertain` and `refuted` map to them on import. The point model, bands and caps are in
the approved proposal on #473; the 500-case size cut-off also applies to rare phenotypes such as
aHUS.

- **APOL1**: kept as ClinGen's Glomerulopathy GCEP curated it, Mendelian Definitive (AR), not
  re-recorded as a susceptibility `Established association`. Entities ClinGen curated on the
  Mendelian SOP are adopted as is.
