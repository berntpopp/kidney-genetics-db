# Roadmap: Kidney-Genetics Database v0.2.0 Frontend Migration

## Overview

Migrate the entire frontend from JavaScript + Vuetify 3 to TypeScript + Tailwind CSS v4 + shadcn-vue across 9 sequential phases. Each phase ends in a working, buildable application. Phases 1 and 2 are non-visual infrastructure work; Phase 3 establishes the app shell all pages depend on; Phases 4-8 migrate features in order of complexity; Phase 9 removes all Vuetify dependencies.

## Milestones

- 🚧 **v0.2.0 Frontend Migration** — Phases 1-9 (in progress)

## Phases

**Phase Numbering:**
- Integer phases (1-9): Planned milestone work in execution order
- Decimal phases: Urgent insertions via `/gsd:insert-phase` if needed

- [x] **Phase 1: Foundation Setup** — Install and configure TypeScript, Tailwind v4, shadcn-vue, Vitest, and audit icons without changing any UI
- [ ] **Phase 2: TypeScript Migration** — Migrate all non-component files (stores, API modules, composables, utils, router) to TypeScript
- [ ] **Phase 3: App Shell, Navigation, Auth, Feedback, Icons** — Migrate the application skeleton, authentication UI, toast system, and replace all icons
- [ ] **Phase 4: Simple Public Pages** — Migrate five low-complexity public views using established component patterns
- [ ] **Phase 5: Gene Detail and Evidence Components** — Migrate the primary public detail page and all associated domain components
- [ ] **Phase 6: Data Tables** — Migrate GeneTable and all admin data tables to TanStack Table with server-side pagination
- [ ] **Phase 7: Admin Panel** — Migrate all 11 admin views, forms, and the sidebar navigation
- [ ] **Phase 8: Network Analysis and Visualizations** — Migrate visualization wrappers while preserving D3/Cytoscape rendering internals
- [ ] **Phase 9: Cleanup and Vuetify Removal** — Remove all Vuetify dependencies, clean coexistence hacks, verify zero references

## Phase Details

### Phase 1: Foundation Setup

**Goal:** TypeScript, Tailwind CSS v4, shadcn-vue, and Vitest are installed and configured so that every subsequent phase can build on a stable, conflict-free foundation — with zero visual changes to the running application.

**Dependencies:** None (first phase)

**Requirements:** FNDN-01, FNDN-02, FNDN-03, FNDN-04, FNDN-05, FNDN-06, FNDN-07, FNDN-08, FNDN-09, FNDN-10, TEST-01

**Success Criteria:**
1. `npm run build` and `npm run dev` succeed with no errors after all tooling changes
2. Tailwind utility classes applied to a test element render correctly alongside Vuetify components on the same page (no CSS preflight conflicts)
3. shadcn-vue `components.json` is initialized and `npx shadcn-vue add button` installs a component into `src/components/ui/` without errors
4. A Vitest smoke test (`vitest run`) passes with at least one passing test
5. An MDI icon audit document exists listing all 198 unique icons with Lucide equivalents or gap-resolution decisions for the ~30-40 without direct matches

**Estimated complexity:** MEDIUM
**Research needed:** No — all tooling setup is precisely specified in research (STACK.md, ARCHITECTURE.md). All configurations are deterministic.

**Plans:** 3 plans in 3 waves (sequential)

Plans:
- [x] 01-01-PLAN.md — TypeScript packages, tsconfig project references, vite.config.ts rename, domain type interfaces
- [x] 01-02-PLAN.md — Tailwind CSS v4 + shadcn-vue initialization + CSS @layer coexistence + cn() utility
- [x] 01-03-PLAN.md — Vitest configuration with smoke test + Makefile CI integration + MDI icon audit

---

### Phase 2: TypeScript Migration

**Goal:** All non-component TypeScript migration is complete so that every subsequent Vue component migration automatically receives typed data from correctly typed stores, API modules, and composables — with zero visual changes to the running application.

**Dependencies:** Phase 1

**Requirements:** TSML-01, TSML-02, TSML-03, TSML-04, TSML-05, TSML-06, TSML-07, TSML-08, TEST-04, TEST-05

