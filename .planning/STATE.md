# Project State

## Project Reference

See: .planning/PROJECT.md (updated 2026-02-28)

**Core value:** Researchers and clinicians can quickly find, explore, and evaluate kidney disease gene evidence
**Current focus:** v0.2.0 Frontend Migration — Phase 2 (Plan 2 complete)

## Current Position

Phase: 2 of 9 (02-typescript-migration) — In progress
Plan: 2 of 3 in phase (02-02 complete)
Status: 02-02 complete — API layer migration done (client + 12 modules + 2 services)
Last activity: 2026-02-28 - Completed 02-02-PLAN.md (API client + 12 API modules + 2 services migrated, 23 tests added)

Progress: [████░░░░░░] ~20%

## Performance Metrics

**Velocity:**
- Total plans completed: 5
- Average duration: 6m 22s
- Total execution time: 30m 48s (Phase 01: 12m 0s, Phase 02 so far: 18m 48s)

**By Phase:**

| Phase | Plans | Total | Avg/Plan |
|-------|-------|-------|----------|
| 01-foundation-setup | 3 | 12m 0s | 4m 0s |
| 02-typescript-migration | 2 (of 3) | 18m 48s | 9m 24s |

*Updated after each plan completion*

## Accumulated Context

### Decisions

- Feature branch strategy with worktrees for parallel execution
- Vitest component testing added during migration (not deferred)
- All 9 phases in single milestone to minimize coexistence window
- zod pinned to v3.24 (v4 incompatible with vee-validate peer deps)
- tailwind-merge must be v3.x for Tailwind v4 compatibility
- shadcn-vue uses reka-ui (not radix-vue) — use shadcn-vue.com docs only
- **01-01:** allowJs: true + checkJs: false chosen to coexist with legacy JS without type errors
- **01-01:** verbatimModuleSyntax: true enforced from day one for ESM-only import style
- **01-01:** @tsconfig/node22 explicitly installed (not relied on as transitive dep)
- **01-01:** git mv used for vite.config rename to preserve commit history
- **01-02:** @tailwindcss/vite plugin (no tailwind.config.js needed for v4)
- **01-02:** CSS layer order: theme < base < vuetify < components < utilities
- **01-02:** vuetify/styles imported via @layer(vuetify) in main.css (removed from vuetify.js)
- **01-02:** OKLCH color space for all CSS custom properties
- **01-02:** components.json uses "config": "" (empty) — correct for Tailwind v4
- **01-02:** @typescript-eslint/parser added to eslint.config.js (pre-existing ESLint gap fixed)
- **01-03:** jsdom over happy-dom for Vitest (better DOM spec compliance, plan spec)
- **01-03:** Separate vitest.config.ts from vite.config.ts (test isolation)
- **01-03:** No custom SVGs for icon migration (context from labels, not icons)
- **01-03:** mdi-vuejs dropped (1 icon total) — purely decorative Vue.js logo
- **01-03:** 198 MDI icons mapped: 92 direct / 68 close / 29 generic / 9 drop
- **02-01:** WindowLogService inline interface in env.d.ts (not import from logService.js) to avoid forward reference — refine in 02-02 when logService.ts migrated
- **02-01:** EvidenceData union includes Record<string, unknown> fallback for HGNC/gnomAD/GTEx (not rendered by frontend views)
- **02-01:** debounce.ts flush() accepts args for type compat but uses lastArgs internally (documented)
- **02-01:** 4 pre-existing JS silent bugs fixed by TypeScript strict mode (warning→warn, 3-arg error, undefined vs null, index access)
- **02-02:** LogService exported as class so Window.logService in env.d.ts uses actual class type (import() syntax avoids top-level import in declaration file)
- **02-02:** Admin modules return Promise<AxiosResponse<T>> (raw response) — callers use .data, preserving existing behavior without component changes
- **02-02:** getCacheNamespaces exception: returns processed CacheNamespacesResult (not raw AxiosResponse) to preserve async aggregation logic
- **02-02:** LogLevel as const for literal string type inference on _log() level parameter
- **02-02:** LOG_LEVEL_PRIORITY lookup uses ?? 0 for TypeScript strict no-unchecked-indexed-access compliance

### Pending Todos

None yet.

### Blockers / Concerns

- **Phase 3 prerequisite: RESOLVED** — Icon audit complete (01-icon-audit.md). All 198 MDI icons mapped. 1 dropped (mdi-vuejs). Phase 3 planning can now finalize.
- **Phase 5 prerequisite:** Evidence tier OKLCH color values require design sign-off before GeneDetail migration
- **Phase 6 research flag:** Multi-select chip pattern (Combobox + TagsInput) is MEDIUM confidence — build isolated prototype before planning Phase 6
- **02-02: RESOLVED** — Window.logService now uses actual LogService class type (inline interface removed)

## Session Continuity

Last session: 2026-02-28T11:20:18Z
Stopped at: Completed 02-02-PLAN.md — API layer (client + 12 modules + 2 services) migrated to TypeScript
Resume file: None
