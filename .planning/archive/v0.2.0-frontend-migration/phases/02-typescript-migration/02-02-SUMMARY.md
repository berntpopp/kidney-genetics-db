---
phase: 02-typescript-migration
plan: 02
subsystem: api
tags: [typescript, axios, api-client, logservice, websocket, api-modules, testing]

# Dependency graph
requires:
  - phase: 02-typescript-migration
    plan: 01
    provides: types/gene.ts, types/log.ts, types/auth.ts, types/pipeline.ts, env.d.ts Window augmentations, all utility .ts files

provides:
  - Typed Axios instance (client.ts) with _retry module augmentation and typed interceptors
  - LogService class exported with typed public API (debug/info/warn/error/critical/logPerformance/logApiCall)
  - LogLevel as const object with literal string types
  - GeneListResult interface for all gene list endpoints
  - StatisticsResult<T> generic interface for statistics endpoints
  - Typed network params (BuildNetworkParams, ClusterNetworkParams, EnrichHPOParams, EnrichGOParams)
  - DataSource interface for datasource endpoints
  - All 6 admin modules typed with Promise<AxiosResponse<T>> returns
  - WebSocketService class with MessageHandler type and typed connect/send/subscribe
  - Window.logService refined to use actual LogService class type in env.d.ts
  - 4 API test files (client, genes, statistics, auth) with 23 tests satisfying TEST-05

