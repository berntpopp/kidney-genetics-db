# Phase 2: TypeScript Migration - Research

**Researched:** 2026-02-28
**Domain:** TypeScript migration of non-component JavaScript files (stores, API modules, composables, utils, router, services, plugins, config)
**Confidence:** HIGH

---

## Summary

This phase migrates 34 `.js` files in `frontend/src/` (everything except `.vue` components) to TypeScript. Phase 1 already established the full toolchain: `tsconfig.app.json` with `allowJs: true`, `checkJs: false`, `verbatimModuleSyntax: true`, `strict: true`, and foundation types in `src/types/`. All files that need migration have been inventoried below with their current structure, exports, and dependencies. The migration is mechanical — rename `.js` to `.ts` and add type annotations — with no functional changes required.

The primary complexity is typing the 9 annotation source evidence payloads (`EvidenceSource.source_data`), the Axios client interceptors, and the `window` global augmentations (`window.logService`, `window._env_`). Every other file is straightforward.

**Primary recommendation:** Migrate in dependency order: utilities first (no imports from project), then API client, then stores, then router, then API modules, then services, then composables, then config/plugins. This order prevents circular import issues during migration.

---

## File Inventory

### Complete list of .js files requiring migration (34 files)

#### Entry point (1 file)
| File | Lines | Complexity |
|------|-------|-----------|
| `src/main.js` | 44 | LOW — createApp, plugin registration, logService init |

#### Router (1 file)
| File | Lines | Complexity |
|------|-------|-----------|
| `src/router/index.js` | 163 | MEDIUM — route meta types, navigation guard with authStore |

#### Stores (2 files)
| File | Lines | Complexity | Notes |
|------|-------|-----------|-------|
| `src/stores/auth.js` | 319 | HIGH — many typed actions, complex state, depends on `src/api/auth.js` |
| `src/stores/logStore.js` | 330 | MEDIUM — typed log entry interface needed, `addLogEntry(entry)` needs `LogEntry` type |

#### API modules (12 files)
| File | Lines | Complexity | Notes |
|------|-------|-----------|-------|
| `src/api/client.js` | 69 | MEDIUM — Axios instance with typed interceptors, `window._env_` access |
| `src/api/auth.js` | 166 | MEDIUM — uses `LoginResponse`, `User` types from Phase 1 |
| `src/api/genes.js` | 247 | HIGH — complex pagination loop, `window.logService` calls, `networkAnalysisConfig` import |
| `src/api/statistics.js` | 110 | LOW — straightforward typed return shapes |
| `src/api/network.js` | 129 | LOW — typed request/response for 5 network operations |
| `src/api/datasources.js` | 19 | LOW — 2 functions, simplest API module |
| `src/api/admin/annotations.js` | 196 | MEDIUM — 17 functions, returns raw Axios responses |
| `src/api/admin/cache.js` | 95 | MEDIUM — 7 functions, `getCacheNamespaces` returns constructed object |
| `src/api/admin/ingestion.js` | 105 | LOW — 8 functions, FormData upload |
| `src/api/admin/logs.js` | 67 | LOW — 4 functions |
| `src/api/admin/pipeline.js` | 111 | LOW — 12 functions, all simple |
| `src/api/admin/staging.js` | 122 | LOW — 9 functions |

#### Services (2 files)
| File | Lines | Complexity | Notes |
|------|-------|-----------|-------|
| `src/services/logService.js` | 341 | HIGH — singleton class, typed store interface, `window.logService` global set via `main.js` |
| `src/services/websocket.js` | 208 | MEDIUM — class with `ref(false)` typed state, `messageHandlers: Map<string, Function[]>` |

