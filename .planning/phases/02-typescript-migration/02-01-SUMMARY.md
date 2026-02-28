---
phase: 02-typescript-migration
plan: 01
subsystem: ui
tags: [typescript, types, evidence, logging, vuetify, utils, config]

# Dependency graph
requires:
  - phase: 01-foundation-setup
    provides: tsconfig.app.json with allowJs/checkJs/verbatimModuleSyntax, env.d.ts skeleton, src/types/ directory

provides:
  - Per-source evidence type interfaces (ClinGen, GenCC, HPO, PanelApp, PubTator, DiagnosticPanels, Literature)
  - EvidenceData union type replacing Record<string, unknown> in EvidenceSource.source_data
  - LogEntry/LogLevel types for log store and service typing
  - Window augmentations (logService, _env_, snackbar) in env.d.ts
  - ImportMetaEnv augmentation (VITE_API_URL, VITE_WS_URL)
  - DebouncedFunction<T> generic interface for typed debounce usage
  - TierName/GroupName union types and typed TIER_CONFIG/SCORE_RANGES
  - All 11 utility .js files renamed to .ts with full type annotations
  - Both config .js files renamed to .ts with typed config objects
  - vuetify.js renamed to vuetify.ts

affects:
  - 02-02 (API modules, services, stores — depend on types and utils established here)
  - 02-03 (composables — depend on debounce.ts, networkStateCodec.ts, wildcardMatcher.ts)
  - 03 (component migration — depends on EvidenceData type for evidence panels)

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "verbatimModuleSyntax: use import type for type-only imports in all .ts files"
    - "Window augmentation in env.d.ts (not inline declarations) for global types"
    - "Per-source evidence type union for discriminated evidence data access"
    - "DebouncedFunction<T> generic interface pattern for function type wrappers"

key-files:
  created:
    - frontend/src/types/evidence.ts
    - frontend/src/types/log.ts
  modified:
    - frontend/env.d.ts
    - frontend/src/types/gene.ts
    - frontend/src/types/index.ts
    - frontend/src/utils/debounce.ts
    - frontend/src/utils/wildcardMatcher.ts
    - frontend/src/utils/stateCompression.ts
    - frontend/src/utils/formatters.ts
    - frontend/src/utils/adminBreadcrumbs.ts
    - frontend/src/utils/adminIcons.ts
    - frontend/src/utils/publicBreadcrumbs.ts
    - frontend/src/utils/logSanitizer.ts
    - frontend/src/utils/evidenceTiers.ts
    - frontend/src/utils/networkStateCodec.ts
    - frontend/src/utils/version.ts
    - frontend/src/config.ts
    - frontend/src/config/networkAnalysis.ts
    - frontend/src/plugins/vuetify.ts

key-decisions:
  - "Window augmentation uses inline WindowLogService interface (not import from logService.js) to avoid circular dependency before logService is migrated"
  - "EvidenceData union includes Record<string, unknown> fallback for HGNC/gnomAD/GTEx sources not rendered by frontend views"
  - "networkStateCodec.ts: logService.warning() (non-existent) fixed to logService.warn() (Rule 1 bug fix)"
  - "debounce.ts flush() accepts args for type compatibility but uses lastArgs internally (documented behavior from Pitfall 5)"
  - "stateCompression.ts error call: merged 3rd arg into data object to match WindowLogService 2-param signature"

patterns-established:
  - "BreadcrumbItem interface: { title: string; to?: string | null; disabled: boolean } — consistent across admin/public breadcrumbs"
  - "Config files use explicit interface types (AppConfig, NetworkAnalysisConfig) not inline object types"
  - "Utility functions use explicit parameter and return types (no inference from untyped params)"

# Metrics
duration: 9m 36s
completed: 2026-02-28
---

# Phase 02 Plan 01: Foundation Types and Utility Migration Summary