affects:
  - 02-03 (composables — import from typed API modules and services)
  - 03 (store migration — stores currently import from API modules)
  - All store/composable/component files that import from api/* or services/*

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "Admin API modules return Promise<AxiosResponse<T>> not Promise<T> — callers use .data"
    - "Public API modules extract response.data and return typed objects"
    - "Axios module augmentation for _retry via declare module 'axios'"
    - "LogService exported as class (not just singleton) for Window augmentation"
    - "vi.mock('@/api/client') pattern for API module unit tests"
    - "Admin logs.exportLogs() exception: returns response.data directly (not AxiosResponse)"

key-files:
  created:
    - frontend/src/api/__tests__/client.spec.ts
    - frontend/src/api/__tests__/genes.spec.ts
    - frontend/src/api/__tests__/statistics.spec.ts
    - frontend/src/api/__tests__/auth.spec.ts
  modified:
    - frontend/env.d.ts
    - frontend/src/api/client.ts
    - frontend/src/api/auth.ts
    - frontend/src/api/genes.ts
    - frontend/src/api/statistics.ts
    - frontend/src/api/network.ts
    - frontend/src/api/datasources.ts
    - frontend/src/api/admin/annotations.ts
    - frontend/src/api/admin/cache.ts
    - frontend/src/api/admin/ingestion.ts
    - frontend/src/api/admin/logs.ts
    - frontend/src/api/admin/pipeline.ts
    - frontend/src/api/admin/staging.ts
    - frontend/src/services/logService.ts
    - frontend/src/services/websocket.ts

key-decisions:
  - "LogService exported as class (not just singleton) so Window.logService in env.d.ts can use the actual class type"
  - "Window augmentation in env.d.ts uses import() type to avoid circular dependency between env.d.ts and logService.ts"
  - "LogLevel as const — literal types ensure _log() level parameter is constrained to valid values"
  - "Admin module pattern: Promise<AxiosResponse<T>> preserves existing caller behavior where views access .data"
  - "CacheNamespaces exception: getCacheNamespaces() processes namespaces and returns CacheNamespacesResult (not AxiosResponse) to preserve existing async aggregation logic"
  - "LOG_LEVEL_PRIORITY lookup uses nullish coalescing (?? 0) to handle TypeScript strict no-unchecked-indexed-access"

patterns-established:
  - "API module test pattern: vi.mock('@/api/client') then verify calls with expect().toHaveBeenCalledWith()"
  - "JsonApiItem<T> local interface for typing JSON:API item wrappers within gene API"
  - "GeneListResult: { items, total, page, perPage, pageCount, meta } — consistent across getGenes and getGenesByIds"

# Metrics
duration: 9m 12s
completed: 2026-02-28
---

# Phase 02 Plan 02: API Layer TypeScript Migration Summary

**14 JS files renamed to .ts (client + 12 API modules + 2 services) with fully typed request/response interfaces — all downstream consumers now receive autocompletion and compile-time type safety. 23 new API module tests satisfy TEST-05 requirement.**

## Performance

- **Duration:** 9m 12s
- **Started:** 2026-02-28T11:11:06Z
- **Completed:** 2026-02-28T11:20:18Z
- **Tasks:** 2
- **Files modified:** 15 renamed/updated + 4 test files created

## Accomplishments

- Migrated `client.ts` with Axios module augmentation for `_retry` and typed request/response interceptors
- Migrated `logService.ts` as exported `LogService` class with typed properties and methods; `LogLevel as const` for literal types
- Refined `Window.logService` in `env.d.ts` from inline interface to actual `import('@/services/logService').LogService` type
- Migrated all 5 public API modules with typed return interfaces: `GeneListResult`, `StatisticsResult<T>`, `NetworkData`, `EnrichmentResult`, `DataSource`
- Migrated all 6 admin API modules with `Promise<AxiosResponse<T>>` returns (preserving existing caller behavior)
- Migrated `websocket.ts` as exported `WebSocketService` class with `MessageHandler` type and typed connect/subscribe/send
- Created 4 test files with 23 tests (client, genes, statistics, auth) covering request construction verification
- Zero TypeScript errors, `npm run build` exits 0, all 26 tests pass

## Task Commits

Each task was committed atomically:

1. **Task 1: Migrate API client, 12 API modules, and 2 services to TypeScript** - `1cd7acb` (feat)
2. **Task 2: Add API module tests satisfying TEST-05 requirement** - `b010b01` (test)

## Files Created/Modified

**Renamed to TypeScript (git mv):**
- `frontend/src/api/client.ts` — Axios instance + _retry augmentation + typed interceptors
- `frontend/src/api/auth.ts` — LoginResponse, RefreshResponse, User return types
- `frontend/src/api/genes.ts` — GeneListResult, GeneEvidenceResult, JsonApiItem<T> local types
- `frontend/src/api/statistics.ts` — StatisticsResult<T>, SourceDistributionItem, SummaryStatisticsData
- `frontend/src/api/network.ts` — BuildNetworkParams, ClusterNetworkParams, NetworkData, EnrichmentResult
- `frontend/src/api/datasources.ts` — DataSource interface
- `frontend/src/api/admin/annotations.ts` — PipelineUpdateParams, AxiosResponse returns
- `frontend/src/api/admin/cache.ts` — CacheNamespaceDetail, getCacheNamespaces processed result
- `frontend/src/api/admin/ingestion.ts` — typed File upload, AxiosResponse returns
- `frontend/src/api/admin/logs.ts` — LogQueryParams, exportLogs returns data directly
- `frontend/src/api/admin/pipeline.ts` — all functions typed with AxiosResponse returns
- `frontend/src/api/admin/staging.ts` — StagingApprovalData, NormalizationLogParams
- `frontend/src/services/logService.ts` — LogService class, LogLevel as const, LogStore interface
- `frontend/src/services/websocket.ts` — WebSocketService class, MessageHandler type

**Updated:**
- `frontend/env.d.ts` — Window.logService uses `import('@/services/logService').LogService`

**Created (tests):**
- `frontend/src/api/__tests__/client.spec.ts` — Axios instance + interceptor tests
- `frontend/src/api/__tests__/genes.spec.ts` — getGenes, getGene, getGeneEvidence, getHPOClassifications tests
- `frontend/src/api/__tests__/statistics.spec.ts` — getSummaryStatistics, getSourceDistributions, getSourceOverlaps, getEvidenceComposition tests
- `frontend/src/api/__tests__/auth.spec.ts` — login, getCurrentUser, refreshToken, logout, getAllUsers tests

## Decisions Made

- **LogService class export:** Exported the `LogService` class (in addition to the `logService` singleton) so `env.d.ts` can reference `import('@/services/logService').LogService` directly, eliminating the temporary inline `WindowLogService` interface from Plan 01.
- **Window augmentation via import():** Used `import('@/services/logService').LogService` in env.d.ts instead of a named import to keep env.d.ts as a pure declaration file (no `import` statements at top level).
- **LOG_LEVEL_PRIORITY nullish coalescing:** TypeScript strict mode flagged `LOG_LEVEL_PRIORITY[level]` as `number | undefined`; used `?? 0` to safely default unknown levels to 0 priority.
- **Admin module return type:** All admin modules return `Promise<AxiosResponse<T>>` (raw response) because existing component callers access `.data` on the return value. This preserves existing behavior without requiring component changes in Plan 03.
- **getCacheNamespaces exception:** This function aggregates multiple API calls and returns a processed result `CacheNamespacesResult` rather than a raw `AxiosResponse`, consistent with its original implementation and caller expectations.

## Deviations from Plan

None — plan executed exactly as written.

## Issues Encountered

One TypeScript strict mode issue fixed inline during Task 1:
- `LOG_LEVEL_PRIORITY[level]` is `number | undefined` under strict mode — resolved with `?? 0` nullish coalescing before the comparison.

## User Setup Required

None - no external service configuration required.

## Next Phase Readiness

- All 14 API/service files fully typed — Plan 02-03 can import from typed modules
- `GeneListResult` interface ready for stores/composables that consume `geneApi.getGenes()`
- `LogService` class type available in `window.logService` — all components that call `window.logService.*` get autocompletion
- `WebSocketService` exported class type ready for composables that wrap `wsService`
- `MessageHandler` type exported for type-safe WebSocket subscriptions
- TEST-05 requirement satisfied: 23 API module tests + pre-existing 3 component tests = 26 total

---
*Phase: 02-typescript-migration*
*Completed: 2026-02-28*
