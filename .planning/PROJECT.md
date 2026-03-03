# Kidney-Genetics Database

## What This Is

A modern web platform for curating and exploring kidney disease-related genes. Python/FastAPI backend with Vue.js frontend, PostgreSQL database. 571+ genes with annotations from 9 sources, admin panel with pipeline management, and interactive network analysis visualizations. Currently at production-ready Alpha (v0.1.0).

## Core Value

Researchers and clinicians can quickly find, explore, and evaluate kidney disease gene evidence with confidence in the data quality and completeness.

## Last Completed Milestone: v0.2.0 Frontend Migration

**Status:** COMPLETE (2026-03-01)

**What shipped:**
- Complete TypeScript migration (strict mode) across all 40+ JS files and 73 Vue components
- Replaced Vuetify 3 with shadcn-vue (Reka UI primitives) + Tailwind CSS v4
- Replaced MDI icons with Lucide icons
- Replaced Vuetify data tables with TanStack Table
- Replaced Vuetify forms with vee-validate + Zod
- Added Vitest component testing for migrated components
- Zero Vuetify dependencies remaining
- Smaller bundle size and faster builds

## Requirements

### Validated

<!-- Shipped and confirmed valuable in v0.1.0 + v0.2.0 -->

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
- TypeScript strict mode across entire frontend
- Tailwind CSS v4 + shadcn-vue component system
- TanStack Table with server-side pagination/sorting/filtering
- vee-validate + Zod typed forms
- Lucide icons (tree-shakeable, Vue-native)
- vue-sonner toast notifications
- VueUse useColorMode theme management
- Vitest component tests
- Complete Vuetify removal (zero references)

### Active

No active milestone. Next milestone TBD.

## Key Decisions

| Decision | Rationale | Outcome |
|----------|-----------|---------|
| shadcn-vue over PrimeVue/Headless UI | Full component ownership (source in repo), Reka UI primitives, excellent TS support, smaller bundle | Shipped v0.2.0 |
| Tailwind CSS v4 (not v3) | 10x faster builds, CSS-first config, built-in @layer support | Shipped v0.2.0 |
| TanStack Table for data tables | Composable, headless, TS-first — replaces Vuetify's opinionated v-data-table | Shipped v0.2.0 |
| vee-validate + Zod for forms | End-to-end type safety from schema to form values | Shipped v0.2.0 |
| Lucide over Heroicons/Phosphor | Good coverage (~1500 icons), tree-shakeable, Vue-native component | Shipped v0.2.0 |
| All 9 phases in single milestone | Complete migration avoids long coexistence period | Shipped v0.2.0 |
| Add Vitest during migration | Test as we migrate rather than backfilling later | Shipped v0.2.0 |

---
*Last updated: 2026-03-03 — v0.2.0 Frontend Migration complete*
