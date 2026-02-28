# Frontend Migration Plan: TypeScript + Tailwind CSS v4 + shadcn-vue

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement each phase plan task-by-task. Each phase has its own detailed plan file in `.planning/phases/<phase-dir>/`.

**Goal:** Migrate the frontend from JavaScript + Vuetify 3 to TypeScript + Tailwind CSS v4 + shadcn-vue, covering ~65 remaining Vue files (~24,000 lines) across 6 execution phases.

**Architecture:** Incremental phase-by-phase migration where Vuetify and shadcn-vue coexist. Each phase produces a shippable, working state. Detailed per-phase plans live in `.planning/phases/<NN-name>/NN-XX-PLAN.md` and are executed with the executing-plans skill.

**Tech Stack:** Vue 3, TypeScript, Tailwind CSS v4, shadcn-vue (new-york style, reka-ui primitives), TanStack Table v8, vee-validate + Zod, vue-sonner, Lucide icons, D3.js (kept), Cytoscape.js (kept)

---

## Progress Tracker

| Phase | Name | Files | Lines | Status |
|-------|------|-------|-------|--------|
| 01 | Foundation Setup | ~10 | — | DONE |
| 02 | TypeScript Migration | ~40 | — | DONE |
| 03 | App Shell, Nav, Auth, Icons | ~75 | — | DONE |
| 04 | Public Pages + Footer | 7 | ~2,110 | DONE |
| 05 | Gene Detail & Evidence | 20 | ~3,650 | PLANNED (3 plans) |
| 06 | Data Tables | 4+infra | ~1,400 | PLANNED (2 plans) |
| 07 | Admin Panel | 22 | ~8,740 | PLANNED (4 plans) |
| 08 | Network & Visualizations | 11 | ~6,165 | PLANNED (3 plans) |
| 09 | Cleanup & Vuetify Removal | ~8 | — | PLANNED (1 plan) |

**Critical path:** 03 → 04 → 05 + 06 (parallel) → 07 (needs 06) → 08 → 09

---

## Phase 03: App Shell, Nav, Auth, Icons (DONE)

**Plans:** `.planning/phases/03-app-shell-nav-auth-icons/`

| Plan | Title | Status |
|------|-------|--------|
| 03-01 | App shell layout migration | DONE |
| 03-02 | UserMenu + AdminHeader to shadcn-vue | DONE |
| 03-03 | Auth modals + auth pages to shadcn-vue | DONE |
| 03-04 | Toast replacement — all v-snackbar to vue-sonner | DONE |
| 03-05 | Icon replacement — all v-icon to Lucide | DONE |

---

## Phase 04: Public Pages + Footer (DONE)

**Goal:** Migrate 7 simple public-facing pages and the footer from Vuetify layout/cards to Tailwind + shadcn-vue.

**Plans directory:** `.planning/phases/04-public-pages-footer/`

**shadcn-vue components to install:**
```bash
npx shadcn-vue@latest add tabs alert switch accordion scroll-area
```

### Files

| File | Lines | Key Vuetify | New shadcn-vue | Complexity |
|------|-------|-------------|----------------|------------|
| `src/components/AppFooter.vue` | 209 | v-footer, v-menu, v-list, v-icon | DropdownMenu, custom footer | Medium |
| `src/views/Home.vue` | 267 | v-container, v-row, v-col, v-card, v-icon, useDisplay | Card, Tailwind grid | Low |
| `src/views/About.vue` | 485 | v-container, v-card, v-chip, v-avatar, v-icon | Card, Badge, Accordion | Low-Medium |
| `src/views/Dashboard.vue` | 202 | v-container, v-tabs, v-select | Tabs, Select (custom) | Low-Medium |
| `src/views/DataSources.vue` | 463 | v-container, v-card, v-chip, v-tooltip, v-progress-circular | Card, Badge, Tooltip, Progress | Medium |
| `src/views/Profile.vue` | 455 | v-card, v-list, v-chip, v-avatar, v-divider | Card, Avatar, Separator, Badge | Medium |
| `src/views/Genes.vue` | 34 | v-container, v-breadcrumbs | Tailwind container, Breadcrumb | Trivial |

### Tasks (6 tasks, ~2-3 plans)