**Success Criteria:**
1. `vue-tsc --noEmit` exits with zero errors across all migrated `.ts` files
2. Both Pinia stores (auth, logStore) have typed state, getters, and actions — TypeScript catches a type error if an action returns the wrong shape
3. All 12 API modules return typed response interfaces — callers receive autocompletion for response fields
4. All 6 composables have typed return values — Vue components using them receive typed data
5. Vitest tests for composables and API modules pass in CI (`make ci-frontend`)

**Estimated complexity:** MEDIUM
**Research needed:** No — TypeScript migration of non-component files follows established patterns with `allowJs: true, checkJs: false`.

**Plans:** TBD

Plans:
- [ ] 02-01: main.ts, router, stores migration (TSML-01, TSML-02, TSML-06)
- [ ] 02-02: API modules and services migration (TSML-03, TSML-07)
- [ ] 02-03: Composables, utilities, type checking (TSML-04, TSML-05, TSML-08, TEST-04, TEST-05)

---

### Phase 3: App Shell, Navigation, Auth, Feedback, Icons

**Goal:** The application skeleton (header, footer, navigation, mobile drawer, dark mode, auth modals, toast notifications, and all icons) is fully migrated to shadcn-vue + Lucide so that every page that loads after this phase renders inside the new layout system.

**Dependencies:** Phase 2

**Requirements:** LNAV-01, LNAV-02, LNAV-03, LNAV-04, LNAV-05, LNAV-06, LNAV-07, AUTH-01, AUTH-02, AUTH-03, AUTH-04, TFBK-01, TFBK-02, TFBK-03, ICON-01, ICON-02, ICON-03, ICON-04, TEST-02

**Success Criteria:**
1. The application loads with a Tailwind-based layout (no `<v-app>` or `<v-main>`) and all existing pages remain accessible via the navigation menu
2. The mobile navigation drawer opens and closes correctly at viewport widths below 768px using the shadcn-vue Sheet component
3. Dark mode toggles between light and dark themes with both Vuetify components (still present in pages) and shadcn-vue components (in the shell) rendering correctly — no flash or mismatch between `.v-theme--dark` and `.dark` classes
4. A user can log in via the LoginModal, see a toast notification on success or error, and the auth state updates in the header (user avatar visible, login button hidden)
5. All navigation icons render as Lucide SVG components — no MDI font glyphs visible in the header, footer, or user menu

**Estimated complexity:** HIGH
**Research needed:** Yes — icon mapping for the 198 unique MDI icons (gap audit from Phase 1) must be finalized before Phase 3 begins. Visual testing at 320px/768px/1280px breakpoints required after completion. Dark mode dual-system synchronization watcher must be manually verified.

**Plans:** TBD

Plans:
- [ ] 03-01: App shell and layout migration (LNAV-01, LNAV-02, LNAV-03, LNAV-04)
- [ ] 03-02: User menu, breadcrumbs, and dark mode toggle (LNAV-05, LNAV-06, LNAV-07)
- [ ] 03-03: Auth modals with vee-validate + Zod (AUTH-01, AUTH-02, AUTH-03, AUTH-04)
- [ ] 03-04: Toast system and icon replacement (TFBK-01, TFBK-02, TFBK-03, ICON-01, ICON-02, ICON-03, ICON-04, TEST-02)

---

### Phase 4: Simple Public Pages

**Goal:** Five low-complexity public views are migrated to Tailwind + shadcn-vue using the component patterns established in Phase 3, proving the pattern works at page scale before tackling domain-complex views.

**Dependencies:** Phase 3

**Requirements:** SPGE-01, SPGE-02, SPGE-03, SPGE-04, SPGE-05

**Success Criteria:**
1. Home, About, and DataSources pages render with Tailwind layouts — no Vuetify grid classes (`v-row`, `v-col`) visible in page source
2. The Profile page displays user information and all interactive elements (password change button, profile edits) work correctly
3. The Dashboard page displays all statistics cards and overview metrics with the same data as before migration
4. All five pages pass `npm run build` with no TypeScript errors in their component files