#### Composables (6 files)
| File | Lines | Complexity | Notes |
|------|-------|-----------|-------|
| `src/composables/useBackupApi.js` | 197 | MEDIUM — uses `fetch()` directly (not Axios), refs need typing |
| `src/composables/useBackupFormatters.js` | 103 | LOW — pure formatting functions, no external deps |
| `src/composables/useD3Tooltip.js` | 190 | MEDIUM — D3 selection types, `MouseEvent`, `onUnmounted` |
| `src/composables/useNetworkSearch.js` | 173 | LOW — depends on `wildcardMatcher` utils |
| `src/composables/useNetworkUrlState.js` | 302 | HIGH — depends on debounce, networkStateCodec, vue-router, `window.snackbar` global |
| `src/composables/useSettingsApi.js` | 155 | MEDIUM — uses `fetch()` directly, same pattern as useBackupApi |

#### Utilities (11 files)
| File | Lines | Complexity | Notes |
|------|-------|-----------|-------|
| `src/utils/adminBreadcrumbs.js` | 43 | LOW — simple typed return arrays |
| `src/utils/adminIcons.js` | 71 | LOW — typed string constants |
| `src/utils/debounce.js` | 113 | MEDIUM — generic function types `<T extends (...args: unknown[]) => unknown>` |
| `src/utils/evidenceTiers.js` | 222 | MEDIUM — typed config objects, union literal types for tier names |
| `src/utils/formatters.js` | 48 | LOW — 3 pure functions |
| `src/utils/logSanitizer.js` | 451 | MEDIUM — many overloads, `_testing` export needs typed |
| `src/utils/networkStateCodec.js` | 326 | MEDIUM — depends on stateCompression, `window.logService` calls |
| `src/utils/publicBreadcrumbs.js` | 89 | LOW — simple typed return arrays |
| `src/utils/stateCompression.js` | 139 | LOW — LZString, well-contained |
| `src/utils/version.js` | 64 | LOW — async function, `__APP_VERSION__` declare already in env.d.ts |
| `src/utils/wildcardMatcher.js` | 118 | LOW — pure functions with typed validation results |

#### Config (2 files)
| File | Lines | Complexity | Notes |
|------|-------|-----------|-------|
| `src/config.js` | 14 | LOW — typed config object, `window._env_` access |
| `src/config/networkAnalysis.js` | 146 | LOW — large config object, all typed literals |

#### Plugins (1 file)
| File | Lines | Complexity | Notes |
|------|-------|-----------|-------|
| `src/plugins/vuetify.js` | 161 | LOW — `createVuetify()` already typed by Vuetify |

#### Component index files (2 files — LOW PRIORITY)
| File | Notes |
|------|-------|
| `src/components/branding/index.js` | 1-line export, trivial |
| `src/components/visualizations/index.js` | 3 component re-exports, trivial |

**Note on component index files:** These are technically in `components/` (not excluded from TSML requirements) but contain only component re-exports. They are trivially migrated alongside component files in Phase 3 and can be deferred.

---

## Phase 1 Foundation (Already Exists)

### Existing type definitions in `src/types/`

**`src/types/api.ts`** — JSON:API wrapper types:
- `JsonApiResponse<T>`, `JsonApiListResponse<T>`, `JsonApiMeta`, `JsonApiLinks`
- `JsonApiError`, `ApiErrorResponse`

**`src/types/auth.ts`** — Auth types:
- `User` (id, email, username, role, is_active, created_at, updated_at)
- `UserRole = 'admin' | 'curator' | 'public'`
- `LoginRequest`, `LoginResponse` (access_token, token_type, user)
- `AuthState`

**`src/types/gene.ts`** — Gene types:
- `Gene`, `GeneDetail extends Gene`
- `EvidenceSource` — has `source_data: Record<string, unknown>` (PHASE 2 TARGET)
- `GeneListParams`

**`src/types/pipeline.ts`** — Pipeline/WebSocket types:
- `PipelineStatus`, `PipelineSource`, `PipelineSourceStatus`
- `WebSocketMessage` — has `data: Record<string, unknown>` (consider typing)