**Task 1: AppFooter.vue**
- Replace `v-footer` with semantic `<footer>` + Tailwind classes
- Replace `v-menu` with DropdownMenu (version info popover)
- Replace `v-list`/`v-list-item` with Tailwind-styled list
- Replace `v-icon` with Lucide icons (should already be done by 03-05)
- Replace `v-container`/`v-row`/`v-col` with Tailwind flex/grid

**Task 2: Home.vue**
- Replace `v-container`/`v-row`/`v-col` with Tailwind responsive grid
- Replace `v-card` with Card components or Tailwind-styled divs
- Replace `useDisplay()` with VueUse `useBreakpoints()` or Tailwind responsive classes
- Remove `import { useDisplay } from 'vuetify'`
- Keep gradient backgrounds (convert to Tailwind gradient utilities)

**Task 3: About.vue**
- Replace layout with Tailwind grid
- Replace `v-card` sections with Card
- Replace `v-chip` with Badge
- Replace accordion/expansion sections with Accordion
- Replace `v-avatar` with Avatar

**Task 4: Dashboard.vue**
- Replace `v-tabs` with Tabs
- Replace `v-select` with custom Select or native select
- Keep visualization component embeds unchanged (migrated in Phase 08)

**Task 5: DataSources.vue + Genes.vue**
- DataSources: Replace card grid, progress indicators, tooltips
- Genes: Trivial — just replace container/breadcrumbs (GeneTable migrated in Phase 06)

**Task 6: Profile.vue**
- Replace profile card layout
- Replace `v-list` with Tailwind-styled list
- Wire ChangePasswordModal (already migrated in 03-03)

### Verification
- `npm run build` succeeds
- `npm run lint` has 0 errors
- All 7 pages render correctly in browser
- Responsive layout works (mobile + desktop)
- No `v-container`, `v-row`, `v-col`, `v-footer` tags in migrated files

---

## Phase 05: Gene Detail & Evidence Components

**Goal:** Migrate the gene detail page, gene info sub-components, evidence display components, and shared scoring components.

**Plans directory:** `.planning/phases/05-gene-detail-evidence/`

**shadcn-vue components to install (if not already):**
```bash
npx shadcn-vue@latest add accordion progress
```

### Files

| File | Lines | Key Vuetify | Complexity |
|------|-------|-------------|------------|
| **Gene Detail Page** | | | |
| `src/views/GeneDetail.vue` | 352 | v-container, v-breadcrumbs, v-btn, v-menu, v-tabs | Medium-High |
| `src/views/GeneStructure.vue` | 422 | v-container, v-card, v-progress-circular, v-alert | Medium |
| **Gene Info Components** | | | |
| `src/components/gene/GeneInformationCard.vue` | 198 | v-card, v-avatar, v-icon, v-divider, v-progress-circular | Medium |
| `src/components/gene/GeneBasicInfo.vue` | 49 | v-tooltip, Vuetify utility classes | Low |
| `src/components/gene/GeneConstraints.vue` | 117 | v-tooltip, v-chip, v-icon | Low |
| `src/components/gene/GeneExpression.vue` | 204 | v-tooltip, v-chip, v-icon | Low-Medium |
| `src/components/gene/GenePhenotypes.vue` | 178 | v-chip, v-tooltip, v-icon | Low-Medium |
| `src/components/gene/MousePhenotypes.vue` | 133 | v-chip, v-tooltip, v-icon | Low |
| `src/components/gene/ClinVarVariants.vue` | 204 | v-chip, v-tooltip, v-icon | Low-Medium |
| `src/components/gene/ProteinInteractions.vue` | 146 | v-chip, v-tooltip, v-icon | Low |
| **Evidence Components** | | | |
| `src/components/evidence/EvidenceCard.vue` | 255 | v-expansion-panel, v-avatar, v-chip, v-icon | Medium |
| `src/components/evidence/ClinGenEvidence.vue` | 270 | v-chip, v-tooltip, v-icon | Low-Medium |
| `src/components/evidence/GenCCEvidence.vue` | 241 | v-chip, v-tooltip, v-icon | Low-Medium |
| `src/components/evidence/HPOEvidence.vue` | 168 | v-chip, v-tooltip, v-icon | Low |
| `src/components/evidence/PubTatorEvidence.vue` | 195 | v-chip, v-tooltip, v-icon | Low |
| `src/components/evidence/PanelAppEvidence.vue` | 290 | v-chip, v-tooltip, v-icon | Low-Medium |
| `src/components/evidence/DiagnosticPanelsEvidence.vue` | 200 | v-chip, v-tooltip, v-icon | Low |
| `src/components/evidence/LiteratureEvidence.vue` | 316 | v-chip, v-tooltip, v-icon | Low-Medium |
| **Shared Components** | | | |
| `src/components/EvidenceTierBadge.vue` | 59 | v-tooltip, v-chip, v-icon | Low |
| `src/components/ScoreBreakdown.vue` | 317 | v-tooltip, v-chip, v-card, v-progress-circular | Medium |
| `src/components/TierHelpDialog.vue` | 107 | v-dialog, v-card, v-chip, v-alert | Low-Medium |

