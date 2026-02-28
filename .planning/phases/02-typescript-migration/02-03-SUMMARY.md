---
phase: 02-typescript-migration
plan: 03
subsystem: stores-composables
tags: [typescript, pinia, vue-router, composables, vitest, tsml-08, test-04]

# Dependency graph
requires:
  - phase: 02-typescript-migration
    plan: 01
    provides: types/auth.ts (User, UserRole), types/log.ts (LogEntry, LogLevel), utils/debounce.ts (DebouncedFunction), utils/wildcardMatcher.ts, utils/networkStateCodec.ts
  - phase: 02-typescript-migration
    plan: 02
    provides: api/auth.ts (typed auth API functions), services/logService.ts (LogService class), env.d.ts (Window.logService typed)

provides:
  - useAuthStore (Pinia store) with ref<User | null> state, typed UserRole computed, catch (err unknown) narrowing
  - useLogStore (Pinia store) with ref<LogEntry[]> state, typed addLogEntry(entry LogEntry, maxEntriesOverride number | null) action
  - router/index.ts with RouteMeta augmentation (requiresAuth?: boolean, requiresAdmin?: boolean)
  - main.ts typed app entry point with typed plugin registration
  - useBackupFormatters.ts with BackupFormatters return interface, null-safe format functions
  - useD3Tooltip.ts with d3 Selection<HTMLDivElement> type (requires @types/d3)
  - useNetworkSearch.ts with cytoscape.Core typed instance, NetworkSearchReturn interface
  - useBackupApi.ts with BackupApiReturn typed interface, BackupRecord/BackupCreateOptions/RestoreOptions
  - useSettingsApi.ts with SettingsApiReturn typed interface, SettingsListParams
  - useNetworkUrlState.ts with DebouncedFunction<(state: NetworkState) => void> syncStateToUrl
  - 4 test files: auth.spec.ts (11 tests), logStore.spec.ts (12 tests), useBackupFormatters.spec.ts (19 tests), useNetworkSearch.spec.ts (8 tests)
  - ESLint config updated with DOM type globals (HTMLDivElement, DOMRect, RequestInit, MouseEvent, etc.)

affects:
  - Phase 03 (component migration — all Vue components import from these typed stores and composables)
  - All .vue components using useAuthStore, useLogStore, composable return types

# Tech tracking
tech-stack.added:
  - "@types/d3": "^7.4.3" (TypeScript declarations for D3 library)

tech-stack.patterns:
  - Pinia composition API stores with explicit ref<T> generics (ref<User | null>, ref<LogEntry[]>)
  - Vue Router RouteMeta module augmentation in router/index.ts
  - catch (err unknown) + narrowing pattern for type-safe error handling
  - Computed functions returning functions typed as computed<(arg: T) => R>
  - eslint-disable-next-line no-unused-vars for module augmentation declarations
  - D3 Selection<HTMLDivElement, unknown, HTMLElement, unknown> for typed tooltip manipulation

# File tracking
key-files.created:
  - frontend/src/stores/__tests__/auth.spec.ts
  - frontend/src/stores/__tests__/logStore.spec.ts
  - frontend/src/composables/__tests__/useBackupFormatters.spec.ts
  - frontend/src/composables/__tests__/useNetworkSearch.spec.ts

key-files.modified:
  - frontend/src/stores/auth.js -> auth.ts (ref<User | null>, typed catch, typed admin actions)
  - frontend/src/stores/logStore.js -> logStore.ts (ref<LogEntry[]>, LogStats/LogsByLevel/MemoryUsage interfaces)
  - frontend/src/router/index.js -> index.ts (RouteMeta augmentation, RouteRecordRaw[] typed routes)
  - frontend/src/main.js -> main.ts (typed plugin registration)
  - frontend/src/composables/useBackupApi.js -> useBackupApi.ts
  - frontend/src/composables/useBackupFormatters.js -> useBackupFormatters.ts
  - frontend/src/composables/useD3Tooltip.js -> useD3Tooltip.ts
  - frontend/src/composables/useNetworkSearch.js -> useNetworkSearch.ts
  - frontend/src/composables/useNetworkUrlState.js -> useNetworkUrlState.ts
  - frontend/src/composables/useSettingsApi.js -> useSettingsApi.ts
  - frontend/src/components/branding/index.js -> index.ts
  - frontend/src/components/visualizations/index.js -> index.ts
  - frontend/eslint.config.js (added DOM type globals for TypeScript files)
  - frontend/package.json (added @types/d3 devDependency)

# Decisions
decisions:
  - "@types/d3 installed as devDependency — d3 package lacks bundled TypeScript types, @types/d3 v7.4.3 provides full typed Selection, Transition, etc."
  - "D3 tooltip typed as Selection<HTMLDivElement, unknown, HTMLElement, unknown> — precise generic avoids any"
  - "catch (err unknown) narrowing pattern: cast to { response?: { data?: { detail?: string } } } for Axios errors"
  - "RouteMeta interface in declare module block suppressed with eslint-disable-next-line no-unused-vars — false positive from ESLint not understanding module augmentation"
  - "hasPermission and hasRole computed<(arg) => R> pattern: eslint-disable-next-line on the computed wrapping to avoid false-positive no-unused-vars"
  - "ESLint globals extended for TypeScript files: MouseEvent, HTMLElement, HTMLDivElement, DOMRect, RequestInit, MessageEvent, Event, Element, Node, FormData, File"
  - "Pre-existing ESLint errors (6) in debounce.ts and client.spec.ts not fixed — outside scope of this plan"

# Metrics
metrics:
  duration: "16m 41s"
  completed: "2026-02-28"
  tasks_completed: 2
  tasks_planned: 2
  tests_added: 50
  files_migrated: 12
---