**`src/types/index.ts`** — Re-exports all above

### tsconfig setup
```json
// tsconfig.app.json
{
  "extends": "@vue/tsconfig/tsconfig.dom.json",
  "compilerOptions": {
    "strict": true,
    "allowJs": true,
    "checkJs": false,
    "verbatimModuleSyntax": true
  }
}
```

### env.d.ts (already has)
- `ImportMetaEnv.VITE_API_BASE_URL?: string` (note: `VITE_API_URL` is used in client.js but not declared — this is a gap)
- `declare const __APP_VERSION__: string`
- Missing: `Window` augmentation for `logService`, `_env_`, `snackbar`

---

## Architecture Patterns

### Recommended Migration Order (dependency-safe)

**Tier 1 — No project imports (migrate first):**
1. `src/utils/debounce.js`
2. `src/utils/wildcardMatcher.js`
3. `src/utils/stateCompression.js`
4. `src/utils/formatters.js`
5. `src/utils/adminBreadcrumbs.js`
6. `src/utils/adminIcons.js`
7. `src/utils/publicBreadcrumbs.js`
8. `src/utils/logSanitizer.js`
9. `src/utils/evidenceTiers.js`
10. `src/config/networkAnalysis.js`
11. `src/config.js`

**Tier 2 — Depend on Tier 1 only:**
12. `src/utils/networkStateCodec.js` (imports stateCompression)
13. `src/api/client.js` (no project imports)
14. `src/plugins/vuetify.js` (no project imports)

**Tier 3 — Depend on Tier 1-2:**
15. `src/services/logService.js` (imports logSanitizer)
16. `src/api/auth.js` (imports client)
17. `src/api/datasources.js` (imports client)
18. `src/api/statistics.js` (imports client)
19. `src/api/network.js` (imports client)
20. `src/api/admin/logs.js` (imports client)
21. `src/api/admin/staging.js` (imports client)
22. `src/api/admin/ingestion.js` (imports client)
23. `src/api/admin/cache.js` (imports client)
24. `src/api/admin/pipeline.js` (imports client)
25. `src/api/admin/annotations.js` (imports client)

**Tier 4 — Depend on Tier 3:**
26. `src/utils/version.js` (imports api/client)
27. `src/stores/logStore.js` (no store deps)
28. `src/api/genes.js` (imports client, networkAnalysisConfig)

**Tier 5 — Depend on Tier 4:**
29. `src/stores/auth.js` (imports api/auth)
30. `src/services/websocket.js` (standalone but uses window.logService)

**Tier 6 — Depend on Tier 5:**
31. `src/router/index.js` (imports stores/auth)
32. `src/main.js` (imports all)
33. `src/composables/useBackupApi.js` (imports stores/auth)
34. `src/composables/useBackupFormatters.js` (no deps)
35. `src/composables/useD3Tooltip.js` (no deps)
36. `src/composables/useNetworkSearch.js` (imports wildcardMatcher)
37. `src/composables/useSettingsApi.js` (imports stores/auth)
38. `src/composables/useNetworkUrlState.js` (imports debounce, networkStateCodec, vue-router)

### Cross-Dependencies Map

```
main.js
  ├── stores/logStore.js
  ├── services/logService.js → utils/logSanitizer.js
  ├── router/index.js → stores/auth.js → api/auth.js → api/client.js
  └── plugins/vuetify.js

api/genes.js
  ├── api/client.js
  └── config/networkAnalysis.js

composables/useNetworkUrlState.js
  ├── utils/debounce.js
  ├── utils/networkStateCodec.js → utils/stateCompression.js
  └── vue-router

composables/useNetworkSearch.js
  └── utils/wildcardMatcher.js
```

---

## Critical Typing Problems

### 1. `window` global augmentations (env.d.ts additions needed)

`window.logService`, `window._env_`, and `window.snackbar` are used across many files but not typed in `env.d.ts`. These must be added before migrating files that reference them.