### Tasks (7 tasks, ~3-4 plans)

**Task 1: Shared components (EvidenceTierBadge, TierHelpDialog, ScoreBreakdown)**
- EvidenceTierBadge: Replace `v-tooltip` + `v-chip` with Tooltip + Badge
- TierHelpDialog: Replace `v-dialog` + `v-card` with Dialog + Card
- ScoreBreakdown: Replace card/chip/progress with Card + Badge + Progress

**Task 2: Gene info components (8 files)**
- All follow same pattern: replace `v-chip` → Badge, `v-tooltip` → Tooltip, `v-icon` → Lucide
- GeneInformationCard: Replace `v-card` → Card, `v-avatar` → Avatar, `v-progress-circular` → spinner
- Replace all Vuetify utility classes (`d-flex`, `align-center`, `ga-`) with Tailwind equivalents

**Task 3: EvidenceCard.vue**
- Replace `v-expansion-panel` with Accordion (AccordionItem, AccordionTrigger, AccordionContent)
- Replace `v-avatar` → Avatar, `v-chip` → Badge
- Keep source-specific slot content structure

**Task 4: Evidence source components (8 files)**
- All follow same pattern: data display with chips and tooltips
- Replace `v-chip` → Badge, `v-tooltip` → Tooltip
- Replace Vuetify utility classes with Tailwind

**Task 5: GeneDetail.vue**
- Replace `v-container`/`v-breadcrumbs` with Tailwind + Breadcrumb
- Replace `v-tabs` with Tabs (TabsList, TabsTrigger, TabsContent)
- Replace `v-menu` with DropdownMenu (gene actions)
- Keep all child component imports unchanged

**Task 6: GeneStructure.vue**
- Replace `v-container`/`v-card` with Tailwind + Card
- Replace `v-progress-circular` with spinner
- Replace `v-alert` with Alert
- Keep visualization embed unchanged (migrated in Phase 08)

**Task 7: Verification**
- Build + lint pass
- Gene detail page fully functional with all tabs
- Evidence accordion expands/collapses correctly
- Tier badges show correct colors
- Score breakdown displays correctly

---

## Phase 06: Data Tables

**Goal:** Create reusable TanStack Table infrastructure and migrate the main GeneTable (server-side) and EnrichmentTable.

**Plans directory:** `.planning/phases/06-data-tables/`

**This is the HIGHEST COMPLEXITY phase.** The GeneTable is 892 lines with server-side pagination, multi-dimensional filtering, URL parameter sync, and custom cell renderers.

**shadcn-vue components to install:**
```bash
npx shadcn-vue@latest add table select slider pagination checkbox command
```

**npm packages to verify:**
```bash
# @tanstack/vue-table should already be installed from Phase 01
npm ls @tanstack/vue-table
```

### Files

| File | Lines | Table Type | Complexity |
|------|-------|-----------|------------|
| **Infrastructure (create)** | | | |
| `src/components/ui/data-table/DataTable.vue` | — | Wrapper | Medium |
| `src/components/ui/data-table/DataTableColumnHeader.vue` | — | Sortable header | Low |
| `src/components/ui/data-table/DataTablePagination.vue` | — | Pagination | Medium |
| `src/components/ui/data-table/DataTableViewOptions.vue` | — | Column toggle | Low |
| `src/components/ui/data-table/DataTableFacetedFilter.vue` | — | Faceted filter | Medium |
| **Application tables** | | | |
| `src/components/GeneTable.vue` | 892 | Server-side | **VERY HIGH** |
| `src/views/Genes.vue` | 34 | Wrapper | Trivial |
| `src/components/network/EnrichmentTable.vue` | 440 | Client-side | High |