**Estimated complexity:** LOW
**Research needed:** No — straightforward component mapping; all patterns are established in Phase 3.

**Plans:** TBD

Plans:
- [ ] 04-01: Home, About, DataSources migration (SPGE-01, SPGE-02, SPGE-03)
- [ ] 04-02: Profile and Dashboard migration (SPGE-04, SPGE-05)

---

### Phase 5: Gene Detail and Evidence Components

**Goal:** GeneDetail.vue and all 16 associated gene info and evidence components are migrated so that the primary public-facing detail page — the most domain-complex view in the application — functions fully with shadcn-vue components.

**Dependencies:** Phase 3

**Requirements:** GDEV-01, GDEV-02, GDEV-03, GDEV-04, GDEV-05, GDEV-06, GDEV-07, TEST-03

**Success Criteria:**
1. A gene detail page loads with shadcn-vue Tabs replacing `v-tabs` — all tab panels (Overview, Evidence, Phenotypes, etc.) switch correctly and preserve URL state
2. Evidence tier badges render in the correct colors for each tier (Definitive, Strong, Moderate, Limited, No Known Disease Relationship) — verified against the pre-migration color baseline
3. Evidence expansion panels (ClinGen, GenCC, HPO, PanelApp, DiagnosticPanels, Literature, PubTator) open and close correctly using shadcn-vue Accordion
4. The TierHelpDialog opens when clicked and displays correct tier explanation content
5. Vitest component tests for EvidenceCard and EvidenceTierBadge pass

**Estimated complexity:** HIGH
**Research needed:** Yes — evidence tier OKLCH color values must be mapped from Vuetify semantic colors before migration. Accordion + Tabs composition in GeneDetail needs manual testing with real data (571+ genes). Requires design sign-off on color mapping.

**Plans:** TBD

Plans:
- [ ] 05-01: GeneDetail tabs and Accordion structure (GDEV-01, GDEV-07)
- [ ] 05-02: Gene info components (GDEV-02)
- [ ] 05-03: Evidence components and tier system (GDEV-03, GDEV-04, GDEV-05, GDEV-06, TEST-03)

---

### Phase 6: Data Tables

**Goal:** GeneTable and all admin data tables are migrated to TanStack Table with server-side pagination, sorting, and filtering fully working — this is the highest-risk phase due to TanStack Table's non-obvious pagination reset behavior and the multi-select chip filter pattern.

**Dependencies:** Phase 3

**Requirements:** DTBL-01, DTBL-02, DTBL-03, DTBL-04, DTBL-05, DTBL-06, DTBL-07, DTBL-08, DTBL-09

**Success Criteria:**
1. The Genes page loads with a TanStack Table displaying 571+ genes with server-side pagination — navigating to page 3 then applying a filter resets to page 1 automatically (not staying on page 3 of a smaller result set)
2. Column header click sorts the gene table ascending/descending and the sort indicator updates correctly
3. Multi-select chip filters for evidence sources and tiers work — selecting multiple values narrows the gene list and selected values appear as removable chips
4. Clicking any gene row navigates to that gene's detail page
5. Score and evidence tier columns render correctly with badge/chip styling (not plain text)

**Estimated complexity:** HIGH
**Research needed:** Yes — the multi-select chip pattern (Combobox + TagsInput composition) is MEDIUM confidence from research; build an isolated `MultiSelect.vue` prototype before committing the full GeneTable migration. URL sync from `parseUrlParams`/`updateUrl` → TanStack Table state needs explicit mapping documented before planning begins.

**Plans:** TBD

Plans:
- [ ] 06-01: TanStack Table infrastructure and DataTable wrapper (DTBL-01)
- [ ] 06-02: GeneTable core migration — pagination and sorting (DTBL-02, DTBL-03, DTBL-05, DTBL-09)
- [ ] 06-03: GeneTable filtering, cell renderers, and Genes.vue controls (DTBL-04, DTBL-06, DTBL-07)
- [ ] 06-04: EnrichmentTable and admin data tables (DTBL-08)