**Files using `window.logService`:** auth.js, genes.js, websocket.js, networkStateCodec.js, stateCompression.js, networkUrlState.js, networkSearch.js, auth store
**Files using `window._env_`:** client.js, config.js
**Files using `window.snackbar`:** useNetworkUrlState.js

**Required env.d.ts additions:**
```typescript
// In env.d.ts — Window augmentation
interface Window {
  logService: import('@/services/logService').LogService
  _env_?: {
    API_BASE_URL?: string
    WS_URL?: string
    ENVIRONMENT?: string
    VERSION?: string
  }
  snackbar?: {
    success(msg: string, opts?: Record<string, unknown>): void
    error(msg: string, opts?: Record<string, unknown>): void
  }
}

// Also add missing VITE_API_URL to ImportMetaEnv:
interface ImportMetaEnv {
  readonly VITE_API_BASE_URL?: string
  readonly VITE_API_URL?: string    // used in client.js and websocket.js
  readonly VITE_WS_URL?: string     // used in config.js
}
```

### 2. Annotation source `evidence_data` shapes

The `EvidenceSource.source_data: Record<string, unknown>` in `src/types/gene.ts` needs per-source typed interfaces. Based on backend source analysis:

**ClinGen evidence_data keys:**
- `validity_count: number`, `validities: object[]`, `diseases: string[]`, `classifications: string[]`, `expert_panels: string[]`, `modes_of_inheritance: string[]`, `max_classification_score: number`, `evidence_score: number`, `last_updated: string`

**GenCC evidence_data keys:**
- `submission_count: number`, `submissions: object[]`, `diseases: string[]`, `classifications: string[]`, `submitters: string[]`, `modes_of_inheritance: string[]`, `evidence_score: number`

**HPO evidence_data keys:**
- `hpo_terms: string[]`, `term_count?: number`, `evidence_score: number`

**PanelApp evidence_data keys:**
- `panel_count: number`, `panels: string[]`, `regions: string[]`, `phenotypes: string[]`, `modes_of_inheritance: string[]`, `evidence_levels: string[]`, `last_updated: string`

**PubTator evidence_data keys:**
- `pmids: string[]`, `publication_count: number`, `total_mentions: number`, `evidence_score: number`

**DiagnosticPanels evidence_data keys:**
- `panels: string[]`, `providers: string[]`, `panel_count: number`, `provider_count: number`

**Literature evidence_data keys:**
- `publications: string[]`, `publication_count: number`, `publication_details?: Record<string, unknown>`

The 9 annotation sources are: ClinGen, GenCC, HPO, PanelApp, PubTator, DiagnosticPanels, Literature, plus potentially HGNC, gnomAD, GTEx (referenced in `updateGeneAnnotations` in `admin/annotations.js`). HGNC/gnomAD/GTEx shapes are not directly queried by frontend views consuming `evidence_data`, so `Record<string, unknown>` may remain appropriate for those.

**Decision for planner:** The `EvidenceSource.source_data` field in `src/types/gene.ts` should become a discriminated union via a `SourceData` type in a new `src/types/evidence.ts`. Organization (single file vs per-source files) is Claude's discretion.

### 3. Axios interceptor typing

In `api/client.js`, the response interceptor uses `originalRequest._retry = true` — TypeScript will reject `_retry` on `InternalAxiosRequestConfig`. The solution is to augment the Axios config type:

```typescript
// In api/client.ts or a global type declaration
import 'axios'
declare module 'axios' {
  interface InternalAxiosRequestConfig {
    _retry?: boolean
  }
}
```

### 4. LogStore `addLogEntry(entry)` — needs `LogEntry` interface

The `logStore.js` takes an untyped `entry` parameter. A `LogEntry` interface is needed:
```typescript
interface LogEntry {
  timestamp: string
  level: 'DEBUG' | 'INFO' | 'WARN' | 'ERROR' | 'CRITICAL'
  message: string
  data?: unknown
  correlationId?: string | null
  metadata?: Record<string, unknown>
  url?: string
  userAgent?: string
}
```