### Tasks (6 tasks, ~3 plans)

**Task 1: Create DataTable infrastructure**
- Create base `DataTable.vue` wrapper around `@tanstack/vue-table`
- Create `DataTableColumnHeader.vue` with sort indicators
- Create `DataTablePagination.vue` with page size selector
- Create `DataTableViewOptions.vue` for column visibility
- All components use shadcn-vue Table primitives

**Task 2: GeneTable.vue — column definitions + basic rendering**
- Define TanStack column definitions for all 7 columns
- Custom cell renderers: gene symbol, HGNC ID, tier badge, evidence count, score, sources
- Replace `v-data-table-server` with DataTable
- Replace `v-card` wrapper with Card

**Task 3: GeneTable.vue — server-side pagination + sorting**
- Wire `manualPagination: true` and `manualSorting: true`
- Implement page/sort state → API parameter mapping
- Replace `v-pagination` with DataTablePagination
- Preserve URL query parameter synchronization

**Task 4: GeneTable.vue — filtering**
- Replace `v-text-field` search with Input
- Replace `v-select` filters with Select or Command
- Replace `v-range-slider` with Slider
- Replace `v-switch` with Switch
- Preserve debounced search behavior
- Preserve filter metadata from API

**Task 5: EnrichmentTable.vue**
- Replace `v-data-table` with DataTable (client-side, no manual pagination)
- Replace `v-select` filters with Select
- Replace `v-text-field` threshold with Input
- Preserve CSV export functionality
- Preserve dynamic columns based on enrichment type

**Task 6: Verification**
- Gene browser loads with server-side data
- Pagination, sorting, all 6 filter dimensions work
- URL parameters sync correctly (bookmarkable state)
- Enrichment table renders with dynamic columns
- CSV export works

### Key Technical Decisions
- **TanStack Table** with `useVueTable` composable
- Server-side: `manualPagination: true`, `manualSorting: true`
- Column definitions as typed `ColumnDef<Gene>[]`
- Cell renderers as Vue components or inline render functions
- URL sync via `useRoute`/`useRouter` (preserve existing pattern)

---

## Phase 07: Admin Panel

**Goal:** Migrate all 11 admin views and 9 admin support components from Vuetify to shadcn-vue. Admin data tables reuse the DataTable infrastructure from Phase 06.

**Plans directory:** `.planning/phases/07-admin-panel/`

**Dependencies:** Phase 06 (data table infrastructure)

### Files (22 files, ~8,740 lines)

| File | Lines | Key Vuetify | Complexity |
|------|-------|-------------|------------|
| **Admin Views** | | | |
| `src/views/admin/AdminDashboard.vue` | 547 | v-card, v-icon, v-divider | Medium |
| `src/views/admin/AdminUserManagement.vue` | 464 | v-data-table, v-dialog, v-chip, v-text-field | Medium |
| `src/views/admin/AdminAnnotations.vue` | 939 | v-data-table, v-dialog, v-select, v-switch, v-chip-group | High |
| `src/views/admin/AdminCacheManagement.vue` | 512 | v-data-table, v-dialog, v-chip | Medium |
| `src/views/admin/AdminPipeline.vue` | 610 | v-data-table, v-card, v-chip | Medium |
| `src/views/admin/AdminBackups.vue` | 456 | v-card, v-btn | Medium |
| `src/views/admin/AdminReleases.vue` | 726 | v-data-table, v-chip, v-dialog | Medium |
| `src/views/admin/AdminGeneStaging.vue` | 824 | v-data-table, v-dialog, v-autocomplete | Medium-High |
| `src/views/admin/AdminLogViewer.vue` | 1,144 | v-data-table (server-side), v-select, v-text-field | High |
| `src/views/admin/AdminSettings.vue` | 317 | v-data-table, v-dialog | Medium |
| `src/views/admin/AdminHybridSources.vue` | 756 | v-data-table, v-chip, v-dialog | Medium-High |
| **Admin Components** | | | |
| `src/components/admin/AdminStatsCard.vue` | 114 | v-card, v-progress-circular, v-icon | Low |
| `src/components/admin/LogViewer.vue` | 430 | v-card, v-data-table, v-chip | Medium |
| `src/components/admin/backups/BackupCreateDialog.vue` | 144 | v-dialog, v-form | Low |
| `src/components/admin/backups/BackupDeleteDialog.vue` | 58 | v-dialog | Low |
| `src/components/admin/backups/BackupDetailsDialog.vue` | 135 | v-dialog, v-card | Low |
| `src/components/admin/backups/BackupFilters.vue` | 144 | v-select, v-text-field | Low |
| `src/components/admin/backups/BackupRestoreDialog.vue` | 115 | v-dialog | Low |
| `src/components/admin/settings/SettingEditDialog.vue` | 100 | v-dialog, v-form | Low |
| `src/components/admin/settings/SettingHistoryDialog.vue` | 106 | v-dialog, v-card | Low |
| **Shared (also used by admin)** | | | |
| `src/components/DataSourceProgress.vue` | 538 | v-card, v-expand-transition, v-list, v-progress-linear | Medium |

