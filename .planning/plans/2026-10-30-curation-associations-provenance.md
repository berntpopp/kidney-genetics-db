# Curated associations: inheritance, methodology, provenance, diagnostics (#437) Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** `gene_disease_associations` can hold a reviewed curation truthfully (MOI, relationship type, methodology, external provenance, points, diagnostics), the KGDB editor can enter and amend all of it, `/curation/associations`, the gene panel and the MCP show it, and every record still needs confirmation by a KGDB curator other than its author.

**Architecture:** One Alembic revision (0013) adds nullable columns plus check constraints; existing rows and constraints are unchanged. Validation lives in the Pydantic schemas, the workflow in the existing service. The frontend reuses `curationApi`, `useCurationStore` and the shared/ui components; two new display components (`AssociationProvenance`, `AssociationDiagnostics`) are shared by the page and the gene panel. MCP gets one read-only tool over the public list endpoint.

**Tech Stack:** FastAPI, SQLAlchemy, Alembic, Pydantic v2, PostgreSQL 17; Vue 3 + TypeScript, vee-validate + zod, shadcn-vue, Vitest; FastMCP.

**Spec:** GitHub #437 (body + the three maintainer comments of 2026-10-30), #439 comments "v1.1 … diagnostics" (field list) and "Naming"; `.planning/specs/2026-10-30-curation-alpha/`.

## Global Constraints

- The methodology is alpha: never write "v1"/"v1.1"/"v1.2" in code, copy, seeds or tests; use "draft" (e.g. methodology_version `draft iteration 3`).
- Curated associations never feed the evidence score or tier (no pipeline/aggregation code may read the table).
- Every record, KGDB-authored or Gene-Curator-derived, is published only by a KGDB curator/admin other than `curator_id` (existing `ck_gda_distinct_reviewer`, `ck_gda_published_reviewed`, service checks). No constraint is relaxed.
- Gene Curator's export (gene-curator#532) does not exist: no import endpoint, no pinned GC schema, no sync. Follow-up issue only.
- Never invent identifiers or links. MOI CURIEs below were checked against the pinned `hp.json` (HPO 2026-09-01).
- Susceptibility is never shown with the Mendelian `Chip` classification colours or in the Mendelian table.
- Diagnostics are non-scoring; links render only for `http(s)://` URLs, `rel="noopener noreferrer"`, `target="_blank"`.

### Pinned values

| Name | Values |
|---|---|
| `RELATIONSHIP_TYPES` | `mendelian`, `susceptibility` |
| `MENDELIAN_STRENGTHS` | `Definitive`, `Strong`, `Moderate`, `Limited`, `Disputed`, `Refuted`, `No Known Disease Relationship` |
| `SUSCEPTIBILITY_STRENGTHS` | `Established association`, `Likely association`, `Uncertain association` |
| `SOURCES` | `kgdb`, `gene_curator` |
| `MOI_TERMS` (id → label, hp.json 2026-09-01) | HP:0000006 Autosomal dominant inheritance; HP:0000007 Autosomal recessive inheritance; HP:0001417 X-linked inheritance; HP:0001419 X-linked recessive inheritance; HP:0001423 X-linked dominant inheritance; HP:0032113 Semidominant inheritance; HP:0001427 Mitochondrial inheritance; HP:0001450 Y-linked inheritance; HP:0010984 Digenic inheritance; HP:0001426 Non-Mendelian inheritance |
| `MANE_STATUS` | `select`, `plus_clinical`, `none`, `not_checked` |
| `RESOURCE_TYPES` | `patient_organisation`, `registry`, `variant_database`, `guideline`, `other` |
| `VERIFIED_METHODS` | `fetched`, `api`, `captcha_title_only` |
| `SCORE_KEYS` | `genetic`, `experimental`, `total` (each 0–100) |

## Review Focus