### 5. `debounce.js` generic function types

The custom `debounce` function returns a debounced function with `.cancel()` and `.flush()` methods. This requires careful generic typing since `useNetworkUrlState.js` calls `syncStateToUrl.cancel()` and `syncStateToUrl.flush(state)`:

```typescript
interface DebouncedFunction<T extends (...args: unknown[]) => unknown> {
  (...args: Parameters<T>): void
  cancel(): void
  flush(...args: Parameters<T>): void
}
export function debounce<T extends (...args: unknown[]) => unknown>(
  fn: T,
  delay: number
): DebouncedFunction<T>
```

### 6. Router route meta typing

The router uses `meta: { requiresAuth: true, requiresAdmin: true }` but vue-router's `RouteMeta` is not typed for these fields. TypeScript will complain unless the meta interface is augmented:

```typescript
// In router/index.ts or a .d.ts file
import 'vue-router'
declare module 'vue-router' {
  interface RouteMeta {
    requiresAuth?: boolean
    requiresAdmin?: boolean
  }
}
```

### 7. `verbatimModuleSyntax` enforcement

All type-only imports must use `import type`. When migrating, every `import { SomeType }` that imports only a type must become `import type { SomeType }`. This is a mechanical transformation but must not be forgotten.

---

## API Module Return Type Catalog

Based on direct file inspection:

### `src/api/genes.js` — returns custom shapes (NOT raw JSON:API)
- `getGenes()` → `{ items: Gene[], total: number, page: number, perPage: number, pageCount: number, meta: JsonApiMeta }`
- `getGene(symbol)` → `Gene` (flattened from JSON:API attributes)
- `getGeneEvidence(symbol)` → `{ evidence: EvidenceItem[], meta: JsonApiMeta }`
- `getGeneAnnotations(geneId)` → raw response.data (shape unclear from genes.js alone)
- `getHPOClassifications(geneIds)` → `response.data` (backend-specific shape)
- `getGenesByIds(geneIds, options)` → same shape as `getGenes()`

### `src/api/statistics.js` — all return `{ data: unknown, meta: JsonApiMeta }`
- `getSourceOverlaps()`, `getSourceDistributions()`, `getEvidenceComposition()`, `getSummaryStatistics()`

### `src/api/network.js` — all return `response.data` (Cytoscape JSON)
- `buildNetwork()`, `clusterNetwork()`, `extractSubgraph()`, `enrichHPO()`, `enrichGO()`

### `src/api/datasources.js` — returns raw `.data.data`
- `getDataSources()` → `response.data.data` (array)
- `getDataSource(sourceName)` → `response.data.data` (single)

### `src/api/auth.js` — mixed
- `login()` → `response.data` (matches `LoginResponse` from types/auth.ts)
- `getCurrentUser()` → `response.data` (matches `User`)
- `refreshToken()` → `response.data` (has `access_token: string`)
- All other auth functions → `response.data`

### Admin API modules — all return raw `AxiosResponse` (Promise<AxiosResponse<T>>)
The 6 admin API modules (`annotations`, `cache`, `ingestion`, `logs`, `pipeline`, `staging`) return the raw Axios response (not `.data`). This means callers must use `.data` to access the payload. When typing, these return `Promise<AxiosResponse<T>>` where T is the response body type. **Exception:** `admin/logs.js`'s `exportLogs` returns `response.data` directly.

---

## Existing Tests

**`src/components/ui/__tests__/Button.spec.ts`** — one Vitest test exists (from Phase 1 smoke test).

**Vitest config:**
- Environment: jsdom
- Setup file: `src/test/setup.ts` (empty)
- Include pattern: `src/**/*.{test,spec}.ts`
- Coverage: v8, excludes `src/types/**`