### Tasks (8 tasks, ~4-5 plans)

**Task 1: AdminStatsCard + AdminDashboard**
- AdminStatsCard: Replace `v-card` → Card, spinner → Tailwind spinner
- AdminDashboard: Replace card grid with Tailwind, use AdminStatsCard

**Task 2: DataSourceProgress.vue**
- Replace `v-card`/`v-expand-transition` with Card + Collapsible
- Replace `v-list` with Tailwind-styled list
- Replace `v-progress-linear` with Progress

**Task 3: Backup dialogs (5 files) + AdminBackups**
- All dialogs: Replace `v-dialog` → Dialog or AlertDialog
- BackupCreateDialog: vee-validate + Zod form
- BackupDeleteDialog: AlertDialog with confirmation
- BackupFilters: Replace `v-select`/`v-text-field` → Select/Input

**Task 4: Settings dialogs (2 files) + AdminSettings**
- SettingEditDialog: Dialog + Form
- SettingHistoryDialog: Dialog + Card
- AdminSettings: DataTable with edit/history actions

**Task 5: AdminUserManagement + AdminCacheManagement**
- Both use simple client-side DataTable
- Replace `v-dialog` CRUD modals with Dialog
- Replace `v-chip` status indicators with Badge

**Task 6: AdminAnnotations + AdminPipeline**
- AdminAnnotations: Complex — data table + pipeline controls + progress
- AdminPipeline: Data table + WebSocket progress (keep WS integration)
- Replace `v-switch` → Switch, `v-chip-group` → toggle group

**Task 7: AdminGeneStaging + AdminLogViewer + AdminReleases + AdminHybridSources**
- AdminGeneStaging: DataTable + `v-autocomplete` → Command/Combobox
- AdminLogViewer: Server-side DataTable (reuse pattern from GeneTable)
- AdminReleases + AdminHybridSources: Client-side DataTable

**Task 8: Verification**
- All 11 admin views render correctly
- All CRUD operations work (create, edit, delete)
- Pipeline management functional with WebSocket updates
- Log viewer pagination + filtering works
- All backup operations functional

---

## Phase 08: Network & Visualizations

**Goal:** Migrate network analysis page, graph visualization, and all D3 chart wrapper components. The D3/Cytoscape internals are preserved — only the Vue wrapper layer and Vuetify controls are replaced.

**Plans directory:** `.planning/phases/08-network-visualizations/`

### Files (11 files, ~6,165 lines)