1. An existing published KGDB row after the migration: still published, `relationship_type='mendelian'`, `source='kgdb'`, all other columns unchanged (Task 1 migration test).
2. A `javascript:`/`data:` URL in `external_url`, a tool URL or a resource URL is rejected with 422, and the UI never renders a non-http(s) href (Task 2 + Task 4 tests).
3. Changing `relationship_type` on a draft without changing the strength (e.g. susceptibility + `Strong`) answers 422, not 500 from the DB check (Task 2 test).
4. Two records for the same gene and disease with different MOI are both allowed; the same gene+disease+MOI twice (including both MOI null) answers 409 (Task 2 test).
5. A published record with empty diagnostics shows no "Diagnostics & resources" block and no warning on the page or gene panel (Task 4 test).

---

### Task 1: Migration 0013 and model columns

**Files:**
- Create: `backend/alembic/versions/0013_curation_provenance.py`
- Modify: `backend/app/models/gene_disease_association.py`
- Test: `backend/tests/test_migration_0013_curation_provenance.py` (reuse `baseline_db`, `_alembic`, `_add_gene` from `tests/test_audit_migration_views.py`, `INSERT`/`_user` from `tests/test_migration_gene_disease_associations.py`, as 0011's test does)

**Interfaces:**
- Produces (module constants in `app/models/gene_disease_association.py`): `RELATIONSHIP_TYPES`, `MENDELIAN_STRENGTHS`, `SUSCEPTIBILITY_STRENGTHS`, `SOURCES`, `MOI_TERMS: dict[str, str]`; `EVIDENCE_STRENGTHS = MENDELIAN_STRENGTHS + SUSCEPTIBILITY_STRENGTHS` (kept name).
- Columns: `relationship_type String(20) NOT NULL server_default 'mendelian'`, `moi String(10) NULL`, `methodology String(100) NULL`, `methodology_version String(50) NULL`, `source String(20) NOT NULL server_default 'kgdb'`, `external_id String(100) NULL`, `external_url Text NULL`, `external_curator String(255) NULL`, `external_reviewer String(255) NULL`, `scores JSONB NULL`, `diagnostics JSONB NULL`; `evidence_strength` widened to `String(40)`.
- Constraints: `ck_gda_relationship_type` (IN RELATIONSHIP_TYPES); `ck_gda_strength` replaced by `(relationship_type='mendelian' AND strength IN MENDELIAN) OR (relationship_type='susceptibility' AND strength IN SUSCEPTIBILITY)`; `ck_gda_moi` (`moi IS NULL OR moi ~ '^HP:[0-9]{7}$'`); `ck_gda_source` (IN SOURCES); `ck_gda_external` (`source='kgdb' OR (external_id IS NOT NULL AND external_url ~ '^https?://')`); `ck_gda_external_url` (`external_url IS NULL OR external_url ~ '^https?://'`); `ck_gda_scores_object` / `ck_gda_diagnostics_object` (`IS NULL OR jsonb_typeof(..)='object'`); unique index `uq_gda_source_external_id (source, external_id) WHERE external_id IS NOT NULL`; `uq_gda_gene_disease` replaced by `uq_gda_gene_disease_moi UNIQUE NULLS NOT DISTINCT (gene_id, disease_id, moi)`.

- [ ] **Step 1: Write the failing migration tests**
  - `test_0013_keeps_existing_rows`: at 0012 insert a published row (curator ≠ reviewer); upgrade to 0013; row has `relationship_type='mendelian'`, `source='kgdb'`, same status/reviewer/published_at, new columns NULL.
  - `test_0013_constraints`: after upgrade, each of these inserts raises `IntegrityError`: susceptibility + `Strong`; mendelian + `Likely association`; `moi='HP:6'`; `source='gene_curator'` without `external_id`; `external_url='javascript:alert(1)'`; `scores='[1]'`. And these succeed: same gene+disease with `moi` HP:0000006 and HP:0000007; mendelian + `No Known Disease Relationship`.
  - `test_0013_moi_uniqueness`: same gene+disease+moi twice raises; same gene+disease with moi NULL twice raises.
  - `test_0013_downgrade`: upgrade then downgrade to 0012 with only mendelian, MOI-null rows present succeeds and restores `uq_gda_gene_disease`.
- [ ] **Step 2: Run** `cd backend && uv run pytest tests/test_migration_0013_curation_provenance.py -v` → FAIL (no revision 0013).
- [ ] **Step 3: Implement** revision `0013` (`down_revision="0012"`), inline SQL constraint text (no import of model constants at runtime, see the views gotcha). Downgrade deletes nothing: it raises if any susceptibility row, non-null MOI duplicate, or strength longer than 20 chars exists, then drops columns/constraints and restores the old ones. Mirror every column and constraint in the model's `__table_args__`.
- [ ] **Step 4: Run** the new test file and `tests/test_migration_gene_disease_associations.py tests/test_migration_0011_curation_events.py` → PASS.
- [ ] **Step 5: Commit** `feat(curation): add inheritance, provenance and diagnostics columns (#437)`.

### Task 2: Schemas, service and API

**Files:**
- Modify: `backend/app/schemas/gene_disease_association.py`, `backend/app/services/gene_disease_association_service.py`
- Test: `backend/tests/test_gene_disease_associations.py` (extend; follow its client/user fixtures)

**Interfaces:**
- Consumes: Task 1 constants and columns.
- Produces (schemas): `RelationshipType`, `Moi` (Literal of `MOI_TERMS` keys), `Source`, `Scores` (model, fields `genetic|experimental|total: float | None`, `ge=0, le=100`, `extra="forbid"`), `RecommendedTranscript` (`refseq: str|None` pattern `^NM_\d+\.\d+$`, `ensembl: str|None` pattern `^ENST\d{11}\.\d+$`, `mane_status: Literal[MANE_STATUS]`, `legacy_transcript: str|None ≤50`, `numbering_conversion: str|None ≤500`), `DetectabilityTool` (`name ≤100`, `url: HttpLink|None`, `pmid_or_doi: str|None ≤100`), `Detectability` (`challenge 1–300`, `share_of_variants ≤100|None`, `affected_variants ≤300|None`, `methods: list[str ≤50] ≤20`, `tools: list[DetectabilityTool] ≤10`, `negative_report_does_not_exclude: bool = False`, `sources: list[str ≤300] ≤10`), `Resource` (`type: Literal[RESOURCE_TYPES]`, `name 1–200`, `url: HttpLink`, `language: str|None ≤20`, `audiences: list[str ≤50] ≤10`, `maintainer ≤200|None`, `conflict_of_interest ≤500|None`, `verified: {method: Literal[VERIFIED_METHODS], date: date}`), `Diagnostics` (`recommended_transcript|None`, `detectability ≤20`, `resources ≤50`); all `extra="forbid"`. `HttpLink = Annotated[str, ≤2000, AfterValidator(must start http:// or https://)]`.
- `AssociationCreate` / `AssociationUpdate` gain: `relationship_type` (default `mendelian` on create), `moi`, `methodology ≤100`, `methodology_version ≤50`, `source` (default `kgdb`), `external_id ≤100`, `external_url: HttpLink`, `external_curator ≤255`, `external_reviewer ≤255`, `scores: Scores|None`, `diagnostics: Diagnostics|None`. `AssociationResponse` returns all of them plus `moi_label: str|None` (from `MOI_TERMS`).
- Model validator on create: strength must belong to the relationship type; `source='gene_curator'` needs `external_id` and `external_url`. The service re-checks both on the merged record in `update` (the PATCH may change only one side) and raises `DomainValidationError` (422).
- `_ensure_unique(db, gene_id, disease_id, moi, exclude_id)`; uniqueness message names the MOI.

- [ ] **Step 1: Write failing API tests** (names and assertions):
  - `test_create_susceptibility_record`: POST `relationship_type=susceptibility`, `evidence_strength="Likely association"`, `moi="HP:0001426"` → 201; GET public after publish by a second curator lists it with `moi_label="Non-Mendelian inheritance"`.
  - `test_strength_must_match_relationship_type`: POST susceptibility + `Strong` → 422; PATCH a mendelian draft to `relationship_type=susceptibility` only → 422.
  - `test_no_known_only_mendelian`: mendelian + `No Known Disease Relationship` → 201; susceptibility + it → 422.
  - `test_gene_curator_source_needs_provenance`: `source=gene_curator` without `external_url` → 422; with `external_id="GC-1"` and `external_url="https://example.org/c/1"` → 201, and the same `external_id` again → 409.
  - `test_rejects_non_http_links`: `external_url="javascript:alert(1)"`, a resource url `data:text/html,x`, a tool url `ftp://x` → each 422.
  - `test_diagnostics_round_trip`: the MUC1-shaped payload (mane_status `none`, one detectability with `negative_report_does_not_exclude=true`, one resource with `verified.date`) is returned unchanged; unknown key in `diagnostics` → 422; `mane_status="maybe"` → 422.
  - `test_unique_per_moi`: same gene+disease with HP:0000006 and HP:0000007 → both 201; HP:0000006 again → 409; two with MOI omitted → second 409.
  - `test_imported_record_needs_distinct_confirmer`: a `gene_curator` draft created and submitted by curator A cannot be published by A (403) and is published by B (200). (Existing rule, pinned for imported records.)
- [ ] **Step 2: Run** `cd backend && uv run pytest tests/test_gene_disease_associations.py -v` → new tests FAIL.
- [ ] **Step 3: Implement** the schema types and service checks above; `to_response` adds `moi_label`. Routers stay unchanged.
- [ ] **Step 4: Run** the file → PASS; `uv run ruff check --no-fix app/ && uv run ruff format --check app/ tests/`.
- [ ] **Step 5: Commit** `feat(curation): validate relationship type, MOI, provenance and diagnostics (#437)`.

### Task 3: MCP read-only tool

**Files:**
- Modify: `mcp/src/kidney_genetics_mcp/client/allowlist.py`, `mcp/contract/openapi.snapshot.json` (regenerated from the backend app, see Step 3), generated `mcp/src/kidney_genetics_mcp/contract/_generated_*.py` (via `make -C mcp contract` only), `mcp/src/kidney_genetics_mcp/tools/__init__.py`
- Create: `mcp/src/kidney_genetics_mcp/services/curation.py`, `mcp/src/kidney_genetics_mcp/tools/curation.py`
- Test: `mcp/tests/test_tool_curation.py`; extend `mcp/tests/test_contract_drift.py` consumed/denied lists and `mcp/tests/test_tool_allowlist_security.py`

**Interfaces:**
- Consumes: public `GET /api/curation/associations/` (`gene_symbol`, `limit`, `offset`) with the Task 2 response.
- Produces: allow rule `^/api/curation/associations/?$`; explicit deny `^/api/curation/associations/(workflow|\d+)`; tool `kgdb_list_curated_associations(gene_symbol: str | None = None, relationship_type: Literal["mendelian","susceptibility"] | None = None, response_mode: ResponseMode | None = None)` with the same annotations as the other read-only tools; service `list_curated_associations(client, *, gene_symbol, relationship_type, response_mode) -> dict` returning `{"associations": [...], "total": int}`, filtered client-side by relationship type; `minimal` = gene, disease, relationship_type, strength, moi; `full` adds diagnostics and citations.

- [ ] **Step 1: Write failing tests**: allowlist allows `GET /api/curation/associations/` and denies `/workflow`, `/5`, `/5/publish` and any POST; tool returns only `susceptibility` rows when filtered; `minimal` omits `diagnostics`; the tool's docstring says the records are expert-reviewed and are not part of the evidence score.
- [ ] **Step 2: Run** `make -C mcp check` → FAIL.
- [ ] **Step 3: Implement**; refresh the snapshot with `cd backend && uv run python -c "import json; from app.main import app; print(json.dumps(app.openapi(), indent=2))" > ../mcp/contract/openapi.snapshot.json` (first confirm on unmodified `main` that this reproduces the committed file byte for byte; if not, stop and match the committed format). Then `make -C mcp contract` and review the generated diff.
- [ ] **Step 4: Run** `make -C mcp check && make -C mcp contract-verify` → PASS.
- [ ] **Step 5: Commit** `feat(mcp): add read-only curated-associations tool (#437)`.

### Task 4: Display on /curation/associations and the gene panel

**Files:**
- Modify: `frontend/src/api/curation.ts` (types + constants mirroring the pinned values, `isHttpUrl(url): boolean`), `frontend/src/views/CuratedAssociations.vue`, `frontend/src/components/gene/GeneCuratedAssociations.vue`
- Create: `frontend/src/components/curation/AssociationProvenance.vue`, `frontend/src/components/curation/AssociationDiagnostics.vue`
- Test: `frontend/src/components/curation/__tests__/AssociationProvenance.spec.ts`, `__tests__/AssociationDiagnostics.spec.ts`, `frontend/src/components/gene/__tests__/GeneCuratedAssociations.spec.ts`

**Interfaces:**
- Consumes: Task 2 response fields.
- Produces: `Association` gains the Task 2 fields; constants `MENDELIAN_STRENGTHS`, `SUSCEPTIBILITY_STRENGTHS`, `MOI_TERMS`, `RELATIONSHIP_LABELS`; `<AssociationProvenance :record>` (MOI label + CURIE, methodology + version, "Curated in Gene Curator ↗" link with external curator/reviewer when `source==='gene_curator'`, points when present); `<AssociationDiagnostics :diagnostics>` (renders nothing when null or all lists empty; transcript with MANE status and numbering note; detectability items with an `Alert` "A negative short-read result does not exclude a variant here" when any item has `negative_report_does_not_exclude`; resources as links with "verified <date>").
- The page shows two published tables, "Mendelian gene–disease validity" and "Susceptibility (risk) associations"; the latter uses a neutral `Badge` with the strength text, never `Chip :classification`. The gene panel groups the same way. The workflow table shows provenance + diagnostics so the confirming reviewer sees what they publish, plus a "Gene Curator import" badge for `source==='gene_curator'`.

- [ ] **Step 1: Write failing Vitest specs**: diagnostics renders resource links with `href` equal to the URL and `rel="noopener noreferrer"`; a `javascript:` URL renders as plain text (no anchor); the warning appears only with the flag; null diagnostics renders nothing; provenance shows "Autosomal recessive inheritance" for HP:0000007 and a Gene Curator link only for that source; gene panel puts a susceptibility record under the susceptibility heading and not in a `Chip`.
- [ ] **Step 2: Run** `cd frontend && npm run test:run -- curation GeneCuratedAssociations` → FAIL.
- [ ] **Step 3: Implement** with existing `Card`, `Badge`, `Alert`, `OntologyTerm` components.
- [ ] **Step 4: Run** `npm run lint:check && npm run format:check && npm run test:run && npm run build` → PASS.
- [ ] **Step 5: Commit** `feat(curation): show inheritance, provenance and diagnostics (#437)`.

### Task 5: Editor fields

**Files:**
- Modify: `frontend/src/components/curation/AssociationForm.vue`
- Test: `frontend/src/components/curation/__tests__/AssociationForm.spec.ts`

**Interfaces:**
- Consumes: Task 4 constants and `AssociationInput` (extended with the Task 2 create fields).
- Produces: form sections "Classification" (relationship type select; strength options switch with it and reset when the current one does not fit; MOI select from `MOI_TERMS`), "Methodology & provenance" (methodology, version, source select; external ID/URL/curator/reviewer shown and required for `gene_curator`; genetic/experimental/total points), "Diagnostics & resources" (transcript fields; add/remove rows for detectability and resources; each row's fields as in Task 2). Empty diagnostics are sent as `null`.

- [ ] **Step 1: Write failing specs**: switching to susceptibility offers only the three susceptibility strengths; `gene_curator` without URL blocks submit with a message; adding one resource row and saving emits `diagnostics.resources[0]` with `verified.date`; editing a record with diagnostics pre-fills the rows; every input has a `<Label for>`.
- [ ] **Step 2: Run** `npm run test:run -- AssociationForm` → FAIL.
- [ ] **Step 3: Implement** (zod schema mirrors Task 2; API stays authoritative).
- [ ] **Step 4: Run** lint, format, `test:run`, `build` → PASS.
- [ ] **Step 5: Commit** `feat(curation): edit inheritance, provenance and diagnostics (#437)`.

### Task 6: Follow-up and handoff

- [ ] Open issue "feat(curation): import Gene Curator exports as drafts" referencing #437 and gene-curator#532: pinned export schema + drift check, upsert by `(source, external_id)`, never overwrite a KGDB-edited record without a diff, unknown MOI/verdict rejected, gene missing in KGDB reported.
- [ ] `make check` (backend part needs the test DB at head), `git diff --check`; PR body lists the migration, contract regeneration, verification commands and results.
