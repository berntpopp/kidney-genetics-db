# Plan: HPO neoplasia clinical group with descendant matching (#338)

Status: superseded and implemented. The `neoplasia` group ships with root
HP:0009726 (Renal neoplasm) and descendant matching in the clinical-groups v2
classifier (commit daf11f5, spec `.planning/specs/2026-10-26-hpo-clinical-groups-v2.md`).
The design below is the original proposal and is kept as a record.

## Goal

Kidney-tumour / cancer-predisposition genes (FH, VHL, PALB2, ...) currently get
a `clinical_group.primary` from one incidental term, because there is no
neoplasia group and `_classify_clinical_group` matches signature terms exactly.

## Candidate signature terms (curator to confirm)

IDs resolved with the HPO resolver (`hpo_resolve_term`, HPO release 2026-09-01,
none obsolete). Membership is a curation decision, not settled by this plan.

| HPO ID | Label | Role |
|---|---|---|
| HP:0009726 | Renal neoplasm | proposed root |
| HP:0005584 | Renal cell carcinoma | signature |
| HP:0006770 | Clear cell renal cell carcinoma | signature |
| HP:0006732 | Papillary renal cell carcinoma type 2 | signature |
| HP:0002667 | Nephroblastoma | signature |
| HP:0006772 | Renal angiomyolipoma | signature |

Curator questions: is each term a descendant of HP:0009726 (if so, the root
alone may suffice); should non-renal cancer-predisposition terms count; should
the group be named `neoplasia`.

## Design

1. `backend/config/datasources.yaml` `HPO.clinical_groups`: add
   `neoplasia` with `signature_terms`, `name`, `weight: 1.0`.
2. Descendant matching: expand each group's signature terms through
   `HPOTerms.get_descendants(..., include_self=True)` (the same call
   `get_hpo_term_descendants` in `backend/app/core/hpo/terms.py` wraps, and
   that `get_classification_term_descendants` already uses for onset and
   syndromic groups). Extend `get_classification_term_descendants` to read
   `signature_terms` and give `clinical_groups` its own cache slot (today it
   caches only `onset_groups` and `syndromic_indicators`).
3. Scoring stays per signature term: a signature term counts as matched when
   the gene has that term or any descendant. Keeps the score in [0, 1] and
   comparable across groups of 5 terms. Applying descendants to all six
   existing groups changes their outputs too; decide whether to roll out for
   neoplasia only first.
4. Add `neoplasia` to `CLINICAL_GROUP_PRIORITY` (annotations/hpo.py, #254).
   Its position decides ties; placing it last keeps all current tied
   primaries unchanged.
5. Out of scope here, separate decisions in #338: secondary groups and a
   minimum-evidence rule for `primary`; frontend chip/filter/network colours.

## Data impact (dev DB, read-only, 2026-10-21)

133 genes with HPO annotations carry at least one of the six terms above as an
exact phenotype ID (lower bound; descendants will add more). Their current
primary: none 49, cakut 34, complement 27, cyst_cilio 9, nephrolithiasis 9,
tubulopathy 4, glomerulopathy 1. Expect most of these to move to neoplasia.
Stored results change only after a managed HPO annotation refresh via
`/api/annotations/pipeline/update` (strategy=full, source hpo), followed by
the materialized-view refresh for `gene_hpo_classifications`.

## Tests

- Unit (mocked descendants): a gene with only a descendant of a signature term
  (e.g. clear cell RCC under RCC) scores for that group.
- Real-YAML test: `neoplasia` exists and its terms are valid HP IDs.
- Fixture cases from #338: FH, VHL -> neoplasia; HNF1B stays cakut. Use
  phenotype sets captured from current annotations, not live API calls.
- Existing tie-break and syndromic tests stay green.