| File | Lines | Key Vuetify | Complexity |
|------|-------|-------------|------------|
| **Network** | | | |
| `src/views/NetworkAnalysis.vue` | 1,120 | v-container, v-card, v-select, v-text-field, v-chip | High |
| `src/components/network/NetworkGraph.vue` | 1,619 | v-card, v-select, v-btn, v-chip, v-tooltip | Very High |
| `src/components/network/NetworkSearchOverlay.vue` | 170 | v-text-field, v-card | Low |
| `src/components/network/ClusterDetailsDialog.vue` | 461 | v-dialog, v-card, v-chip | Medium |
| **Visualizations** | | | |
| `src/components/visualizations/GeneStructureVisualization.vue` | 799 | v-chip-group, v-btn-group, useTheme | High |
| `src/components/visualizations/ProteinDomainVisualization.vue` | 773 | v-chip-group, v-btn-group, useTheme | High |
| `src/components/visualizations/D3BarChart.vue` | 364 | useTheme | Medium |
| `src/components/visualizations/D3DonutChart.vue` | 410 | useTheme | Medium |
| `src/components/visualizations/EvidenceCompositionChart.vue` | 270 | Vuetify utility classes | Low-Medium |
| `src/components/visualizations/SourceDistributionsChart.vue` | 302 | Vuetify utility classes | Low-Medium |
| `src/components/visualizations/UpSetChart.vue` | 557 | Vuetify utility classes | Medium |

### Tasks (6 tasks, ~3 plans)

**Task 1: D3 chart wrappers (5 files)**
- Replace `useTheme()` from Vuetify with `useAppTheme()` (after Phase 09 prep)
- For now: read theme from `document.documentElement.classList.contains('dark')`
- Replace Vuetify utility classes with Tailwind
- Keep all D3 rendering logic unchanged

**Task 2: GeneStructureVisualization + ProteinDomainVisualization**
- Replace `v-chip-group` with toggle group (Tailwind buttons or shadcn ToggleGroup)
- Replace `v-btn-group` with Tailwind button group
- Replace `useTheme()` with dark mode detection via VueUse
- Replace Vuetify CSS variables with Tailwind CSS variables
- Keep all D3/SVG rendering unchanged

**Task 3: NetworkSearchOverlay + ClusterDetailsDialog**
- NetworkSearchOverlay: Replace `v-text-field`/`v-card` with Input/Card
- ClusterDetailsDialog: Replace `v-dialog`/`v-card` with Dialog/Card

**Task 4: NetworkGraph.vue**
- Replace `v-card` wrapper with Card
- Replace `v-select` controls with Select
- Replace `v-btn` controls with Button
- Replace `v-chip` indicators with Badge
- Replace `v-tooltip` with Tooltip
- Keep ALL Cytoscape.js logic unchanged
- Keep layout/clustering algorithms unchanged

**Task 5: NetworkAnalysis.vue**
- Replace `v-container`/`v-card` layout with Tailwind + Card
- Replace `v-select`/`v-text-field` filters with Select/Input
- Replace `v-chip` indicators with Badge
- Keep graph component embed and WebSocket integration unchanged

**Task 6: Verification**
- Network graph renders with all layout options
- Node coloring modes work
- Cluster detection works
- Gene search with wildcard works
- All D3 charts render in both light and dark mode
- Gene structure visualization interactive controls work

---

## Phase 09: Cleanup & Vuetify Removal

**Goal:** Remove Vuetify and all related dependencies. Clean up the theme system. Final verification.

**Plans directory:** `.planning/phases/09-cleanup-vuetify-removal/`

**Dependencies:** ALL previous phases complete

### Files

| File | Action |
|------|--------|
| `src/plugins/vuetify.ts` | DELETE |
| `src/composables/useAppTheme.ts` | MODIFY — remove Vuetify sync, keep VueUse `useColorMode` only |
| `src/main.ts` | MODIFY — remove Vuetify plugin import and `app.use(vuetify)` |
| `src/components/branding/KGDBLogo.vue` | MODIFY — replace `useTheme()` with CSS variable / VueUse dark mode |
| `src/components/KidneyGeneticsLogo.vue` | MODIFY — replace `useTheme()` with CSS variable / VueUse dark mode |
| `package.json` | MODIFY — remove `vuetify`, `@mdi/font` |

### Tasks (6 tasks, 1 plan)

