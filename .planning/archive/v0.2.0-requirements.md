# Requirements: Kidney-Genetics Database v0.2.0

**Defined:** 2026-02-28
**Core Value:** Researchers and clinicians can quickly find, explore, and evaluate kidney disease gene evidence

## v1 Requirements

Requirements for milestone v0.2.0 — Frontend Migration. Each maps to roadmap phases.

### Foundation (FNDN)

- [x] **FNDN-01**: TypeScript strict mode enabled across the entire frontend codebase
- [x] **FNDN-02**: tsconfig.json configured with strict: true, allowJs: true, path aliases (@/)
- [x] **FNDN-03**: Type definitions created for all domain interfaces (gene, auth, API responses, pipeline)
- [x] **FNDN-04**: Tailwind CSS v4 installed with @tailwindcss/vite plugin (no PostCSS)
- [x] **FNDN-05**: Tailwind v4 coexists with Vuetify without visual regressions (CSS @layer strategy, preflight disabled)
- [x] **FNDN-06**: shadcn-vue initialized with Reka UI primitives and components.json configured
- [x] **FNDN-07**: cn() utility function available at src/lib/utils.ts (clsx + tailwind-merge v3)
- [x] **FNDN-08**: Theme CSS variables mapped from Vuetify to shadcn-vue convention (--primary, --background, etc.) with light/dark mode
- [x] **FNDN-09**: Vitest installed and configured for component testing
- [x] **FNDN-10**: Complete MDI icon audit documenting all 198 unique icons and their Lucide equivalents (or custom solutions for ~30-40 gaps)

### TypeScript Migration (TSML)

- [x] **TSML-01**: main.js migrated to main.ts with typed app creation and plugin registration
- [x] **TSML-02**: Both Pinia stores (auth, logStore) migrated to TypeScript with typed state, getters, and actions
- [x] **TSML-03**: All 12 API modules migrated to TypeScript with typed request/response interfaces
- [x] **TSML-04**: All 6 composables migrated to TypeScript with typed return values
- [x] **TSML-05**: All 11 utility files migrated to TypeScript
- [x] **TSML-06**: Router migrated to TypeScript with typed route meta fields and navigation guards
- [x] **TSML-07**: WebSocket and logging services migrated to TypeScript
- [x] **TSML-08**: vue-tsc type checking passes with zero errors

### Layout & Navigation (LNAV)

- [x] **LNAV-01**: App shell replaced (v-app/v-main → Tailwind layout with min-h-screen)
- [x] **LNAV-02**: Header/app bar replaced with shadcn-vue NavigationMenu (responsive)
- [x] **LNAV-03**: Mobile navigation drawer replaced with shadcn-vue Sheet
- [x] **LNAV-04**: Footer replaced with Tailwind-styled custom footer
- [x] **LNAV-05**: User menu replaced with shadcn-vue DropdownMenu + Avatar
- [x] **LNAV-06**: Breadcrumbs replaced with shadcn-vue Breadcrumb component
- [x] **LNAV-07**: Theme toggle replaced with VueUse useColorMode() + ModeToggle component

### Authentication UI (AUTH)

- [x] **AUTH-01**: LoginModal migrated to shadcn-vue Dialog + Form (vee-validate + Zod schema)
- [x] **AUTH-02**: ForgotPasswordModal migrated to shadcn-vue Dialog + Form
- [x] **AUTH-03**: ChangePasswordModal migrated to shadcn-vue Dialog + Form
- [x] **AUTH-04**: Login/ForgotPassword views migrated with shadcn-vue components

### Toast & Feedback (TFBK)

- [x] **TFBK-01**: vue-sonner installed and configured as toast provider
- [x] **TFBK-02**: All v-snackbar usages replaced with toast() from vue-sonner
- [x] **TFBK-03**: Loading/success/error sequences use toast.promise() pattern

### Icons (ICON)

- [x] **ICON-01**: Lucide Vue Next installed and configured
- [x] **ICON-02**: Icon mapping module created (src/utils/icons.ts) mapping MDI names to Lucide components
- [x] **ICON-03**: All 431 v-icon usages replaced with Lucide components
- [x] **ICON-04**: Custom icon solutions for medical/scientific icons without Lucide equivalents