**14 Tier 1/2 JS files migrated to TypeScript plus 3 new type definition files — evidence unions, log types, Window augmentations enabling typed access to window.logService/_env_/snackbar across all remaining migration work**

## Performance

- **Duration:** 9m 36s
- **Started:** 2026-02-28T10:57:41Z
- **Completed:** 2026-02-28T11:07:17Z
- **Tasks:** 2
- **Files modified:** 19 (2 created, 17 renamed/updated)

## Accomplishments

- Created `src/types/evidence.ts` with 7 per-source evidence interfaces and `EvidenceData` union type replacing `Record<string, unknown>` in `EvidenceSource.source_data`
- Created `src/types/log.ts` with `LogEntry` interface and `LogLevel` type enabling typed log store and service
- Updated `env.d.ts` with `Window` interface augmentation (logService, _env_, snackbar) and extended `ImportMetaEnv` (VITE_API_URL, VITE_WS_URL)
- Migrated all 11 utility files (git mv), both config files, and vuetify plugin to TypeScript with full type annotations
- Zero TypeScript errors, npm run build exits 0, no regressions

## Task Commits

Each task was committed atomically:

1. **Task 1: Create evidence/log types, update env.d.ts** - `d22a341` (feat)
2. **Task 2: Migrate utilities, configs, vuetify plugin to TypeScript** - `bd0480a` (feat)

**Plan metadata:** (included in final commit below)

## Files Created/Modified

- `frontend/src/types/evidence.ts` — 7 per-source interfaces + EvidenceData union + AnnotationSourceName
- `frontend/src/types/log.ts` — LogEntry interface + LogLevel type
- `frontend/src/types/gene.ts` — EvidenceSource.source_data changed to EvidenceData
- `frontend/src/types/index.ts` — added re-exports for evidence and log types
- `frontend/env.d.ts` — Window augmentation, extended ImportMetaEnv
- `frontend/src/utils/debounce.ts` — DebouncedFunction<T> generic interface
- `frontend/src/utils/wildcardMatcher.ts` — PatternValidationResult interface
- `frontend/src/utils/stateCompression.ts` — CompressionResult interface, typed functions
- `frontend/src/utils/formatters.ts` — typed date/bytes formatting
- `frontend/src/utils/adminBreadcrumbs.ts` — BreadcrumbItem interface
- `frontend/src/utils/adminIcons.ts` — Record<string, string> icon map
- `frontend/src/utils/publicBreadcrumbs.ts` — BreadcrumbItem + BreadcrumbPage interfaces
- `frontend/src/utils/logSanitizer.ts` — SanitizedLogEntry, RedactionSummary interfaces
- `frontend/src/utils/evidenceTiers.ts` — TierName/GroupName unions, typed TIER_CONFIG/SCORE_RANGES
- `frontend/src/utils/networkStateCodec.ts` — NetworkState/QueryParams interfaces; bug fix
- `frontend/src/utils/version.ts` — AllVersionsResult/FrontendVersionInfo interfaces
- `frontend/src/config.ts` — AppConfig interface
- `frontend/src/config/networkAnalysis.ts` — NetworkAnalysisConfig interface
- `frontend/src/plugins/vuetify.ts` — createVuetify() already typed by Vuetify

## Decisions Made

- **WindowLogService inline interface:** Used an inline `WindowLogService` interface in env.d.ts rather than `import type { LogService }` to avoid forward reference to a not-yet-migrated .js file. Will be refined in Plan 02 when logService.ts is migrated.
- **EvidenceData fallback:** Included `Record<string, unknown>` in the EvidenceData union for HGNC/gnomAD/GTEx sources whose fields are not rendered by frontend views (per research recommendation).
- **debounce flush() signature:** Typed `flush(...args: Parameters<T>)` to accept args for type compatibility with callers (useNetworkUrlState calls `flush(state)`), but the implementation uses stored `lastArgs`. Behavior documented in JSDoc.

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug] Fixed window.logService.warning() — method does not exist**