---

### Phase 7: Admin Panel

**Goal:** All 11 admin views, 13 admin form dialogs, and the admin sidebar navigation are migrated to shadcn-vue so that administrators have a fully functional panel using the new component system.

**Dependencies:** Phases 3 and 6 (admin tables depend on DataTable infrastructure from Phase 6)

**Requirements:** ADMN-01, ADMN-02, ADMN-03, ADMN-04, ADMN-05, ADMN-06, ADMN-07, ADMN-08, ADMN-09, ADMN-10, ADMN-11, ADMN-12, ADMN-13

**Success Criteria:**
1. The admin sidebar navigation renders with shadcn-vue Sidebar — persistent collapse state works and keyboard shortcuts function
2. AdminPipeline shows pipeline controls and real-time progress via WebSocket — the progress bar updates during an active pipeline run
3. AdminUserManagement displays a TanStack Table of users — create, edit, and delete actions open dialogs with vee-validate + Zod typed forms
4. All destructive admin actions (delete user, restore backup, clear cache) show an AlertDialog confirmation before executing
5. All 5 backup dialogs (Create, Delete, Details, Filters, Restore) open and close correctly and their forms validate with Zod schemas

**Estimated complexity:** HIGH
**Research needed:** No — admin forms and dialogs use patterns established in Phase 3; admin tables use infrastructure from Phase 6.

**Plans:** TBD

Plans:
- [ ] 07-01: Admin layout and dashboard (ADMN-01, ADMN-02)
- [ ] 07-02: AdminPipeline with WebSocket (ADMN-03)
- [ ] 07-03: Admin data tables — UserManagement, GeneStaging, Annotations, CacheManagement, LogViewer, Releases, HybridSources (ADMN-04, ADMN-05, ADMN-06, ADMN-07, ADMN-08, ADMN-09, ADMN-12)
- [ ] 07-04: Admin dialogs — Backups and Settings with typed Zod forms (ADMN-10, ADMN-11, ADMN-13)

---

### Phase 8: Network Analysis and Visualizations

**Goal:** NetworkAnalysis, all D3 chart wrappers, and GeneStructure are migrated to Tailwind layouts while Cytoscape and D3 rendering internals remain completely unchanged.

**Dependencies:** Phase 3

**Requirements:** NTVZ-01, NTVZ-02, NTVZ-03, NTVZ-04, NTVZ-05, NTVZ-06

**Success Criteria:**
1. The Network Analysis page loads and Cytoscape renders a gene interaction network — pan, zoom, and node click interactions work identically to before migration
2. The network search overlay (gene search input + results card) renders in the correct position over the Cytoscape canvas
3. The ClusterDetailsDialog opens when a cluster is selected and displays cluster data correctly
4. All D3 chart wrappers on the Dashboard render their visualizations — no chart is blank or incorrectly sized after the layout class migration
5. GeneStructure.vue renders its visualization without layout regressions

**Estimated complexity:** MEDIUM
**Research needed:** No — D3/Cytoscape internals are unchanged; only wrapper layout classes migrate. All component patterns are established by Phase 3.

**Plans:** TBD

Plans:
- [ ] 08-01: NetworkAnalysis layout, NetworkGraph wrapper, search overlay (NTVZ-01, NTVZ-02, NTVZ-03)
- [ ] 08-02: ClusterDetailsDialog, D3 chart wrappers, GeneStructure (NTVZ-04, NTVZ-05, NTVZ-06)

---

### Phase 9: Cleanup and Vuetify Removal

**Goal:** Every Vuetify reference is removed from the codebase, the CSS coexistence layer hacks are cleaned up, and the final bundle is verified to contain zero Vuetify or MDI font assets.

**Dependencies:** Phases 1-8 (all component migration must be complete)

**Requirements:** CLNP-01, CLNP-02, CLNP-03, CLNP-04, CLNP-05, CLNP-06, CLNP-07, CLNP-08, TEST-06

