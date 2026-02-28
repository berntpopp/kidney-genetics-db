# Project State

## Project Reference

See: .planning/PROJECT.md (updated 2026-02-28)

**Core value:** Researchers and clinicians can quickly find, explore, and evaluate kidney disease gene evidence
**Current focus:** v0.2.0 Frontend Migration — Phase 2 (Plan 1 complete)

## Current Position

Phase: 2 of 9 (02-typescript-migration) — In progress
Plan: 1 of 3 in phase (02-01 complete)
Status: 02-01 complete — foundation types and utility migration done
Last activity: 2026-02-28 - Completed 02-01-PLAN.md (types + 14 utility/config/plugin files migrated)

Progress: [███░░░░░░░] ~15%

## Performance Metrics

**Velocity:**
- Total plans completed: 4
- Average duration: 5m 54s
- Total execution time: 21m 36s (Phase 01: 12m 0s, Phase 02 so far: 9m 36s)

**By Phase:**

| Phase | Plans | Total | Avg/Plan |
|-------|-------|-------|----------|
| 01-foundation-setup | 3 | 12m 0s | 4m 0s |
| 02-typescript-migration | 1 (of 3) | 9m 36s | 9m 36s |

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

### Pending Todos

None yet.

### Blockers / Concerns

- **Phase 3 prerequisite: RESOLVED** — Icon audit complete (01-icon-audit.md). All 198 MDI icons mapped. 1 dropped (mdi-vuejs). Phase 3 planning can now finalize.
- **Phase 5 prerequisite:** Evidence tier OKLCH color values require design sign-off before GeneDetail migration
- **Phase 6 research flag:** Multi-select chip pattern (Combobox + TagsInput) is MEDIUM confidence — build isolated prototype before planning Phase 6
- **02-02 note:** WindowLogService interface in env.d.ts should be refined once logService.ts is migrated (replace inline interface with exported class type)

## Session Continuity

Last session: 2026-02-28T11:07:17Z
Stopped at: Completed 02-01-PLAN.md — foundation types and utility migration done
Resume file: None