# Phase 2 Plan 3: Stores, Router, and Composables TypeScript Migration Summary

**One-liner:** Full TypeScript migration of Pinia stores (auth + log), Vue Router with RouteMeta augmentation, and 6 composables — TSML-08 verified with vue-tsc clean pass, 50 new tests added for TEST-04.

## What Was Built

This plan completed Wave 3 of the TypeScript migration — the final wave. Every non-component `.js` file in `frontend/src/` is now TypeScript. Pinia stores provide typed reactive state to all Vue components. The router provides typed meta fields via module augmentation. Composables have typed return values.

### Stores

**auth.ts** (`ref<User | null>` state):
- `const user = ref<User | null>(null)` — CRITICAL explicit generic
- `const accessToken = ref<string | null>(...)` and `refreshToken`
- `catch (err: unknown)` then narrowed to `{ response?: { data?: { detail?: string } } }`
- `hasPermission` and `hasRole` typed as `computed<(arg: T) => R>`
- All admin actions return proper typed results from API

**logStore.ts** (`ref<LogEntry[]>` state):
- `const logs = ref<LogEntry[]>([])` — explicit generic
- `LogStats`, `LogsByLevel`, `MemoryUsage`, `ExportOptions` interfaces defined
- `addLogEntry(entry: LogEntry, maxEntriesOverride: number | null = null): void`
- All computed counts with return type annotations
- `clearLogs(): number` returns count for callers

### Router

`router/index.ts` with module augmentation:
```typescript
declare module 'vue-router' {
  interface RouteMeta {
    requiresAuth?: boolean
    requiresAdmin?: boolean
  }
}
```
Routes typed as `RouteRecordRaw[]`. Navigation guard fully typed.

### Composables

- **useBackupFormatters.ts**: `BackupFormatters` return interface, null-safe formatters using `??`
- **useD3Tooltip.ts**: `Selection<HTMLDivElement, unknown, HTMLElement, unknown>` type, @types/d3 installed
- **useNetworkSearch.ts**: `cytoscape.Core | null` typed instance, `NetworkSearchReturn` interface
- **useBackupApi.ts**: `BackupRecord`, `BackupCreateOptions`, `RestoreOptions` interfaces
- **useSettingsApi.ts**: `SettingsListParams`, `SettingsApiReturn` interfaces
- **useNetworkUrlState.ts**: `DebouncedFunction<(state: NetworkState) => void>` for `syncStateToUrl`

## Test Coverage (TEST-04 Satisfied)

| File | Tests | Coverage |
|------|-------|----------|
| stores/__tests__/auth.spec.ts | 11 | initial state, login, logout, init, isAdmin, hasRole, clearError |
| stores/__tests__/logStore.spec.ts | 12 | addLogEntry, trim, clear, filters, viewer visibility |
| composables/__tests__/useBackupFormatters.spec.ts | 19 | all 7 formatters, null/undefined, edge cases |
| composables/__tests__/useNetworkSearch.spec.ts | 8 | wildcard *, ?, invalid patterns, clearSearch, isNodeMatched |
| **Total new** | **50** | |

## TSML-08 Verification

```bash
npx vue-tsc --noEmit --project tsconfig.app.json
# Exit: 0 — zero TypeScript errors across entire project
```

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 2 - Missing Critical] @types/d3 not installed**

- **Found during:** Task 2 — useD3Tooltip.ts migration
- **Issue:** `d3` package has no bundled TypeScript declarations. vue-tsc errored with `TS7016: Could not find a declaration file for module 'd3'`
- **Fix:** `npm install --save-dev @types/d3` — installed v7.4.3 which provides full typed Selection, Transition, etc.
- **Files modified:** package.json, package-lock.json
- **Commit:** 5f4abff

**2. [Rule 2 - Missing Critical] ESLint config missing DOM type globals for .ts files**

- **Found during:** Task 2 — npm run lint after migrating composables
- **Issue:** TypeScript files (`.ts`) ESLint config lacked DOM globals. `MouseEvent`, `HTMLElement`, `HTMLDivElement`, `DOMRect`, `RequestInit`, `MessageEvent`, `Event`, `Element`, `Node`, `FormData`, `File` all flagged as undefined.
- **Fix:** Added DOM type globals to the `files: ['**/*.{ts,tsx}']` config block in `eslint.config.js`
- **Files modified:** eslint.config.js

**3. [Rule 1 - Bug] False-positive ESLint warnings for RouteMeta and hasPermission/hasRole**

- **Found during:** Task 1/2 — npm run lint
- **Issue:** ESLint `no-unused-vars` incorrectly flags `interface RouteMeta` inside `declare module 'vue-router'` and the inner function parameters of `computed<(arg) => R>` patterns as unused
- **Fix:** Added `eslint-disable-next-line no-unused-vars` suppression comments where ESLint produces false positives
- **Impact:** Zero — TypeScript verifies these are correctly used

## Pre-existing Issues (Not Fixed)

6 ESLint errors remain in pre-existing files (outside this plan's scope):
- `frontend/src/api/__tests__/client.spec.ts`: `'global' is not defined` (1 error)
- `frontend/src/utils/debounce.ts`: `@typescript-eslint/no-explicit-any` and `@typescript-eslint/no-unused-vars` rules not found (5 errors) — these use `eslint-disable` for a TypeScript ESLint plugin rule that isn't installed in the flat config

## Next Phase Readiness

Phase 3 (component migration) can proceed:
- All stores export typed state consumable by Vue components
- All composables have typed return values
- Router provides typed RouteMeta for navigation guards
- `useAuthStore().isAuthenticated`, `isAdmin`, `hasRole()` are fully typed
- `useLogStore().addLogEntry(entry: LogEntry)` is typed
- All 6 composables ready for Vue component consumption
