# Kidney-Genetics Database

## What This Is

A modern web platform for curating and exploring kidney disease-related genes. Python/FastAPI backend with Vue.js frontend, PostgreSQL database. 571+ genes with annotations from 9 sources, admin panel with pipeline management, and interactive network analysis visualizations. Currently at production-ready Alpha (v0.1.0).

## Core Value

Researchers and clinicians can quickly find, explore, and evaluate kidney disease gene evidence with confidence in the data quality and completeness.

## Current Milestone: v0.2.0 Frontend Migration

**Goal:** Migrate the entire frontend from JavaScript + Vuetify 3 to TypeScript + Tailwind CSS v4 + shadcn-vue, achieving type safety, smaller bundles, and full component ownership.

**Target features:**
- Complete TypeScript migration (strict mode) across all 40+ JS files and 73 Vue components
- Replace Vuetify 3 with shadcn-vue (Radix Vue primitives) + Tailwind CSS v4
- Replace MDI icons with Lucide icons
- Replace Vuetify data tables with TanStack Table
- Replace Vuetify forms with vee-validate + Zod
- Add Vitest component testing for migrated components
- Zero Vuetify dependencies remaining after migration
- Smaller bundle size and faster builds

## Requirements

### Validated

<!-- Shipped and confirmed valuable in v0.1.0 Alpha -->

- Gene browsing with server-side pagination, sorting, and filtering
- Gene detail pages with multi-source evidence display
- Evidence scoring and tier system
- 9 annotation source integrations (PanelApp, HPO, ClinGen, GenCC, PubTator, ClinVar, diagnostic panels, STRING PPI, mouse phenotypes)
- JWT authentication with admin/curator/public roles
- Admin panel (user management, cache control, pipeline management, backups, settings)
- Network analysis with Cytoscape visualization
- Dashboard with D3.js statistical visualizations
- Dark/light theme support
- WebSocket real-time pipeline progress
- ARQ background worker for pipeline operations

### Active

<!-- v0.2.0 scope — Frontend migration -->

- [ ] TypeScript strict mode across entire frontend
- [ ] Tailwind CSS v4 + shadcn-vue replacing Vuetify 3
- [ ] TanStack Table replacing v-data-table
- [ ] vee-validate + Zod replacing Vuetify forms
- [ ] Lucide icons replacing MDI icons
- [ ] vue-sonner replacing v-snackbar
- [x] VueUse useColorMode replacing Vuetify useTheme
- [ ] Vitest component tests for migrated components
- [x] Complete Vuetify removal (zero references)
- [x] Bundle size reduction

### Out of Scope

- Backend changes — v0.2.0 is frontend-only
- New features or API endpoints — migration preserves existing functionality
- D3.js/Cytoscape/UpSet.js internals — visualization libraries stay as-is, only Vue wrappers change
- Mobile app — web-first continues
- Playwright E2E test rewrites — existing E2E tests should pass, new tests are Vitest unit/component only

## Context

- Frontend: 73 Vue components, 40 JS files, 22 views (11 public + 11 admin)
- Vuetify usage: 431 v-icon, 412 v-btn, 396 v-col, 350 v-chip, 254+ v-card occurrences
- Highest complexity: v-data-table (29 usages), v-form (18 usages) — require full architectural replacement
- Visualization libs (D3, Cytoscape, UpSet.js) are SVG/canvas-based and independent of UI framework
- No existing frontend unit tests — Vitest will be added during migration
- Vuetify and Tailwind will coexist during phased migration

## Constraints

- **Branching**: Single feature branch for entire migration, using worktrees for parallel phase execution
- **Coexistence**: Vuetify + Tailwind must coexist without CSS conflicts during migration (use @layer, import ordering)
- **Shippable phases**: Each phase must end in a working, buildable state
- **Backward compatibility**: All existing backend API contracts unchanged
- **Package manager**: npm for frontend (not yarn/pnpm)
- **Build tool**: Vite (existing)

## Key Decisions

| Decision | Rationale | Outcome |
|----------|-----------|---------|
| shadcn-vue over PrimeVue/Headless UI | Full component ownership (source in repo), Radix Vue primitives, excellent TS support, smaller bundle | -- Pending |
| Tailwind CSS v4 (not v3) | 10x faster builds, CSS-first config, built-in @layer support | -- Pending |
| TanStack Table for data tables | Composable, headless, TS-first — replaces Vuetify's opinionated v-data-table | -- Pending |
| vee-validate + Zod for forms | End-to-end type safety from schema to form values | -- Pending |
| Lucide over Heroicons/Phosphor | Good coverage (~1500 icons), tree-shakeable, Vue-native component | -- Pending |
| All 9 phases in single milestone | Complete migration avoids long coexistence period | -- Pending |
| Add Vitest during migration | Test as we migrate rather than backfilling later | -- Pending |

---
*Last updated: 2026-02-28 after milestone v0.2.0 initialization*