### Simple Pages (SPGE)

- [x] **SPGE-01**: Home.vue migrated (hero, feature cards, CTA with Tailwind + shadcn-vue)
- [x] **SPGE-02**: About.vue migrated (static content with Tailwind layout)
- [x] **SPGE-03**: DataSources.vue migrated (data source display)
- [x] **SPGE-04**: Profile.vue migrated (user profile page)
- [x] **SPGE-05**: Dashboard.vue migrated (statistics cards, overview metrics)

### Gene Detail & Evidence (GDEV)

- [x] **GDEV-01**: GeneDetail.vue migrated with shadcn-vue Tabs replacing v-tabs
- [x] **GDEV-02**: All 8 gene info components migrated (BasicInfo, Constraints, Expression, ClinVar, Phenotypes, MousePhenotypes, ProteinInteractions, InformationCard)
- [x] **GDEV-03**: All 8 evidence components migrated (EvidenceCard, ClinGen, GenCC, HPO, PanelApp, DiagnosticPanels, Literature, PubTator)
- [x] **GDEV-04**: EvidenceTierBadge migrated to shadcn-vue Badge with correct tier colors
- [x] **GDEV-05**: ScoreBreakdown migrated to shadcn-vue Card
- [x] **GDEV-06**: TierHelpDialog migrated to shadcn-vue Dialog
- [x] **GDEV-07**: Expansion panels replaced with shadcn-vue Accordion

### Data Tables (DTBL)

- [x] **DTBL-01**: Reusable DataTable infrastructure created (DataTable, ColumnHeader, Pagination, ViewOptions, FacetedFilter)
- [x] **DTBL-02**: GeneTable migrated to TanStack Table with server-side pagination (manualPagination, 0-based pageIndex handling)
- [x] **DTBL-03**: GeneTable server-side sorting works correctly
- [x] **DTBL-04**: GeneTable column-level filtering works (including multi-select with chips for sources/tiers)
- [x] **DTBL-05**: GeneTable row click navigation to gene detail preserved
- [x] **DTBL-06**: GeneTable custom cell renderers (score badges, evidence tiers) working
- [x] **DTBL-07**: Genes.vue search/filter controls migrated
- [x] **DTBL-08**: EnrichmentTable (network analysis) migrated to TanStack Table
- [x] **DTBL-09**: Pagination auto-resets on filter/sort changes (explicit watch implementation)

### Admin Panel (ADMN)

- [x] **ADMN-01**: Admin layout migrated (AdminHeader, AdminStatsCard, sidebar navigation)
- [x] **ADMN-02**: AdminDashboard.vue migrated (stats cards, overview)
- [x] **ADMN-03**: AdminPipeline.vue migrated (pipeline controls, Progress component, WebSocket integration preserved)
- [x] **ADMN-04**: AdminUserManagement migrated with TanStack Table + forms
- [x] **ADMN-05**: AdminGeneStaging migrated with TanStack Table
- [x] **ADMN-06**: AdminAnnotations migrated with TanStack Table
- [x] **ADMN-07**: AdminCacheManagement migrated with TanStack Table
- [x] **ADMN-08**: AdminLogViewer migrated with TanStack Table
- [x] **ADMN-09**: AdminReleases migrated with TanStack Table
- [x] **ADMN-10**: AdminBackups migrated (5 dialogs: Create, Delete, Details, Filters, Restore)
- [x] **ADMN-11**: AdminSettings migrated (SettingEditDialog, SettingHistoryDialog)
- [x] **ADMN-12**: AdminHybridSources migrated with TanStack Table
- [x] **ADMN-13**: All admin forms use vee-validate + Zod schemas

### Network & Visualizations (NTVZ)

- [x] **NTVZ-01**: NetworkAnalysis.vue layout migrated to Tailwind (Cytoscape integration preserved)
- [x] **NTVZ-02**: NetworkGraph.vue wrapper migrated (Cytoscape internals unchanged)
- [x] **NTVZ-03**: NetworkSearchOverlay migrated (Input + Card replacing v-text-field/v-card)
- [x] **NTVZ-04**: ClusterDetailsDialog migrated to shadcn-vue Dialog
- [x] **NTVZ-05**: All D3 chart Vue wrappers migrated (layout/styling only; D3 rendering unchanged)
- [x] **NTVZ-06**: GeneStructure.vue view migrated