**Phase 2 test plan (from CONTEXT.md decisions):**
- API module tests: mock Axios client, verify request URL/params/headers (~2-3 per module)
- Store tests: state + behavior, auth flow end-to-end (~5-8 per store)
- Utility/composable depth: Claude's discretion

**Pattern for mocking Axios in tests:**
```typescript
import { vi } from 'vitest'
import apiClient from '@/api/client'

vi.mock('@/api/client', () => ({
  default: {
    get: vi.fn(),
    post: vi.fn(),
    put: vi.fn(),
    delete: vi.fn()
  }
}))
```

---

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| AxiosRequestConfig type extension | Custom `_retry` field workaround | `declare module 'axios'` augmentation | TypeScript module augmentation is the official pattern |
| Route meta typing | Runtime type-checking | `declare module 'vue-router'` RouteMeta augmentation | Vue Router documents this exact pattern |
| Window global typing | Type casts everywhere | `interface Window` in env.d.ts | Single declaration covers all files |
| Type-safe store patterns | Custom store factory | Pinia `defineStore` with composition API (already used) | Stores are already setup-store style, just add types |
| D3 selection typing | Manual DOM typings | `@types/d3` is already a transitive dep via `d3` package | D3 v7 ships its own types |

---

## Common Pitfalls

### Pitfall 1: `verbatimModuleSyntax` requires `import type` for type-only imports
**What goes wrong:** TypeScript error: "This import is never used as a value and must use 'import type'."
**Why it happens:** `verbatimModuleSyntax: true` prevents type-erased imports.
**How to avoid:** When adding type imports, always use `import type { Foo }`.
**Warning signs:** `TS1484` error code in `vue-tsc` output.

### Pitfall 2: `allowJs: true` means .js files are NOT type-checked
**What goes wrong:** A renamed `.ts` file still being loaded as `.js` (stale build cache) causes no errors during migration.
**Why it happens:** Vite/tsbuildinfo cache can be stale.
**How to avoid:** Run `vue-tsc --noEmit` after each batch of renames to verify.
**Warning signs:** No TypeScript errors even for obviously wrong types.

### Pitfall 3: Pinia stores use composition API — `ref<T>()` types needed
**What goes wrong:** `ref(null)` becomes `Ref<null>` not `Ref<User | null>` without explicit generic.
**Why it happens:** TypeScript infers `Ref<null>` from the initial value.
**How to avoid:** Annotate all refs explicitly: `const user = ref<User | null>(null)`.
**Warning signs:** TypeScript errors when assigning `User` objects to store state refs.

### Pitfall 4: Admin API modules return `Promise<AxiosResponse<T>>` not `Promise<T>`
**What goes wrong:** Callers in Vue components already use `.data` on the result — if typed as returning `.data` directly, types won't match actual usage.
**Why it happens:** Unlike `genes.js` which extracts `.data`, admin modules return raw `AxiosResponse`.
**How to avoid:** Check each admin module's return style before typing (verified: all admin modules return raw response, except `logs.exportLogs`).
**Warning signs:** Type errors in component code when accessing `.data.data`.

### Pitfall 5: `debounce.flush()` is called with args in useNetworkUrlState.js
**What goes wrong:** The custom `debounce` implementation's `flush()` ignores passed args and uses `lastArgs` from previous call. The `useNetworkUrlState.js` calls `syncStateToUrl.flush(state)` — the arg is ignored.
**Why it happens:** The current `flush()` implementation doesn't accept args.
**How to avoid:** Type `flush()` to accept optional args matching the debounced function, document the behavior.
**Warning signs:** TypeScript error if `flush` is typed without accepting args.

