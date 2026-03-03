---
phase: 01-foundation-setup
plan: 01
subsystem: ui
tags: [typescript, vite, vue, tsconfig, prettier, eslint, type-interfaces]

# Dependency graph
requires: []
provides:
  - TypeScript strict-mode configuration with allowJs/checkJs-false for zero-friction JS coexistence
  - tsconfig project references (app + node) with @/ path alias
  - env.d.ts with Vite ImportMetaEnv globals and Vue module declaration
  - vite.config.ts (renamed from .js via git mv)
  - Domain type interfaces: Gene, GeneDetail, EvidenceSource, GeneListParams
  - Domain type interfaces: User, UserRole, LoginRequest, LoginResponse, AuthState
  - Domain type interfaces: JsonApiResponse, JsonApiListResponse, JsonApiMeta, JsonApiLinks, JsonApiError
  - Domain type interfaces: PipelineStatus, PipelineSource, PipelineSourceStatus, WebSocketMessage
  - Prettier format:check covering .ts files (required for CI)
affects:
  - 01-foundation-setup (all subsequent plans in this phase use these types)
  - All later phases that create .ts files (Prettier coverage, path alias, tsconfig inheritance)

# Tech tracking
tech-stack:
  added:
    - typescript@5.9.3
    - vue-tsc@2.2.12
    - "@vue/tsconfig@0.8.1"
    - "@types/node@22"
    - "@tsconfig/node22"
  patterns:
    - "TypeScript project references (tsconfig.json -> tsconfig.app.json + tsconfig.node.json)"
    - "allowJs: true + checkJs: false — include JS files without type-checking them"
    - "Barrel re-export pattern for domain types via src/types/index.ts"
    - "verbatimModuleSyntax: true for strict ESM import semantics"

key-files:
  created:
    - frontend/tsconfig.json
    - frontend/tsconfig.app.json
    - frontend/tsconfig.node.json
    - frontend/env.d.ts
    - frontend/src/types/gene.ts
    - frontend/src/types/auth.ts
    - frontend/src/types/api.ts
    - frontend/src/types/pipeline.ts
    - frontend/src/types/index.ts
  modified:
    - frontend/vite.config.ts (renamed from vite.config.js via git mv)
    - frontend/package.json (scripts + devDependencies)
    - frontend/eslint.config.js (added .ts to file patterns)

key-decisions:
  - "allowJs: true + checkJs: false chosen to avoid hundreds of type errors from existing JS codebase while enabling strict type checking for new .ts files"
  - "verbatimModuleSyntax: true enforced to ensure ESM-only import style in all new TS files"
  - "@tsconfig/node22 explicitly installed (not relied on as transitive dep) so tsconfig.node.json extends it reliably"
  - "git mv used for vite.config rename to preserve full commit history"

patterns-established:
  - "All new TS files use named exports and import type for type-only imports"
  - "Domain types live in src/types/ with one file per domain and barrel index.ts"
  - "Prettier format:check must cover .ts files — update scripts whenever new file types added"

# Metrics
duration: 2m 23s
completed: 2026-02-28
---

# Phase 1 Plan 1: TypeScript and Build Configuration Summary

**TypeScript strict-mode project references with allowJs coexistence, vite.config.ts, and domain type interfaces for Gene, Auth, API, and Pipeline entities**

## Performance

- **Duration:** 2m 23s
- **Started:** 2026-02-28T09:06:09Z
- **Completed:** 2026-02-28T09:08:32Z
- **Tasks:** 2
- **Files modified:** 12 (9 created, 3 modified, 1 renamed)

## Accomplishments

- TypeScript toolchain installed (typescript 5.9.3, vue-tsc 2.2.12, @vue/tsconfig, @tsconfig/node22) with project references separating app and node concerns
- Strict mode enabled with allowJs/checkJs-false so existing JavaScript files coexist without errors while new TypeScript gets full type checking
- All major domain entity interfaces created in src/types/ covering Gene, Auth, JSON:API responses, and Pipeline status
- Prettier format:check and ESLint now cover .ts files, ensuring CI passes for all future TypeScript additions

## Task Commits

Each task was committed atomically:

1. **Task 1: Install TypeScript packages and create tsconfig project references** - `489e106` (chore)
2. **Task 2: Rename vite.config to TypeScript and create domain type interfaces** - `60e4464` (feat)

**Plan metadata:** (docs commit — see below)

## Files Created/Modified

- `frontend/tsconfig.json` - Root tsconfig with project references and @/ path alias
- `frontend/tsconfig.app.json` - App tsconfig extending @vue/tsconfig/tsconfig.dom.json with strict, allowJs, checkJs: false
- `frontend/tsconfig.node.json` - Node tsconfig extending @tsconfig/node22 for vite.config.*
- `frontend/env.d.ts` - Vite ImportMetaEnv globals, Vue .vue module declaration, __APP_VERSION__
- `frontend/vite.config.ts` - Renamed from vite.config.js (git mv, content unchanged)
- `frontend/src/types/gene.ts` - Gene, GeneDetail, EvidenceSource, GeneListParams interfaces
- `frontend/src/types/auth.ts` - User, UserRole, LoginRequest, LoginResponse, AuthState interfaces
- `frontend/src/types/api.ts` - JsonApiResponse<T>, JsonApiListResponse<T>, JsonApiMeta, JsonApiLinks, JsonApiError, ApiErrorResponse interfaces
- `frontend/src/types/pipeline.ts` - PipelineStatus, PipelineSource, PipelineSourceStatus, WebSocketMessage interfaces
- `frontend/src/types/index.ts` - Barrel re-export for all type modules
- `frontend/package.json` - Added TS devDependencies, updated format/format:check scripts to include .ts files
- `frontend/eslint.config.js` - Added .ts to file patterns, added *.config.ts to ignores

## Decisions Made

- **allowJs + checkJs: false**: Enabled so existing .js files are compiled (for path resolution) but not type-checked. This avoids hundreds of immediate type errors from the legacy JS codebase while enabling strict checking for all new .ts files.
- **verbatimModuleSyntax: true**: Enforced from day one so all new TS files use `import type` for type-only imports, preventing issues with bundlers and tree-shaking.
- **@tsconfig/node22 explicit install**: Installed directly (not relied on as a transitive dep of @vue/tsconfig) so tsconfig.node.json's `extends` directive resolves reliably regardless of dependency hoisting changes.
- **git mv for vite.config rename**: Used `git mv vite.config.js vite.config.ts` to preserve full commit history on the config file, making future `git blame` and `git log --follow` useful.

## Deviations from Plan

None - plan executed exactly as written.

## Issues Encountered

None.

## User Setup Required

None - no external service configuration required.

## Next Phase Readiness

- TypeScript infrastructure is in place: all subsequent plans in Phase 1 and later phases can create .ts files and have them type-checked, formatted, and linted by CI.
- The domain type interfaces in src/types/ are stubs — they will be refined as actual component migration proceeds in later plans.
- vite.config.ts is production-ready and builds successfully (verified: 1357 modules transformed, exit 0).
- No blockers for plans 01-02 onward.

---
*Phase: 01-foundation-setup*
*Completed: 2026-02-28*