**Task 1: Audit for remaining Vuetify**
```bash
grep -r "from 'vuetify'" src/           # Should be 0 (except plugins/vuetify.ts)
grep -r "v-container\|v-row\|v-col\|v-card\|v-btn\|v-icon\|v-chip" src/ --include="*.vue" | grep -v node_modules
grep -r "v-data-table\|v-dialog\|v-menu\|v-tabs\|v-list\|v-alert" src/ --include="*.vue"
grep -r "v-snackbar\|v-form\|v-text-field\|v-select\|v-switch" src/ --include="*.vue"
grep -r "d-flex\|align-center\|justify-space-between\|elevation-\|ma-\|pa-" src/ --include="*.vue"
```
All must return zero results.

**Task 2: Remove Vuetify theme sync from useAppTheme.ts**
- Remove `import { useTheme } from 'vuetify'`
- Remove `vuetifyTheme` const and both `watch()` calls syncing Vuetify
- Keep `useColorMode` and `toggleTheme` — these drive the `.dark` class for shadcn-vue
- Simplified composable: just VueUse `useColorMode` + `isDark` computed + `toggleTheme`

**Task 3: Update branding components**
- KGDBLogo.vue: Replace `useTheme()` with `useAppTheme()` or direct CSS variable access
- KidneyGeneticsLogo.vue: Same treatment
- Ensure logo colors respond to light/dark mode via CSS variables, not Vuetify theme

**Task 4: Remove Vuetify from main.ts**
- Remove `import vuetify from '@/plugins/vuetify'`
- Remove `app.use(vuetify)`
- Delete `src/plugins/vuetify.ts`

**Task 5: Uninstall Vuetify packages**
```bash
npm uninstall vuetify @mdi/font
```

**Task 6: Final verification**
- `npm run build` succeeds with zero Vuetify references
- `npm run lint` passes with 0 errors
- Full manual testing of all pages (public + admin)
- Light/dark mode toggle works everywhere
- Logos render correctly in both modes
- Bundle size comparison (before/after)

---

## Component Mapping Quick Reference

| Vuetify | shadcn-vue / Tailwind | Status |
|---------|----------------------|--------|
| `v-app` | `<div class="min-h-screen bg-background">` | DONE (03-01) |
| `v-app-bar` | Custom header + NavigationMenu | DONE (03-01) |
| `v-navigation-drawer` | Sheet | DONE (03-01) |
| `v-footer` | Custom `<footer>` | DONE (04) |
| `v-container`/`v-row`/`v-col` | Tailwind grid/flex | Phases 04-08 |
| `v-btn` | Button | DONE (03-01) |
| `v-card` + sub | Card + sub | Phases 04-08 |
| `v-dialog` | Dialog / AlertDialog | DONE auth (03-03), others 05-08 |
| `v-text-field` | Input + Label | DONE auth (03-03), others 06-08 |
| `v-select` | Select | Phase 06 |
| `v-autocomplete` | Command / Combobox | Phase 07 |
| `v-chip` | Badge | Phases 04-08 |
| `v-tabs` | Tabs | DONE (04 Dashboard), 05 (GeneDetail) |
| `v-alert` | Alert | DONE (04) |
| `v-snackbar` | vue-sonner toast | Phase 03-04 |
| `v-form` | Form (vee-validate+Zod) | DONE auth (03-03), others 07 |
| `v-expansion-panel` | Accordion | Phase 05 |
| `v-tooltip` | Tooltip | Phases 05-08 |
| `v-menu` | DropdownMenu | DONE (03-02), others 04-05 |
| `v-list`/`v-list-item` | Tailwind styled list | Phases 04-07 |
| `v-pagination` | Pagination | Phase 06 |
| `v-progress-linear` | Progress | Phase 07 |
| `v-progress-circular` | Tailwind spinner | Phases 04-07 |
| `v-divider` | Separator | Phases 04-08 |
| `v-switch` | Switch | Phase 07 |
| `v-data-table` | DataTable (TanStack) | Phase 06-07 |
| `v-icon` (mdi-*) | Lucide icons | Phase 03-05 |
| `v-breadcrumbs` | Breadcrumb | DONE (03-02) |
| `v-avatar` | Avatar | DONE (03-02), others 04-05 |
| `v-spacer` | Tailwind `flex-1` / `grow` | Phases 04-08 |

---

## shadcn-vue Components: Install Schedule