### Pitfall 6: `window.logService.warning()` — method does not exist
**What goes wrong:** `networkStateCodec.js` calls `window.logService.warning()` but `logService.js` has no `warning()` method (it has `warn()`).
**Why it happens:** JS silently allows calling non-existent methods when accessed via optional chaining or with no strict typing.
**How to avoid:** When creating the `LogService` type, the missing `warning()` method will surface as a TypeScript error. Fix the callers to use `warn()`.
**Warning signs:** `TS2339: Property 'warning' does not exist on type 'LogService'`.

### Pitfall 7: `src/utils/version.js` uses `__APP_VERSION__` global
**What goes wrong:** `__APP_VERSION__` is declared in `env.d.ts` as `declare const __APP_VERSION__: string`. This is already correct.
**Why it happens:** Not a pitfall — already handled.
**How to avoid:** No action needed — already in env.d.ts.

---

## Code Examples

### Pinia store with typed refs
```typescript
// Source: Pinia docs + existing store pattern
import { defineStore } from 'pinia'
import { ref, computed } from 'vue'
import type { User } from '@/types/auth'

export const useAuthStore = defineStore('auth', () => {
  const user = ref<User | null>(null)
  const accessToken = ref<string | null>(localStorage.getItem('access_token'))
  const isLoading = ref(false)
  const error = ref<string | null>(null)

  const isAuthenticated = computed(() => !!accessToken.value && !!user.value)
  // ...
})
```

### Axios module augmentation for `_retry`
```typescript
// In src/api/client.ts
import 'axios'
declare module 'axios' {
  interface InternalAxiosRequestConfig {
    _retry?: boolean
  }
}
```

### Vue Router meta augmentation
```typescript
// In src/router/index.ts
import 'vue-router'
declare module 'vue-router' {
  interface RouteMeta {
    requiresAuth?: boolean
    requiresAdmin?: boolean
  }
}
```

### Window global augmentation in env.d.ts
```typescript
// In env.d.ts (additions to existing file)
import type { LogService } from '@/services/logService'

interface Window {
  logService: LogService
  _env_?: {
    API_BASE_URL?: string
    WS_URL?: string
    ENVIRONMENT?: string
    VERSION?: string
  }
  snackbar?: {
    success(msg: string, opts?: Record<string, unknown>): void
    error(msg: string, opts?: Record<string, unknown>): void
  }
}
```

### Typed API module (pattern for genes.ts)
```typescript
// Source: existing genes.js structure + JSON:API types
import type { Gene, GeneListParams } from '@/types/gene'
import type { JsonApiMeta } from '@/types/api'

interface GeneListResult {
  items: Gene[]
  total: number
  page: number
  perPage: number
  pageCount: number
  meta: JsonApiMeta
}

// Axios generics usage (for modules that return response.data):
const response = await apiClient.get<{ data: GeneJsonApiItem[]; meta: JsonApiMeta }>('/api/genes/', { params })
```

### Evidence source typed discriminated union
```typescript
// Proposed src/types/evidence.ts
export interface ClinGenEvidenceData {
  validity_count: number
  validities: ClinGenValidity[]
  diseases: string[]
  classifications: string[]
  expert_panels: string[]
  modes_of_inheritance: string[]
  evidence_score: number
  last_updated: string
}

export interface PanelAppEvidenceData {
  panel_count: number
  panels: string[]
  regions: string[]
  phenotypes: string[]
  modes_of_inheritance: string[]
  evidence_levels: string[]
  last_updated: string
}

// ... other source types ...

export type AnnotationSourceName =
  | 'ClinGen' | 'GenCC' | 'HPO' | 'PanelApp'
  | 'PubTator' | 'DiagnosticPanels' | 'Literature'

export type EvidenceData =
  | ClinGenEvidenceData
  | GenCCEvidenceData
  | HPOEvidenceData
  | PanelAppEvidenceData
  | PubTatorEvidenceData
  | DiagnosticPanelsEvidenceData
  | LiteratureEvidenceData
  | Record<string, unknown>  // fallback for HGNC/gnomAD/GTEx

// Then in gene.ts, replace:
// source_data: Record<string, unknown>
// with:
// source_data: EvidenceData
```

