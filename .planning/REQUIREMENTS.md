# Requirements: Kidney-Genetics Database v0.2.0

**Defined:** 2026-02-28
**Core Value:** Researchers and clinicians can quickly find, explore, and evaluate kidney disease gene evidence

## v1 Requirements

Requirements for milestone v0.2.0 — Frontend Migration. Each maps to roadmap phases.

### Foundation (FNDN)

- [ ] **FNDN-01**: TypeScript strict mode enabled across the entire frontend codebase
- [ ] **FNDN-02**: tsconfig.json configured with strict: true, allowJs: true, path aliases (@/)
- [ ] **FNDN-03**: Type definitions created for all domain interfaces (gene, auth, API responses, pipeline)
- [ ] **FNDN-04**: Tailwind CSS v4 installed with @tailwindcss/vite plugin (no PostCSS)
- [ ] **FNDN-05**: Tailwind v4 coexists with Vuetify without visual regressions (CSS @layer strategy, preflight disabled)
- [ ] **FNDN-06**: shadcn-vue initialized with Reka UI primitives and components.json configured
- [ ] **FNDN-07**: cn() utility function available at src/lib/utils.ts (clsx + tailwind-merge v3)
- [ ] **FNDN-08**: Theme CSS variables mapped from Vuetify to shadcn-vue convention (--primary, --background, etc.) with light/dark mode
- [ ] **FNDN-09**: Vitest installed and configured for component testing
- [ ] **FNDN-10**: Complete MDI icon audit documenting all 193 unique icons and their Lucide equivalents (or custom solutions for ~30-40 gaps)

### TypeScript Migration (TSML)

- [ ] **TSML-01**: main.js migrated to main.ts with typed app creation and plugin registration
- [ ] **TSML-02**: Both Pinia stores (auth, logStore) migrated to TypeScript with typed state, getters, and actions
- [ ] **TSML-03**: All 12 API modules migrated to TypeScript with typed request/response interfaces
- [ ] **TSML-04**: All 6 composables migrated to TypeScript with typed return values
- [ ] **TSML-05**: All 11 utility files migrated to TypeScript
- [ ] **TSML-06**: Router migrated to TypeScript with typed route meta fields and navigation guards
- [ ] **TSML-07**: WebSocket and logging services migrated to TypeScript
- [ ] **TSML-08**: vue-tsc type checking passes with zero errors

### Layout & Navigation (LNAV)

- [ ] **LNAV-01**: App shell replaced (v-app/v-main → Tailwind layout with min-h-screen)
- [ ] **LNAV-02**: Header/app bar replaced with shadcn-vue NavigationMenu (responsive)
- [ ] **LNAV-03**: Mobile navigation drawer replaced with shadcn-vue Sheet
- [ ] **LNAV-04**: Footer replaced with Tailwind-styled custom footer
- [ ] **LNAV-05**: User menu replaced with shadcn-vue DropdownMenu + Avatar
- [ ] **LNAV-06**: Breadcrumbs replaced with shadcn-vue Breadcrumb component
- [ ] **LNAV-07**: Theme toggle replaced with VueUse useColorMode() + ModeToggle component

### Authentication UI (AUTH)

- [ ] **AUTH-01**: LoginModal migrated to shadcn-vue Dialog + Form (vee-validate + Zod schema)
- [ ] **AUTH-02**: ForgotPasswordModal migrated to shadcn-vue Dialog + Form
- [ ] **AUTH-03**: ChangePasswordModal migrated to shadcn-vue Dialog + Form
- [ ] **AUTH-04**: Login/ForgotPassword views migrated with shadcn-vue components

### Toast & Feedback (TFBK)

- [ ] **TFBK-01**: vue-sonner installed and configured as toast provider
- [ ] **TFBK-02**: All v-snackbar usages replaced with toast() from vue-sonner
- [ ] **TFBK-03**: Loading/success/error sequences use toast.promise() pattern

### Icons (ICON)

- [ ] **ICON-01**: Lucide Vue Next installed and configured
- [ ] **ICON-02**: Icon mapping module created (src/utils/icons.ts) mapping MDI names to Lucide components
- [ ] **ICON-03**: All 431 v-icon usages replaced with Lucide components
- [ ] **ICON-04**: Custom icon solutions for medical/scientific icons without Lucide equivalents

### Simple Pages (SPGE)

- [ ] **SPGE-01**: Home.vue migrated (hero, feature cards, CTA with Tailwind + shadcn-vue)
- [ ] **SPGE-02**: About.vue migrated (static content with Tailwind layout)
- [ ] **SPGE-03**: DataSources.vue migrated (data source display)
- [ ] **SPGE-04**: Profile.vue migrated (user profile page)
- [ ] **SPGE-05**: Dashboard.vue migrated (statistics cards, overview metrics)

### Gene Detail & Evidence (GDEV)

