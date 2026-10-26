# Reviewed gene–disease association records (#26)

Status: implemented (migration 0007). Maintainer decisions of 2026-10-26: store
MONDO and OMIM IDs only; published records are publicly visible.

## Record

`gene_disease_associations` holds one row per (gene, disease) pair. A gene can
have many diseases; the same disease can be recorded only once per gene
(`uq_gda_gene_disease`, API 409). Fields: gene, `disease_id`, curator-entered
`disease_name` (a short label), `evidence_strength`, `citations` (PMIDs, at
least one), an optional `evidence_summary` (≤2000 characters), status,
curator/reviewer user ids, and `created_at`, `updated_at`, `submitted_at`,
`reviewed_at`, `published_at`. A gene that has records cannot be deleted
(no cascade). Deleting a user who authored or reviewed a record returns 409;
deactivate that user instead, so provenance is kept.

## Identity rules

- `disease_id` must be `MONDO:` plus 7 digits or `OMIM:` plus 6 digits. Input is
  trimmed and upper-cased. Both the API and a database CHECK enforce this.
  Malformed request bodies get the app-wide `400 VALIDATION_ERROR`; a
  well-formed body naming an unknown gene gets 422.
- HPO identifiers (`HP:`) describe phenotypes, not diseases. They are rejected
  with an explicit message and are never treated as disease IDs. The automated
  HPO evidence elsewhere in KGDB stays separate from these records.
- Free text is only a label: `disease_name` never establishes identity. The ID
  does that. No ontology lookup checks that the name matches the ID; the
  reviewer checks it.
- Citations are PubMed IDs. `12345678` and `PMID:12345678` are both accepted and
  stored as `PMID:12345678`. Duplicates are removed. Other identifiers (DOI, PMC)
  are rejected. A database CHECK enforces the stored form.
- Evidence strength follows the ClinGen gene–disease validity classes:
  Definitive, Strong, Moderate, Limited, Disputed, Refuted.
- KGDB stores and shows only IDs and outbound links (MONDO → Monarch,
  OMIM → omim.org/entry, PMID → PubMed). No OMIM text is copied. The maintainer
  still owes a check of OMIM's terms of use for redistributing OMIM identifiers.

## Workflow and visibility

`draft → in_review → published`; curators and admins act, nobody else.

| Action | Allowed from | Who |
|---|---|---|
| create (always a draft) | – | any curator/admin |
| edit (PATCH) | draft | author only |
| submit | draft | author only |
| publish | in_review | curator/admin other than the author |
| return to draft | in_review, published | curator/admin other than the author |

- Self-publication returns 403, and the database enforces
  `reviewer_id <> curator_id`. A published row must have a reviewer and
  `published_at`.
- Published records cannot be edited (409). To fix one, a reviewer returns it
  to draft, which removes it from public view. The author then edits it and
  submits it again.
- `reviewer_id`/`reviewed_at` record the most recent review action (publish or
  return). Full history, comments and templates are deferred (original #26
  scope).
- Public: `GET /api/curation/associations/` lists published records only.
  Curators/admins: `GET /api/curation/associations/workflow` lists every status.
  Anonymous callers get 401 on write and workflow routes; viewers get 403.

## Automated data

Only the curation model, schema, service and router reference this table. No
pipeline, aggregation or view code does, and
`tests/test_gene_disease_associations.py::test_no_pipeline_code_writes_expert_records`
enforces this. Automated evidence updates therefore cannot overwrite expert
decisions. Migration 0007 only creates the table. Downgrade drops only this table.