### Cleanup & Removal (CLNP)

- [x] **CLNP-01**: Zero v- component tags remain in codebase
- [x] **CLNP-02**: Zero Vuetify utility classes remain in codebase
- [x] **CLNP-03**: Zero --v-theme-* CSS variable references remain in scoped styles
- [x] **CLNP-04**: vuetify and @mdi/font removed from package.json
- [x] **CLNP-05**: src/plugins/vuetify.js deleted and Vuetify plugin registration removed from main.ts
- [x] **CLNP-06**: Tailwind CSS coexistence hacks removed (selective imports replaced with full @import "tailwindcss")
- [x] **CLNP-07**: npm run build succeeds with zero Vuetify references
- [x] **CLNP-08**: Bundle size measured and reduced compared to pre-migration baseline

### Testing (TEST)

- [x] **TEST-01**: Vitest configured with Vue Test Utils and happy-dom/jsdom
- [x] **TEST-02**: Component tests written for all migrated shadcn-vue UI wrapper components
- [x] **TEST-03**: Component tests written for key domain components (GeneTable, EvidenceCard, LoginModal)
- [x] **TEST-04**: Composable tests written for all 6 migrated composables
- [x] **TEST-05**: API module tests written for typed API client and interceptors
- [x] **TEST-06**: All Vitest tests pass in CI pipeline

## v2 Requirements

Deferred to future milestones. Tracked but not in current roadmap.

### Enhanced Testing

- **ETEST-01**: Playwright E2E tests updated for new component selectors
- **ETEST-02**: Visual regression testing with Playwright screenshots
- **ETEST-03**: Accessibility testing automation (axe-core integration)

### Performance Optimization

- **PERF-01**: Code splitting per route (lazy loading all views)
- **PERF-02**: Component-level tree-shaking audit
- **PERF-03**: Lighthouse performance score > 90

### Design System

- **DSGN-01**: Design tokens documented and standardized
- **DSGN-02**: Storybook or Histoire for component documentation
- **DSGN-03**: Custom medical/scientific icon set

## Out of Scope

| Feature | Reason |
|---------|--------|
| Backend changes | v0.2.0 is frontend-only; API contracts unchanged |
| New features or endpoints | Migration preserves existing functionality only |
| D3.js/Cytoscape/UpSet.js internals | Visualization libraries are SVG/canvas-based and framework-independent |
| Mobile app | Web-first continues |
| Playwright E2E rewrites | Existing E2E should pass; new tests are Vitest only |
| Storybook/Histoire | Defer component documentation to future milestone |
| SSR/SSG | Not needed for this application |
| i18n/localization | Not in current scope |

## Traceability