- [ ] **GDEV-01**: GeneDetail.vue migrated with shadcn-vue Tabs replacing v-tabs
- [ ] **GDEV-02**: All 8 gene info components migrated (BasicInfo, Constraints, Expression, ClinVar, Phenotypes, MousePhenotypes, ProteinInteractions, InformationCard)
- [ ] **GDEV-03**: All 8 evidence components migrated (EvidenceCard, ClinGen, GenCC, HPO, PanelApp, DiagnosticPanels, Literature, PubTator)
- [ ] **GDEV-04**: EvidenceTierBadge migrated to shadcn-vue Badge with correct tier colors
- [ ] **GDEV-05**: ScoreBreakdown migrated to shadcn-vue Card
- [ ] **GDEV-06**: TierHelpDialog migrated to shadcn-vue Dialog
- [ ] **GDEV-07**: Expansion panels replaced with shadcn-vue Accordion

### Data Tables (DTBL)

- [ ] **DTBL-01**: Reusable DataTable infrastructure created (DataTable, ColumnHeader, Pagination, ViewOptions, FacetedFilter)
- [ ] **DTBL-02**: GeneTable migrated to TanStack Table with server-side pagination (manualPagination, 0-based pageIndex handling)
- [ ] **DTBL-03**: GeneTable server-side sorting works correctly
- [ ] **DTBL-04**: GeneTable column-level filtering works (including multi-select with chips for sources/tiers)
- [ ] **DTBL-05**: GeneTable row click navigation to gene detail preserved
- [ ] **DTBL-06**: GeneTable custom cell renderers (score badges, evidence tiers) working
- [ ] **DTBL-07**: Genes.vue search/filter controls migrated
- [ ] **DTBL-08**: EnrichmentTable (network analysis) migrated to TanStack Table
- [ ] **DTBL-09**: Pagination auto-resets on filter/sort changes (explicit watch implementation)

### Admin Panel (ADMN)

- [ ] **ADMN-01**: Admin layout migrated (AdminHeader, AdminStatsCard, sidebar navigation)
- [ ] **ADMN-02**: AdminDashboard.vue migrated (stats cards, overview)
- [ ] **ADMN-03**: AdminPipeline.vue migrated (pipeline controls, Progress component, WebSocket integration preserved)
- [ ] **ADMN-04**: AdminUserManagement migrated with TanStack Table + forms
- [ ] **ADMN-05**: AdminGeneStaging migrated with TanStack Table
- [ ] **ADMN-06**: AdminAnnotations migrated with TanStack Table
- [ ] **ADMN-07**: AdminCacheManagement migrated with TanStack Table
- [ ] **ADMN-08**: AdminLogViewer migrated with TanStack Table
- [ ] **ADMN-09**: AdminReleases migrated with TanStack Table
- [ ] **ADMN-10**: AdminBackups migrated (5 dialogs: Create, Delete, Details, Filters, Restore)
- [ ] **ADMN-11**: AdminSettings migrated (SettingEditDialog, SettingHistoryDialog)
- [ ] **ADMN-12**: AdminHybridSources migrated with TanStack Table
- [ ] **ADMN-13**: All admin forms use vee-validate + Zod schemas

### Network & Visualizations (NTVZ)

- [ ] **NTVZ-01**: NetworkAnalysis.vue layout migrated to Tailwind (Cytoscape integration preserved)
- [ ] **NTVZ-02**: NetworkGraph.vue wrapper migrated (Cytoscape internals unchanged)
- [ ] **NTVZ-03**: NetworkSearchOverlay migrated (Input + Card replacing v-text-field/v-card)
- [ ] **NTVZ-04**: ClusterDetailsDialog migrated to shadcn-vue Dialog
- [ ] **NTVZ-05**: All D3 chart Vue wrappers migrated (layout/styling only; D3 rendering unchanged)
- [ ] **NTVZ-06**: GeneStructure.vue view migrated

### Cleanup & Removal (CLNP)

- [ ] **CLNP-01**: Zero v- component tags remain in codebase
- [ ] **CLNP-02**: Zero Vuetify utility classes remain in codebase
- [ ] **CLNP-03**: Zero --v-theme-* CSS variable references remain in scoped styles
- [ ] **CLNP-04**: vuetify and @mdi/font removed from package.json
- [ ] **CLNP-05**: src/plugins/vuetify.js deleted and Vuetify plugin registration removed from main.ts
- [ ] **CLNP-06**: Tailwind CSS coexistence hacks removed (selective imports replaced with full @import "tailwindcss")
- [ ] **CLNP-07**: npm run build succeeds with zero Vuetify references
- [ ] **CLNP-08**: Bundle size measured and reduced compared to pre-migration baseline

### Testing (TEST)