### Vitest test for API module
```typescript
// Source: vitest docs + existing test pattern
import { describe, it, expect, vi, beforeEach } from 'vitest'
import { statisticsApi } from '@/api/statistics'

vi.mock('@/api/client', () => ({
  default: {
    get: vi.fn()
  }
}))

import apiClient from '@/api/client'

describe('statisticsApi', () => {
  beforeEach(() => {
    vi.clearAllMocks()
  })

  it('getSummaryStatistics calls correct endpoint', async () => {
    const mockData = { data: { total_genes: 571 }, meta: {} }
    vi.mocked(apiClient.get).mockResolvedValue({ data: mockData })

    const result = await statisticsApi.getSummaryStatistics()
    expect(apiClient.get).toHaveBeenCalledWith('/api/statistics/summary')
    expect(result.data).toEqual(mockData.data)
  })
})
```

---

## State of the Art

| Old Approach | Current Approach | Impact |
|--------------|------------------|--------|
| `import type { Foo } from './foo'` optional | Required by `verbatimModuleSyntax: true` | Must use `import type` for all type-only imports |
| `Ref<T>` inferred from initial value | Must be explicit for `null` initial values | `ref<User \| null>(null)` pattern required |
| `any` for untyped API responses | Axios generics `get<ResponseType>()` or type assertion | Both are valid; prefer generics for HTTP verbs |
| Module augmentation via `/// <reference>` | Standard `declare module 'axios'` in .ts file | Use standard approach |

---

## Open Questions

1. **Component index files (`components/branding/index.js`, `components/visualizations/index.js`)**
   - What we know: These are 2 trivial files that just re-export .vue components
   - What's unclear: Whether TSML-05 ("all 11 utility files") counts these as utility files
   - Recommendation: Include them in Phase 2 since they're trivial (1-3 lines each) even though they live in `components/`

2. **`EvidenceData` union type completeness**
   - What we know: HGNC, gnomAD, GTEx, STRINGdb_PPI, clinvar are referenced as sources in `updateGeneAnnotations()` params but their `evidence_data` shapes are not exposed in frontend views
   - What's unclear: Whether the frontend actually renders fields from these sources
   - Recommendation: Use `Record<string, unknown>` as the fallback for unknown sources in the discriminated union; only create specific interfaces for sources whose data the frontend renders

3. **`LogService` class export for Window typing**
   - What we know: `env.d.ts` needs `import type { LogService }` to type `window.logService`
   - What's unclear: Whether `logService.ts` should export the class type or an interface
   - Recommendation: Export both the class instance (`logService`) and the class type (`LogService`), then use `typeof logService` for the window type to avoid circular imports

---

## Sources

### Primary (HIGH confidence)
- Direct file inspection of all 34 .js files — complete
- Direct inspection of `tsconfig.app.json`, `tsconfig.node.json`, `tsconfig.json`
- Direct inspection of `vitest.config.ts`, `vite.config.ts`
- Direct inspection of `src/types/*.ts` (5 files)
- Direct inspection of `env.d.ts`
- Direct inspection of backend pipeline source files for evidence_data shapes
- `frontend/package.json` — library versions confirmed

### Secondary (MEDIUM confidence)
- Backend `app/pipeline/sources/unified/*.py` files — evidence_data key names extracted from Python source code, verified accurate

---

## Metadata

**Confidence breakdown:**
- File inventory: HIGH — all files directly read
- Dependency order: HIGH — derived from actual import statements
- Typing problems: HIGH — derived from actual code patterns
- Evidence data shapes: MEDIUM — backend Python files read but some fields (HGNC/gnomAD/GTEx) not fully explored
- Test patterns: HIGH — Vitest config and existing test file read

**Research date:** 2026-02-28
**Valid until:** 2026-03-28 (stable tech stack, 30-day horizon)