| Requirement | Phase | Status |
|-------------|-------|--------|
| FNDN-01 | Phase 1 | Complete |
| FNDN-02 | Phase 1 | Complete |
| FNDN-03 | Phase 1 | Complete |
| FNDN-04 | Phase 1 | Complete |
| FNDN-05 | Phase 1 | Complete |
| FNDN-06 | Phase 1 | Complete |
| FNDN-07 | Phase 1 | Complete |
| FNDN-08 | Phase 1 | Complete |
| FNDN-09 | Phase 1 | Complete |
| FNDN-10 | Phase 1 | Complete |
| TEST-01 | Phase 1 | Complete |
| TSML-01 | Phase 2 | Complete |
| TSML-02 | Phase 2 | Complete |
| TSML-03 | Phase 2 | Complete |
| TSML-04 | Phase 2 | Complete |
| TSML-05 | Phase 2 | Complete |
| TSML-06 | Phase 2 | Complete |
| TSML-07 | Phase 2 | Complete |
| TSML-08 | Phase 2 | Complete |
| TEST-04 | Phase 2 | Complete |
| TEST-05 | Phase 2 | Complete |
| LNAV-01 | Phase 3 | Complete |
| LNAV-02 | Phase 3 | Complete |
| LNAV-03 | Phase 3 | Complete |
| LNAV-04 | Phase 3 | Complete |
| LNAV-05 | Phase 3 | Complete |
| LNAV-06 | Phase 3 | Complete |
| LNAV-07 | Phase 3 | Complete |
| AUTH-01 | Phase 3 | Complete |
| AUTH-02 | Phase 3 | Complete |
| AUTH-03 | Phase 3 | Complete |
| AUTH-04 | Phase 3 | Complete |
| TFBK-01 | Phase 3 | Complete |
| TFBK-02 | Phase 3 | Complete |
| TFBK-03 | Phase 3 | Complete |
| ICON-01 | Phase 3 | Complete |
| ICON-02 | Phase 3 | Complete |
| ICON-03 | Phase 3 | Complete |
| ICON-04 | Phase 3 | Complete |
| TEST-02 | Phase 3 (ongoing through Phase 8) | Complete |
| SPGE-01 | Phase 4 | Complete |
| SPGE-02 | Phase 4 | Complete |
| SPGE-03 | Phase 4 | Complete |
| SPGE-04 | Phase 4 | Complete |
| SPGE-05 | Phase 4 | Complete |
| GDEV-01 | Phase 5 | Complete |
| GDEV-02 | Phase 5 | Complete |
| GDEV-03 | Phase 5 | Complete |
| GDEV-04 | Phase 5 | Complete |
| GDEV-05 | Phase 5 | Complete |
| GDEV-06 | Phase 5 | Complete |
| GDEV-07 | Phase 5 | Complete |
| TEST-03 | Phase 5 (ongoing through Phase 7) | Complete |
| DTBL-01 | Phase 6 | Complete |
| DTBL-02 | Phase 6 | Complete |
| DTBL-03 | Phase 6 | Complete |
| DTBL-04 | Phase 6 | Complete |
| DTBL-05 | Phase 6 | Complete |
| DTBL-06 | Phase 6 | Complete |
| DTBL-07 | Phase 6 | Complete |
| DTBL-08 | Phase 6 | Complete |
| DTBL-09 | Phase 6 | Complete |
| ADMN-01 | Phase 7 | Complete |
| ADMN-02 | Phase 7 | Complete |
| ADMN-03 | Phase 7 | Complete |
| ADMN-04 | Phase 7 | Complete |
| ADMN-05 | Phase 7 | Complete |
| ADMN-06 | Phase 7 | Complete |
| ADMN-07 | Phase 7 | Complete |
| ADMN-08 | Phase 7 | Complete |
| ADMN-09 | Phase 7 | Complete |
| ADMN-10 | Phase 7 | Complete |
| ADMN-11 | Phase 7 | Complete |
| ADMN-12 | Phase 7 | Complete |
| ADMN-13 | Phase 7 | Complete |
| NTVZ-01 | Phase 8 | Complete |
| NTVZ-02 | Phase 8 | Complete |
| NTVZ-03 | Phase 8 | Complete |
| NTVZ-04 | Phase 8 | Complete |
| NTVZ-05 | Phase 8 | Complete |
| NTVZ-06 | Phase 8 | Complete |
| CLNP-01 | Phase 9 | Complete |
| CLNP-02 | Phase 9 | Complete |
| CLNP-03 | Phase 9 | Complete |
| CLNP-04 | Phase 9 | Complete |
| CLNP-05 | Phase 9 | Complete |
| CLNP-06 | Phase 9 | Complete |
| CLNP-07 | Phase 9 | Complete |
| CLNP-08 | Phase 9 | Complete |
| TEST-06 | Phase 9 | Complete |

**Coverage:**
- v1 requirements: 90 total
- Mapped to phases: 90
- Unmapped: 0

**Note on spanning requirements:** TEST-02 (UI component tests) and TEST-03 (domain component tests) are written continuously as components are migrated. Primary phase assignment reflects where each begins; tests are written and committed within each migration phase.

---
*Requirements defined: 2026-02-28*
*Last updated: 2026-03-03 — All 90 requirements marked Complete (v0.2.0 migration finished)*