| Component | Install Phase | Used By |
|-----------|--------------|---------|
| button, input, label, card | DONE (01) | Everywhere |
| dialog, form, avatar, badge | DONE (01) | Auth, evidence, admin |
| breadcrumb, dropdown-menu | DONE (01) | Nav, gene actions |
| navigation-menu, sheet, separator | DONE (01) | App shell |
| sonner, tooltip, popover | DONE (01) | Toast, evidence |
| **tabs** | DONE (04) | Dashboard, GeneDetail |
| **alert** | DONE (04) | Error states |
| **accordion** | DONE (04) | About, EvidenceCard |
| **scroll-area** | DONE (04) | Long lists |
| **switch** | DONE (04) | Profile, admin |
| **table** | 06 | All data tables |
| **select** | 06 | Filters, admin forms |
| **slider** | 06 | GeneTable range filters |
| **pagination** | 06 | Data table pagination |
| **checkbox** | 06 | Table row selection |
| **command** | 07 | Admin gene staging |
| **progress** | 05-07 | Score, pipeline |
| **toggle-group** | 08 | Visualization controls |
| **collapsible** | 07 | DataSourceProgress |

---

## Vuetify Utility → Tailwind Cheat Sheet

| Vuetify | Tailwind |
|---------|----------|
| `d-flex` | `flex` |
| `d-none` | `hidden` |
| `d-inline-flex` | `inline-flex` |
| `flex-grow-1` | `grow` / `flex-1` |
| `flex-wrap` | `flex-wrap` |
| `justify-center` | `justify-center` |
| `justify-space-between` | `justify-between` |
| `align-center` | `items-center` |
| `align-start` | `items-start` |
| `align-stretch` | `items-stretch` |
| `ga-1`..`ga-6` | `gap-1`..`gap-6` |
| `ma-N` / `pa-N` | `m-N` / `p-N` |
| `mt-N`, `mb-N`, `ml-N`, `mr-N` | `mt-N`, `mb-N`, `ml-N`, `mr-N` |
| `text-h3`..`text-h6` | `text-3xl font-bold`..`text-lg font-semibold` |
| `text-subtitle-1` | `text-base text-muted-foreground` |
| `text-body-1` / `text-body-2` | `text-base` / `text-sm` |
| `text-caption` | `text-xs` |
| `text-medium-emphasis` | `text-muted-foreground` |
| `font-weight-bold` | `font-bold` |
| `font-weight-medium` | `font-medium` |
| `elevation-0`..`elevation-4` | `shadow-none`..`shadow-lg` |
| `rounded` | `rounded` |
| `fill-height` | `h-full` |
| `w-100` | `w-full` |
| `v-spacer` | `flex-1` or `grow` |

---

## Files Importing `from 'vuetify'` (must all be removed by Phase 09)

1. `src/plugins/vuetify.ts` — DELETE in Phase 09
2. `src/composables/useAppTheme.ts` — MODIFY in Phase 09
3. ~~`src/views/Home.vue`~~ — DONE in Phase 04 (useDisplay removed)
4. `src/components/branding/KGDBLogo.vue` — MODIFY in Phase 09
5. `src/components/KidneyGeneticsLogo.vue` — MODIFY in Phase 09
6. `src/components/visualizations/D3BarChart.vue` — MODIFY in Phase 08
7. `src/components/visualizations/D3DonutChart.vue` — MODIFY in Phase 08
8. `src/components/visualizations/GeneStructureVisualization.vue` — MODIFY in Phase 08
9. `src/components/visualizations/ProteinDomainVisualization.vue` — MODIFY in Phase 08

---

## Research Sources

- [shadcn-vue](https://www.shadcn-vue.com/docs) — Component library
- [TanStack Table v8 (Vue)](https://tanstack.com/table/v8/docs/framework/vue) — Data table engine
- [Radix Vue / reka-ui](https://www.reka-ui.com/) — Headless UI primitives
- [vee-validate](https://vee-validate.logaretm.com/v4/) — Form validation
- [Zod](https://zod.dev/) — Schema validation
- [Lucide Icons](https://lucide.dev/guide/packages/lucide-vue-next) — Icon library
- [vue-sonner](https://vue-sonner.vercel.app/) — Toast notifications
- [VueUse](https://vueuse.org/) — Vue composition utilities
- [Tailwind CSS v4](https://tailwindcss.com/docs) — CSS framework