- [ ] **TEST-01**: Vitest configured with Vue Test Utils and happy-dom/jsdom
- [ ] **TEST-02**: Component tests written for all migrated shadcn-vue UI wrapper components
- [ ] **TEST-03**: Component tests written for key domain components (GeneTable, EvidenceCard, LoginModal)
- [ ] **TEST-04**: Composable tests written for all 6 migrated composables
- [ ] **TEST-05**: API module tests written for typed API client and interceptors
- [ ] **TEST-06**: All Vitest tests pass in CI pipeline

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
| FNDN-01 | Phase 1 | Pending |
| FNDN-02 | Phase 1 | Pending |
| FNDN-03 | Phase 1 | Pending |
| FNDN-04 | Phase 1 | Pending |
| FNDN-05 | Phase 1 | Pending |
| FNDN-06 | Phase 1 | Pending |
| FNDN-07 | Phase 1 | Pending |
| FNDN-08 | Phase 1 | Pending |
| FNDN-09 | Phase 1 | Pending |
| FNDN-10 | Phase 1 | Pending |
| TEST-01 | Phase 1 | Pending |
| TSML-01 | Phase 2 | Pending |
| TSML-02 | Phase 2 | Pending |
| TSML-03 | Phase 2 | Pending |
| TSML-04 | Phase 2 | Pending |
| TSML-05 | Phase 2 | Pending |
| TSML-06 | Phase 2 | Pending |
| TSML-07 | Phase 2 | Pending |
| TSML-08 | Phase 2 | Pending |
| TEST-04 | Phase 2 | Pending |
| TEST-05 | Phase 2 | Pending |
| LNAV-01 | Phase 3 | Pending |
| LNAV-02 | Phase 3 | Pending |
| LNAV-03 | Phase 3 | Pending |
| LNAV-04 | Phase 3 | Pending |
| LNAV-05 | Phase 3 | Pending |
| LNAV-06 | Phase 3 | Pending |
| LNAV-07 | Phase 3 | Pending |
| AUTH-01 | Phase 3 | Pending |
| AUTH-02 | Phase 3 | Pending |
| AUTH-03 | Phase 3 | Pending |
| AUTH-04 | Phase 3 | Pending |
| TFBK-01 | Phase 3 | Pending |
| TFBK-02 | Phase 3 | Pending |
| TFBK-03 | Phase 3 | Pending |
| ICON-01 | Phase 3 | Pending |
| ICON-02 | Phase 3 | Pending |
| ICON-03 | Phase 3 | Pending |
| ICON-04 | Phase 3 | Pending |
| TEST-02 | Phase 3 (ongoing through Phase 8) | Pending |
| SPGE-01 | Phase 4 | Pending |
| SPGE-02 | Phase 4 | Pending |
| SPGE-03 | Phase 4 | Pending |
| SPGE-04 | Phase 4 | Pending |
| SPGE-05 | Phase 4 | Pending |
| GDEV-01 | Phase 5 | Pending |
| GDEV-02 | Phase 5 | Pending |
| GDEV-03 | Phase 5 | Pending |
| GDEV-04 | Phase 5 | Pending |
| GDEV-05 | Phase 5 | Pending |
| GDEV-06 | Phase 5 | Pending |
| GDEV-07 | Phase 5 | Pending |
| TEST-03 | Phase 5 (ongoing through Phase 7) | Pending |
| DTBL-01 | Phase 6 | Pending |
| DTBL-02 | Phase 6 | Pending |
| DTBL-03 | Phase 6 | Pending |
| DTBL-04 | Phase 6 | Pending |
| DTBL-05 | Phase 6 | Pending |
| DTBL-06 | Phase 6 | Pending |
| DTBL-07 | Phase 6 | Pending |
| DTBL-08 | Phase 6 | Pending |
| DTBL-09 | Phase 6 | Pending |
| ADMN-01 | Phase 7 | Pending |
| ADMN-02 | Phase 7 | Pending |
| ADMN-03 | Phase 7 | Pending |
| ADMN-04 | Phase 7 | Pending |
| ADMN-05 | Phase 7 | Pending |
| ADMN-06 | Phase 7 | Pending |
| ADMN-07 | Phase 7 | Pending |
| ADMN-08 | Phase 7 | Pending |
| ADMN-09 | Phase 7 | Pending |
| ADMN-10 | Phase 7 | Pending |
| ADMN-11 | Phase 7 | Pending |
| ADMN-12 | Phase 7 | Pending |
| ADMN-13 | Phase 7 | Pending |
| NTVZ-01 | Phase 8 | Pending |
| NTVZ-02 | Phase 8 | Pending |
| NTVZ-03 | Phase 8 | Pending |
| NTVZ-04 | Phase 8 | Pending |
| NTVZ-05 | Phase 8 | Pending |
| NTVZ-06 | Phase 8 | Pending |
| CLNP-01 | Phase 9 | Pending |
| CLNP-02 | Phase 9 | Pending |
| CLNP-03 | Phase 9 | Pending |
| CLNP-04 | Phase 9 | Pending |
| CLNP-05 | Phase 9 | Pending |
| CLNP-06 | Phase 9 | Pending |
| CLNP-07 | Phase 9 | Pending |
| CLNP-08 | Phase 9 | Pending |
| TEST-06 | Phase 9 | Pending |

**Coverage:**
- v1 requirements: 90 total
- Mapped to phases: 90
- Unmapped: 0

**Note on spanning requirements:** TEST-02 (UI component tests) and TEST-03 (domain component tests) are written continuously as components are migrated. Primary phase assignment reflects where each begins; tests are written and committed within each migration phase.

---
*Requirements defined: 2026-02-28*
*Last updated: 2026-02-28 — Roadmap created, traceability finalized*
