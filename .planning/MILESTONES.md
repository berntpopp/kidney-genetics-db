# Milestones

## v0.1.0 — Production-Ready Alpha (Completed)

**Shipped:** Pre-GSD (before 2026-02-28)
**Phases:** N/A (built before GSD adoption)

**What shipped:**
- Kidney-Genetics Database with 571+ genes and 9 annotation sources
- FastAPI backend with SQLAlchemy + PostgreSQL
- Vue.js + Vuetify 3 frontend with 73 components
- JWT authentication (admin/curator/public roles)
- Admin panel (users, cache, pipeline, backups, settings)
- Network analysis with Cytoscape
- Dashboard with D3.js visualizations
- ARQ background worker for pipeline operations
- Docker deployment (dev, hybrid, production modes)

---

## v0.2.0 — Frontend Migration (Completed)

**Started:** 2026-02-28
**Completed:** 2026-03-01
**Goal:** Migrate frontend from JS + Vuetify 3 to TypeScript + Tailwind CSS v4 + shadcn-vue
**Phases:** 9 phases, 23 plans

**What shipped:**
- Complete TypeScript migration (strict mode) — 40+ JS files, 73 Vue components
- Tailwind CSS v4 + shadcn-vue (Reka UI primitives) replacing Vuetify 3
- TanStack Table replacing v-data-table (server-side pagination/sorting/filtering)
- vee-validate + Zod replacing Vuetify forms (end-to-end type safety)
- Lucide icons replacing MDI icons (198 icons mapped)
- vue-sonner replacing v-snackbar
- VueUse useColorMode theme management
- Vitest component testing (added during migration)
- Zero Vuetify dependencies — complete removal
- Bundle size reduction (MDI font removed)

**Post-migration backend work (also on main):**
- Pipeline session isolation (per-source DB sessions for parallel updates)
- All 10 annotation sources optimized to bulk file/batch APIs
- Stale annotation version fix (unique constraint change)
- Pipeline resource benchmarking (peak RSS 2,227 MB, safe for 8 GB VPS)
- Gene count grew from 571 to 5,080+ curated genes

---

## Next Milestone — TBD

No next milestone defined yet.
