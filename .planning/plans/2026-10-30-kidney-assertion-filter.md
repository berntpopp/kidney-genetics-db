# Plan: ontology-based kidney filter for GenCC and ClinGen assertions (#438)

Status: approved by the maintainer on 2026-10-30, on the condition that a per-gene tier
dry run is reviewed before release.

## Problem

GenCC and ClinGen assertions are kept only when the disease text contains a kidney
keyword (`keywords.yaml`). Kidney diseases named without one (primary hyperoxaluria,
Gitelman, Bartter, Fabry, cystinuria, Dent, aHUS, …) are dropped. 48 of the 287
`comprehensive_support` genes therefore have no ClinGen/GenCC evidence at all.

## Rule

Keep an assertion when **either** holds:

1. **keyword**: today's `matches_kidney_keyword` (unchanged); or
2. **hpo_panel**: HPO annotates this gene–disease pair with at least one term under
   *Abnormality of the kidney* (HP:0000077) **and** the gene already has PanelApp or
   DiagnosticPanels evidence in KGDB.

Simulation on 2026-10-30 (#438 comment): 376 → 722 genes with a GenCC assertion of Limited
or stronger; 48/48 recovered; +346 others, mostly kidney genes missed today (CLCN5, CD46,
CASR, CLCNKA, CLDN10, ALDOB). Alternatives that were measured and rejected: any kidney term
(+1030), ≥3 terms (34/48 recovered).

The HPO root of the HPO evidence source (HP:0010935) is **not** changed. Measured: lower-tract
kidney genes are already included, and widening it adds noise.

## Data (all already pinned and sha256-checked in KGDB, no new download)

- `hp.json` (HPO 2026-09-01; `HPO.hp_json_url`): descendants of HP:0000077 (`load_hpo_parents`).
- `genes_to_phenotype.txt` (`HPO.genes_to_phenotype_url`): rows of gene_symbol, hpo_id, disease_id
  (OMIM/ORPHA) give the kidney gene–disease pairs.
- MONDO SSSOM (`mondo.sssom_url`, exactMatch only): MONDO → OMIM/Orphanet, so GenCC/ClinGen MONDO
  IDs can be matched to HPO disease IDs. Also use GenCC's own `disease_original_curie`.
- Panel genes: a DB query for genes with `gene_evidence.source_name` in (PanelApp, DiagnosticPanels).

## Design (smallest change)

- New module `app/pipeline/sources/unified/kidney_assertions.py`:
  `KidneyAssertionIndex` with `matches(gene_symbol, disease_ids) -> bool`, built once per run from
  the three pinned files plus the panel-gene query. It reuses `verify_sha256`, `load_hpo_parents`
  and the bulk download helpers, and adds no new configuration except one key:
  `kidney_assertion_hpo_root: HP:0000077`.
- `GenCCUnifiedSource.is_kidney_related` and `ClinGenUnifiedSource.is_kidney_related`: keyword OR
  `index.matches(...)`. Each kept assertion records `kidney_match: keyword | hpo_panel` in its
  evidence data, for provenance and display.
- If the index cannot be built (file or hash failure), log an error, record
  `kidney_filter: keyword_only` in the source metadata, and keep today's behaviour. Never
  silently drop more than today.
- Ordering: the panel gate reads the DB as it is at run time. On a first seed, GenCC/ClinGen may
  run before the panels exist; the next scheduled run corrects this. Documented, no new scheduler
  logic.

## Tests

- Unit: index from tiny fixture files (hp parents, g2p rows, SSSOM rows, panel set). Keyword-only
  pass; hpo_panel pass; kidney term without a panel gene → reject; panel gene without a kidney
  term → reject; MONDO resolved via SSSOM; obsolete or ambiguous mapping ignored.
- Source tests: GenCC and ClinGen keep the AGXT/primary hyperoxaluria row through hpo_panel, and
  a non-kidney row stays out.
- Fallback: index build failure → keyword-only and metadata flag.

## Dry run and release gate

1. A local DB restored from the latest production backup.
2. Run the GenCC and ClinGen updates through the existing pipeline API (`/api/pipeline/` or
   `/api/annotations/pipeline/`), then refresh views.
3. Export the per-gene evidence count, score and tier before and after → a CSV for maintainer
   review (genes changing tier, genes gaining assertions only via `hpo_panel`).
4. Release only after approval; the release notes state the number of genes that changed tier.

## Out of scope

The HPO source root, PanelApp keyword filtering, and display of `kidney_match` in the UI (follow-up).