- **Found during:** Task 2 (networkStateCodec.ts migration)
- **Issue:** `networkStateCodec.js` called `window.logService.warning()` in 2 places, but logService only has `warn()`. This was a silent JS bug (method was undefined), documented in 02-RESEARCH.md Pitfall 6.
- **Fix:** Changed both `warning()` calls to `warn()` in networkStateCodec.ts.
- **Files modified:** `frontend/src/utils/networkStateCodec.ts`
- **Verification:** `grep -r "window.logService.warning" src/` returns zero results. TypeScript now catches this pattern.
- **Committed in:** `bd0480a` (Task 2 commit)

**2. [Rule 1 - Bug] Fixed stateCompression.ts error() call: 3 args to 2-param signature**

- **Found during:** Task 2 (stateCompression.ts type checking)
- **Issue:** `window.logService.error('[msg]:', error, { compressedLength: ..., firstChars: ... })` passed 3 arguments but `WindowLogService.error()` accepts 2. TypeScript surfaced this as TS2554.
- **Fix:** Merged the 3rd argument (context object) into the 2nd argument data object: `error('[msg]:', { error, compressedLength: ..., firstChars: ... })`.
- **Files modified:** `frontend/src/utils/stateCompression.ts`
- **Verification:** `vue-tsc --noEmit` passes with zero errors.
- **Committed in:** `bd0480a` (Task 2 commit, after fix applied before commit)

**3. [Rule 1 - Bug] Fixed evidenceTiers.ts: SCORE_RANGES[-1] returns `undefined` not `null`**

- **Found during:** Task 2 (evidenceTiers.ts type checking)
- **Issue:** `SCORE_RANGES[SCORE_RANGES.length - 1]` could be `undefined` under strict mode, but return type declared as `ScoreRangeConfig | null`. TypeScript TS2322 error.
- **Fix:** Added `?? null` nullish coalescing to safely return null for empty array edge case.
- **Files modified:** `frontend/src/utils/evidenceTiers.ts`
- **Verification:** `vue-tsc --noEmit` passes with zero errors.
- **Committed in:** `bd0480a` (Task 2 commit, after fix applied before commit)

**4. [Rule 1 - Bug] Fixed networkStateCodec.ts: query.v is string | undefined**

- **Found during:** Task 2 (networkStateCodec.ts type checking)
- **Issue:** `parseInt(query.v)` — `query.v` typed as `string | undefined` due to strict index access on `Record<string, string>`. TypeScript TS2345 error.
- **Fix:** Changed to `parseInt(query['v'] ?? '1')` with explicit fallback.
- **Files modified:** `frontend/src/utils/networkStateCodec.ts`
- **Verification:** `vue-tsc --noEmit` passes with zero errors.
- **Committed in:** `bd0480a` (Task 2 commit, after fix applied before commit)

---

**Total deviations:** 4 auto-fixed (4 Rule 1 - Bug)
**Impact on plan:** All 4 bugs were pre-existing JS silent failures now caught by TypeScript strict mode. No scope creep. All bugs fixed within Task 2 before the task commit.

## Issues Encountered

None — TypeScript surfaced 4 pre-existing bugs that were fixed inline per deviation rules before committing.

## User Setup Required

None - no external service configuration required.

## Next Phase Readiness

- All 14 Tier 1/2 files migrated with complete type annotations
- `EvidenceData` union type available for Plan 02's API module typing and Plan 03's component evidence rendering
- `DebouncedFunction<T>` generic ready for Plan 03's `useNetworkUrlState` composable migration
- `LogEntry/LogLevel` types ready for Plan 02's logStore.ts and logService.ts migration
- `Window` augmentations enable type-safe `window.logService/._env_/snackbar` access in all remaining migrations
- Zero TypeScript errors, zero build regressions — clean baseline for Plan 02

---
*Phase: 02-typescript-migration*
*Completed: 2026-02-28*