**Success Criteria:**
1. `grep -rn "v-icon\|v-btn\|v-card\|v-dialog\|v-data-table" frontend/src/` returns zero results
2. `grep -rn "vuetify\|@mdi/font\|v-theme" frontend/src/` returns zero results
3. `npm run build` succeeds with the Vuetify plugin removed and `@import "tailwindcss"` as a single import in `main.css`
4. The built bundle does not include `@mdi/font` — bundle size is measurably smaller than the pre-migration baseline (target: at least 250KB reduction from MDI font removal)
5. All Vitest tests pass in CI (`make ci-frontend` exits 0 with no skipped tests)

**Estimated complexity:** LOW
**Research needed:** No — mechanical cleanup phase; all patterns are established. Final grep audits are documented in research (PITFALLS.md).

**Plans:** TBD

Plans:
- [ ] 09-01: Remove Vuetify package, plugin, and all remaining references (CLNP-01, CLNP-02, CLNP-03, CLNP-04, CLNP-05)
- [ ] 09-02: Clean CSS coexistence hacks and verify build + bundle (CLNP-06, CLNP-07, CLNP-08, TEST-06)

---

## Progress

**Execution order:** 1 → 2 → 3 → 4 → 5 → 6 → 7 → 8 → 9
**Parallelization note:** Phases 4, 5, 6, and 8 all depend only on Phase 3 and can be partially parallelized if worktrees are used. Phase 7 additionally requires Phase 6 (DataTable infrastructure).

| Phase | Goal | Plans | Status | Completed |
|-------|------|-------|--------|-----------|
| 1. Foundation Setup | Install TypeScript, Tailwind v4, shadcn-vue, Vitest; icon audit | 3 plans | ✓ Complete | 2026-02-28 |
| 2. TypeScript Migration | Migrate stores, API modules, composables, utils to TS | TBD | Not started | - |
| 3. App Shell + Navigation + Auth + Icons | Migrate app skeleton, auth, toast, all icons | TBD | Not started | - |
| 4. Simple Public Pages | Migrate Home, About, DataSources, Profile, Dashboard | TBD | Not started | - |
| 5. Gene Detail + Evidence | Migrate GeneDetail and 16 domain components | TBD | Not started | - |
| 6. Data Tables | Migrate GeneTable + admin tables to TanStack Table | TBD | Not started | - |
| 7. Admin Panel | Migrate 11 admin views + 13 form dialogs | TBD | Not started | - |
| 8. Network + Visualizations | Migrate network and D3 wrappers | TBD | Not started | - |
| 9. Cleanup + Vuetify Removal | Remove all Vuetify; verify zero references | TBD | Not started | - |

---

## Coverage

**v1 Requirements:** 90 total
**Mapped:** 90 / 90
**Unmapped:** 0

| Category | Count | Phase |
|----------|-------|-------|
| FNDN (Foundation) | 10 | Phase 1 |
| TEST-01 (Vitest config) | 1 | Phase 1 |
| TSML (TypeScript Migration) | 8 | Phase 2 |
| TEST-04, TEST-05 (Composable + API tests) | 2 | Phase 2 |
| LNAV (Layout + Navigation) | 7 | Phase 3 |
| AUTH (Authentication UI) | 4 | Phase 3 |
| TFBK (Toast + Feedback) | 3 | Phase 3 |
| ICON (Icon System) | 4 | Phase 3 |
| TEST-02 (UI component tests, written as migrated) | 1 | Phase 3 (ongoing through Phase 8) |
| SPGE (Simple Pages) | 5 | Phase 4 |
| GDEV (Gene Detail + Evidence) | 7 | Phase 5 |
| TEST-03 (Domain component tests) | 1 | Phase 5 (ongoing through Phase 7) |
| DTBL (Data Tables) | 9 | Phase 6 |
| ADMN (Admin Panel) | 13 | Phase 7 |
| NTVZ (Network + Visualizations) | 6 | Phase 8 |
| CLNP (Cleanup + Removal) | 8 | Phase 9 |
| TEST-06 (All tests pass in CI) | 1 | Phase 9 |
| **Total** | **90** | |

---

*Roadmap created: 2026-02-28*
*Milestone: v0.2.0 Frontend Migration*
