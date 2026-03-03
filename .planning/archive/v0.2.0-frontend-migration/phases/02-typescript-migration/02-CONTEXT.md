# Phase 2: TypeScript Migration - Context

**Gathered:** 2026-02-28
**Status:** Ready for planning

<domain>
## Phase Boundary

Migrate all non-component JavaScript files (stores, API modules, composables, utils, router, services — 34 files total) to TypeScript with zero visual changes. Phase 1 established the TypeScript toolchain (`allowJs: true`, `checkJs: false`, `verbatimModuleSyntax: true`) and foundation types (`src/types/`). This phase adds full typing to the non-component layer so that all subsequent Vue component migrations receive typed data.

</domain>

<decisions>
## Implementation Decisions

### Type precision for API data
- Create specific typed interfaces for each of the 9 annotation sources (ClinGen, GenCC, HPO, PanelApp, PubTator, DiagnosticPanels, etc.) — replace `Record<string, unknown>` on `source_data` and `annotations` fields with per-source types
- Frontend-centric types: type what the frontend actually consumes, not a mirror of backend Pydantic schemas — if the UI never reads a field, don't type it
- Same typing depth for all 12 API modules — no distinction between public and admin; all get full typed return values
- All API modules return typed response interfaces using the JSON:API wrapper types from `src/types/api.ts`

### Runtime validation
- TypeScript compile-time types only — no Zod validation at API response boundaries
- Zod remains available for form validation in later phases (Phase 3+ auth modals, Phase 7 admin forms) but is not used for API response parsing in Phase 2

### Test depth
- API module tests: Mock the Axios client and verify request construction (correct URL, params, headers) — ~2-3 tests per module
- Store tests: Full state + behavior tests — verify actions update state, getters return expected values, auth flow works end-to-end — ~5-8 tests per store
- Utility tests and composable test depth are at Claude's discretion based on complexity and usage

### Claude's Discretion
- Type definition file organization (single evidence.ts vs per-source files in types/evidence/)
- API response typing mechanism (Axios generics vs type assertions)
- Error handling approach (typed error objects vs bubble-up)
- Axios interceptor typing depth
- Which utilities warrant dedicated test files vs being tested through integration
- Composable test depth per composable (based on complexity)

</decisions>

<specifics>
## Specific Ideas

- Phase 1 already created foundation types in `src/types/` (api.ts, auth.ts, gene.ts, pipeline.ts, index.ts) — extend this structure
- The `GeneDetail.annotations` field (`Record<string, unknown>`) and `EvidenceSource.source_data` (`Record<string, unknown>`) are the primary targets for per-source typing
- 9 annotation sources to type: ClinGen, GenCC, HPO, PanelApp, PubTator, DiagnosticPanels, and any others in the pipeline
- Backend Pydantic schemas in `backend/app/schemas/` can be referenced for field discovery, but frontend types should only include consumed fields

</specifics>

<deferred>
## Deferred Ideas

None — discussion stayed within phase scope

</deferred>

---

*Phase: 02-typescript-migration*
*Context gathered: 2026-02-28*
