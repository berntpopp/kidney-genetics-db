# Project Research Summary

**Project:** Kidney-Genetics Database — Frontend Migration (v0.2.0)
**Domain:** Brownfield SPA migration (Vuetify 3 + JavaScript → TypeScript + Tailwind CSS v4 + shadcn-vue)
**Researched:** 2026-02-28
**Confidence:** HIGH (stack versions, TypeScript patterns, CSS coexistence strategy); MEDIUM (multi-select pattern, icon mapping completeness, dual dark-mode sync)

---

## Executive Summary

This is a brownfield component-library migration of a production medical/scientific data platform: 73 Vue components and 40 JavaScript files currently built on Vuetify 3 must be replaced with shadcn-vue primitives, Tailwind CSS v4, and full TypeScript. The migration is non-trivial in scope (9 phases, milestone v0.2.0) but technically well-understood. The recommended approach is a strict phase-gate strategy where each phase ends in a working, buildable state — no phase should leave the application in a half-migrated visual state. The CSS coexistence strategy (wrapping Vuetify styles in a named CSS `@layer` below Tailwind's `utilities` layer) is the foundational technical bet that must be verified in Phase 0 before any component work begins.

The recommended target stack is: TypeScript 5.7 + vue-tsc 2.2 (incremental migration with `allowJs: true, checkJs: false`), Tailwind CSS v4.2 via `@tailwindcss/vite` plugin (no `tailwind.config.js`), shadcn-vue CLI with reka-ui primitives, TanStack Table v8.21 for server-side data tables, vee-validate 4.15 + zod 3.24 (not zod v4) for forms, lucide-vue-next for icons, and @vueuse/core v14 for dark mode. All versions are confirmed current as of February 2026 and have specific compatibility constraints that must not be violated (notably: zod must stay on v3, tailwind-merge must be v3.x for Tailwind v4, shadcn-vue@latest installs reka-ui not radix-vue).

The highest-risk migration areas are the server-side data table (GeneTable.vue with 571+ genes, URL-synced state, TanStack Table's non-obvious pagination reset behavior), the multi-select chip pattern for GeneTable filters (no direct shadcn-vue equivalent — requires composing TagsInput + Combobox), and the icon inventory (193 unique MDI icons with approximately 30-40 having no direct Lucide equivalent requiring design decisions). All three risks are addressable with known patterns; none are blockers if planned correctly. The dark-mode dual-system period (Vuetify's `.v-theme--dark` class vs shadcn-vue's `.dark` class on `<html>`) requires an explicit synchronization watch during the coexistence window.

---

## Key Findings

### Recommended Stack

See `.planning/research/STACK.md` for full detail, configurations, and version compatibility matrix.

The migration introduces a precisely constrained set of new packages on top of the existing unchanged stack (Vue 3.5, Vite 7, Pinia 3, Vue Router 4, Axios, D3 7.9, Cytoscape 3.33). TypeScript adoption uses a split-tsconfig pattern (`tsconfig.json` → `tsconfig.app.json` + `tsconfig.node.json`) with `allowJs: true, checkJs: false` enabling incremental file-by-file migration without a big-bang rewrite. Tailwind v4 requires the `@tailwindcss/vite` plugin — no `postcss.config.js`, no `tailwind.config.js`. shadcn-vue uses `@theme inline` CSS directives to map CSS variables to Tailwind utility classes.

**Core technologies (new):**
- TypeScript 5.7 + vue-tsc 2.2 + @vue/tsconfig 0.8: type safety infrastructure — `allowJs` enables incremental migration without big-bang rewrite
- Tailwind CSS v4.2 + @tailwindcss/vite 4.2: CSS-first config via `@theme` directive, 10x faster than v3, no JS config file needed
- shadcn-vue (CLI, latest): component source copied into `src/components/ui/` — full ownership, no runtime library dependency; uses reka-ui v2.8 (NOT radix-vue)
- @tanstack/vue-table 8.21: headless data table replacing `v-data-table`; `manualPagination: true` + `rowCount` for server-side GeneTable
- vee-validate 4.15 + @vee-validate/zod 4.15 + zod 3.24: typed form validation replacing `v-form` + `:rules` arrays (zod v4 is incompatible — peer dep constraint)
- lucide-vue-next 0.475+: tree-shakable SVG icons replacing `@mdi/font` (300KB+ CSS font)
- @vueuse/core 14.2: `useColorMode()` replacing Vuetify's `useTheme()` for dark mode
- tailwind-merge 3.5: must be v3.x for Tailwind v4 compatibility (v2.x is v3-only)
- vitest 4.0 + @vue/test-utils 2: component testing added during migration (currently only Playwright E2E exists)

**Critical version constraints:**
- tailwindcss and @tailwindcss/vite must share the same 4.x.y version
- zod must be pinned to `^3.24.0` — zod v4 breaks @vee-validate/zod type inference
- tailwind-merge v3.x required for Tailwind v4 class names
- shadcn-vue@latest installs reka-ui; do not manually install radix-vue alongside it

### Expected Features

See `.planning/research/FEATURES.md` for full component patterns and code examples.

The migration is a component-for-component replacement with a defined dependency graph (Levels 0-6). The feature surface is fully known from the existing Vuetify codebase audit: 431 v-icon, 412 v-btn/v-col/v-row, 350 v-chip, 254 v-card, 60 v-dialog, 29 v-data-table, 18 v-form.

**Must have (table stakes — parity with current Vuetify implementation):**
- Server-side data table with pagination, sorting, URL-synced state — GeneTable (571+ genes, primary public page)
- 60 dialog/AlertDialog replacements including destructive confirmation dialogs across admin flows
- 18 form migrations to vee-validate + zod with typed schemas replacing untyped `:rules` arrays
- Full icon system migration: 431 v-icon → lucide-vue-next (with MDI-to-Lucide mapping for 193 unique icons)
- Dark mode toggle with CSS variable theming replacing Vuetify's JavaScript theme object
- App navigation bar and mobile drawer (no direct shadcn-vue equivalent — compose from primitives)
- Multi-select with chips for GeneTable filter fields (Combobox + TagsInput composition pattern)
- Range slider (dual-thumb) for evidence score/count filters

**Should have (improvements over Vuetify):**
- TypeScript-first forms: compile-time type safety on form values via `toTypedSchema(zod)` — eliminates runtime validation bugs
- TanStack Table headless rendering: eliminates 50+ lines of `:deep()` CSS overrides in GeneTable
- Smaller bundle: lucide-vue-next tree-shaking vs 300KB+ @mdi/font; shadcn-vue vs ~1.2MB Vuetify
- `toast.promise()` for async admin operations (single call replaces loading/success/error snackbar sequences)
- shadcn-vue Sidebar for admin panel (persistent collapsible nav with keyboard shortcuts)
- Vitest component tests for migrated stores, composables, and API modules

**Defer (v2+ or explicitly out of scope for this migration):**
- D3/Cytoscape internals: visualization rendering logic is unchanged; only wrapper layout classes migrate
- New features: this migration is parity + improvement, not new functionality
- vee-validate v5 / zod v4: both have stability or compatibility issues as of Feb 2026 — revisit in v0.3.0
- Accessible animations/transitions beyond Vue's built-in `<Transition>`: low priority, limited Vuetify usage

**Anti-features (do not replicate from Vuetify):**
- Global `defaults` object (invisible coupling) — use explicit wrapper components instead
- `:deep()` CSS overrides for table cell styling — TanStack Table cell render functions use plain HTML + Tailwind
- Vuetify color props (`color="primary"`) — use Tailwind variant classes (`bg-primary text-primary-foreground`)
- MDI icon font (300KB+ unshakable) — replace with lucide-vue-next named imports only
- Options API in new files — use `<script setup lang="ts">` exclusively

### Architecture Approach

See `.planning/research/ARCHITECTURE.md` for full directory structure, patterns, and CSS configurations.

The target architecture maintains the existing four-layer separation (views → domain components → typed application layer → typed API layer) while introducing `src/components/ui/` as the new shadcn-vue primitive layer, `src/types/` as a new shared type declaration directory, and `src/layouts/` for the extracted app shell. The CSS architecture uses native CSS `@layer` declarations to establish explicit cascade precedence: `theme < base < vuetify < components < utilities` — this is the key mechanism that allows Tailwind utilities to override Vuetify styles during the 7-phase coexistence window. The entire coexistence strategy collapses to a single CSS file (`src/assets/main.css`) that must be structured correctly before any component work begins. In Phase 8, Vuetify removal simplifies `main.css` to a plain `@import "tailwindcss"`.

**Major architectural components:**
1. `src/components/ui/` — shadcn-vue primitives (owned source, CLI-generated, project-modifiable)
2. `src/types/*.ts` — shared TypeScript interfaces enabling typed data flow from API → stores → components
3. CSS layer architecture (`main.css`) — Vuetify + Tailwind v4 coexistence via `@layer` precedence
4. TanStack Table wrapper (`src/components/ui/data-table/`) — shared server-side/client-side table infrastructure
5. `src/composables/useTheme.ts` — `useColorMode()` bridge replacing `useTheme()` from Vuetify
6. `vitest.config.ts` — must inherit from `vite.config.ts` via `mergeConfig` to share path aliases and plugins

**TypeScript migration strategy:**
- `allowJs: true, checkJs: false`: only `.ts` files are type-checked; `.js` files can be imported without errors
- Phase 1 migrates all non-component files (stores, API modules, composables, utils) first — these have the highest type safety value and zero visual risk
- Component files (`*.vue`) convert file-by-file adding `lang="ts"` to `<script setup>`
- Strict mode enabled from day one for all `.ts` files; `checkJs: true` deferred to Phase 8

### Critical Pitfalls

See `.planning/research/PITFALLS.md` for full prevention strategies, code examples, and phase-to-pitfall mapping.

1. **Tailwind v4 preflight destroys Vuetify component styles during coexistence** — Prevention: use selective CSS layer imports in `main.css` (`@import "vuetify/styles" layer(vuetify)`) before Phase 0 exit; verify visually that both Vuetify and Tailwind classes render correctly on a test page. Fallback: `prefix(tw)` syntax adds migration overhead but eliminates all conflicts.

2. **Vuetify CSS variables (`--v-theme-*`) silently break after Phase 8 removal** — Prevention: grep for `--v-theme` and `v-theme--dark` in each component as it is migrated (don't batch this to Phase 8); map to shadcn-vue equivalents (`--primary`, `.dark`) in the same commit. Running grep at Phase 8 start is the final audit.

3. **TanStack Table server-side pagination does not auto-reset pageIndex on filter change** — Prevention: in every server-side table, add explicit `watch(columnFilters, () => pagination.value.pageIndex = 0)`. This is a documented TanStack issue (#4797) that is the opposite of Vuetify's automatic behavior and will produce "page 5 of 2" empty table states if missed.

4. **193 unique MDI icons with ~30-40 having no direct Lucide equivalent** — Prevention: run the icon audit in Phase 0 (`grep -rn "mdi-" frontend/src/ | grep -o "mdi-[a-z-]*" | sort -u`), resolve all gaps before component migration begins, create `src/lib/icons.ts` as a central registry for custom SVGs. Discovering gaps mid-component-migration blocks progress.

5. **shadcn-vue@latest uses reka-ui (not radix-vue) — documentation from before Feb 2025 is wrong** — Prevention: always reference `www.shadcn-vue.com` (current), not `v3.shadcn-vue.com` (Radix-based legacy). Trust CLI output over tutorials. Verify `components.json` schema URL is current. Do not install radix-vue alongside reka-ui.

6. **Dark mode dual-system during coexistence (Vuetify's `.v-theme--dark` vs shadcn-vue's `.dark` on `<html>`)** — Prevention: in Phase 2 when migrating the theme toggle, add a `watch` that syncs Vuetify's theme change to the `<html>` class. New shadcn-vue components only respond to `.dark`; old Vuetify components only respond to `.v-theme--dark`. Both must fire together during coexistence.

---

## Implications for Roadmap

The research strongly supports the 9-phase structure (Phases 0-8) already outlined in the architecture research. The phase order is driven by a strict dependency graph: CSS coexistence must be verified before visual component work; types must exist before components use them; the app shell must be migrated before individual pages; data tables are isolated due to their complexity; admin pages come last due to low user-facing risk.

### Phase 0: Foundation Setup (Non-Breaking)
**Rationale:** Every subsequent phase depends on CSS coexistence, TypeScript infrastructure, and icon inventory. Doing this wrong in Phase 0 causes cascading failures in all later phases. Zero visual changes to the application.
**Delivers:** TypeScript tsconfig triple-file setup; Tailwind v4 + @tailwindcss/vite plugin; shadcn-vue CLI init + `components.json`; CSS coexistence `main.css` with `@layer` strategy; `src/lib/utils.ts` (`cn()` helper); `src/types/*.ts` type declarations; Vitest config; complete MDI icon audit with gap resolution plan; `src/lib/icons.ts` registry scaffolding.
**Addresses:** lucide-vue-next installation; shadcn-vue init with reka-ui; `@theme inline` for shadcn-vue CSS variables.
**Avoids:** Pitfall 1 (preflight/coexistence), Pitfall 2 (no `tailwind.config.js`), Pitfall 3 (wrong shadcn-vue docs), Pitfall 5 (icon gaps discovered late), Pitfall 8 (`@theme inline` missing).
**Research flag:** NONE — this phase is fully specified by research. All steps are deterministic.

### Phase 1: Core Infrastructure — TypeScript Migration (Non-Visual)
**Rationale:** Stores and API modules are consumed by all 73 components. Migrating them first means every subsequent component automatically gets typed data from correctly typed sources. No UI rendering = zero visual regression risk.
**Delivers:** `main.ts` → TypeScript; `router/index.ts` → TypeScript; all 2 Pinia stores → TypeScript composition API; all 12 `src/api/` modules → typed; all 6 composables, services, utils → TypeScript. Vitest added with `mergeConfig` pattern.
**Uses:** `src/types/*.ts` from Phase 0; TypeScript `allowJs: true, checkJs: false`.
**Avoids:** Pitfall 7 (TypeScript strict mode errors — fix in stores/API first where the pattern is clearest); Pitfall 12 (Vitest not inheriting Vite config).
**Research flag:** NONE — TypeScript migration of non-component files follows established patterns.

### Phase 2: App Shell + Navigation + Auth
**Rationale:** The app shell is the skeleton all pages hang on. Migrating it before pages ensures the navigation scaffold is correct and dark mode synchronization is established for the entire coexistence window. Auth modals (3 forms) provide a contained first test of the vee-validate + zod pattern.
**Delivers:** `App.vue` restructured (remove `<v-app>`); `AppHeader.vue` + `AppFooter.vue` (Tailwind layout replacing v-app-bar); mobile navigation (shadcn-vue `Sheet`); dark mode toggle with Vuetify/shadcn-vue sync watcher; auth modals (Login, ChangePassword, ForgotPassword) migrated to vee-validate + zod + shadcn-vue Form; UserMenu; Sonner Toaster added to App.vue root.
**Addresses:** NavigationMenu, Sheet (mobile drawer), Dialog (auth modals), Form/Input/Button (auth forms), dark mode (useColorMode).
**Avoids:** Pitfall 9 (dark mode dual-system — synchronization watcher required); Pitfall 4 (scoped `--v-theme-*` variables — replace in each migrated component); Pitfall 11 (vee-validate computed schema — define schemas as `const`, not in `computed()`).
**Research flag:** NEEDS ATTENTION — visual testing session required after Phase 2. The header is icon-heavy (431 total, many in nav) and layout-critical. Verify icon mapping and mobile drawer at 320px/768px/1280px breakpoints.

### Phase 3: Simple Public Pages
**Rationale:** Home, About, DataSources, Dashboard, and profile pages use basic Vuetify primitives (v-card, v-btn, v-chip, v-alert) with 1:1 shadcn-vue equivalents. Low risk, high pattern-establishment value. Dashboard statistics cards provide the first test of Card + Badge + Progress in combination.
**Delivers:** Home, About, DataSources, Login (page), ForgotPassword (page), Profile, Dashboard views fully migrated. Breadcrumb, Avatar, Alert, Tooltip, Separator, Progress components added from shadcn-vue CLI. Responsive grid layout (`v-row`/`v-col` → Tailwind `grid`/`flex`).
**Addresses:** Card, Badge, Button, Breadcrumb, Avatar, Tooltip (TooltipProvider at app root), Progress, Separator.
**Avoids:** Pitfall 4 (per-component `--v-theme-*` audit); `v-spacer` → `ml-auto` replacement.
**Research flag:** NONE — straightforward component mapping; all patterns established in Phase 2.

### Phase 4: Gene Detail + Evidence Components
**Rationale:** GeneDetail is the primary public page and the most domain-complex. Evidence tier badges require careful color mapping from Vuetify semantic colors (success/warning/info) to shadcn-vue Badge variants. Migrate after simple pages to have established component patterns to follow. The Accordion (v-expansion-panels replacement) and Tabs are both needed here.
**Delivers:** GeneDetail.vue; all 8 `src/components/gene/` components; all 8 `src/components/evidence/` components; EvidenceTierBadge (with OKLCH color mapping); ScoreBreakdown; TierHelpDialog; GeneStructure. Accordion, Tabs, DropdownMenu components added.
**Addresses:** Accordion (replaces v-expansion-panels for evidence cards); Tabs (gene detail sections); DropdownMenu (overflow actions); Switch and Checkbox (gene filters); evidence tier OKLCH color tokens in `--theme inline`.
**Avoids:** Pitfall 4 (all 8 evidence components have scoped styles with `--v-theme-surface` references).
**Research flag:** NEEDS ATTENTION — evidence tier color mapping from Vuetify semantic colors to OKLCH values requires a design decision on the exact oklch values. Also: Accordion + Tabs composition in GeneDetail is medium-complexity and should be manually tested with real data.

### Phase 5: Data Tables (Standalone Phase)
**Rationale:** GeneTable is the highest-complexity single migration item in the entire codebase: server-side pagination + sorting + URL-synced state + multi-select chip filters + dual-thumb range slider + custom cell renderers. Isolating this as its own phase allows focused effort and testing. Admin tables share the infrastructure.
**Delivers:** TanStack Table wrapper infrastructure (`src/components/ui/data-table/`); GeneTable.vue (server-side, URL-synced); Genes.vue (gene list page); Pagination component; multi-select chip filter (Combobox + TagsInput composition); RangeFilter component (dual-thumb Slider); all admin data table views (AdminAnnotations, AdminGeneStaging, AdminUserManagement).
**Addresses:** TanStack Table with `manualPagination: true`, `rowCount` (from API `total`), `onPaginationChange`/`onSortingChange` handlers; server-side pattern (`pageIndex` 0-based vs Vuetify's 1-based `page`); cell render functions with sub-components (`GeneSymbolCell.vue`, `EvidenceScoreCell.vue`).
**Avoids:** Pitfall 5 (pageIndex not resetting — add `watch(columnFilters/sorting, resetPageIndex)` to every server-side table); Pitfall 6 (`rowCount` required, not optional); Pitfall 10 (cell render functions — use sub-components, not nested `h()` calls); Pitfall 14 (working state — migrate tables one at a time, verify each before proceeding).
**Research flag:** NEEDS DEEPER RESEARCH during planning — multi-select pattern (Combobox + TagsInput) is MEDIUM confidence from research; may need a prototype before committing the full GeneTable migration. Recommend building `MultiSelect.vue` as a standalone isolated test first. URL state sync with TanStack Table needs explicit mapping from existing `parseUrlParams`/`updateUrl` logic.

### Phase 6: Admin Panel
**Rationale:** Admin-only pages have the smallest user base. Forms with vee-validate + Zod are concentrated here (backup/settings dialogs — 5 backup + 2 settings + user management). Migrate after data tables because admin views heavily use the shared DataTable infrastructure from Phase 5.
**Delivers:** AdminDashboard, AdminPipeline, AdminLogViewer (with right-side Sheet drawer), all backup dialogs (5 components), settings dialogs (2 components), AdminHeader. shadcn-vue Sidebar for admin persistent navigation. All admin forms migrated to typed zod schemas.
**Addresses:** Sidebar (replaces multiple v-navigation-drawer in admin); Sheet (right-side log viewer overlay); AlertDialog (all destructive admin confirmations); form schemas for user CRUD (create/edit/delete); AdminLogViewer dark mode (hardcoded `.v-theme--dark` CSS selectors must be replaced).
**Avoids:** Pitfall 4 (AdminLogViewer has hardcoded `.v-theme--dark` selectors — flag for explicit replacement); Pitfall 11 (admin forms are complex with conditional validation — use `zod.superRefine()` for role-conditional rules, not `computed()` schemas).
**Research flag:** NONE — admin patterns are standard; all primitives established in earlier phases.

### Phase 7: Network Analysis + Visualization Wrappers
**Rationale:** D3 and Cytoscape components only need their Vue wrapper layout classes migrated — internal rendering logic is unchanged. Network analysis page is complex (Cytoscape + overlays) but the complexity is in the visualization library, not in the migration. Leave for late phases when all component patterns are fully established. Lowest regression risk because SVG/canvas rendering is isolated from CSS.
**Delivers:** NetworkAnalysis.vue, NetworkGraph.vue (Cytoscape wrapper), NetworkSearchOverlay.vue, ClusterDetailsDialog.vue, EnrichmentTable.vue; 7 D3 chart Vue wrappers (CSS layout only, D3 internals unchanged); GeneStructure.vue.
**Addresses:** Cytoscape container layout in Tailwind; D3 wrapper responsive sizing; network filter forms using established vee-validate patterns.
**Avoids:** Pitfall (D3/Cytoscape SVG elements receiving Tailwind CSS resets — wrap in `@layer components` isolation or test that preflight doesn't affect SVG computed styles).
**Research flag:** NONE — D3/Cytoscape are isolated from the CSS migration; only wrapper layout changes are needed.

### Phase 8: Vuetify Removal + Final Cleanup
**Rationale:** Final phase removes all Vuetify references once all components are migrated. This is a cleanup phase, not a migration phase. The coexistence CSS architecture (Phase 0) was designed to make this a mechanical cleanup.
**Delivers:** Zero remaining `v-` tags or Vuetify imports (grep verification); `vuetify` and `@mdi/font` uninstalled from `package.json`; `src/plugins/vuetify.js` deleted; `main.css` simplified to plain `@import "tailwindcss"`; `checkJs: true` enabled; `vue-tsc --noEmit` exits 0; bundle size report confirming @mdi/font absence (~250KB reduction).
**Addresses:** Final `grep -rn "v-theme" frontend/src/` audit (must return 0 results); final `grep -rn "mdi-" frontend/src/` audit (must return 0 results); ESLint config updated with TypeScript-aware rules; Playwright E2E suite verified on clean Tailwind-only build.
**Avoids:** Pitfall 4 (final `--v-theme-*` audit ensures no silent CSS breaks); ensuring `@mdi/font` is not in final bundle.
**Research flag:** NONE — this phase is purely mechanical once all preceding phases are complete.

### Phase Ordering Rationale

The 9-phase order follows two primary constraints from research:

**Dependency graph drives the first 3 phases:** CSS coexistence (Phase 0) is a prerequisite for all visual work. TypeScript types (Phase 0 + 1) are prerequisites for typed components. The app shell (Phase 2) is a prerequisite for page-level work. These three phases are strictly ordered.

**Risk profile drives Phases 3-7:** Simple pages (Phase 3) establish patterns at low risk. GeneDetail (Phase 4) applies established patterns to medium-complexity domain components. Data tables (Phase 5) are isolated as a standalone phase because TanStack Table's API surface is large, unfamiliar, and the GeneTable is the highest-complexity single component in the codebase. Admin pages (Phase 6) come after data tables because they depend on the shared DataTable infrastructure. Visualization wrappers (Phase 7) come last because they have the lowest migration complexity and the highest isolation from CSS changes.

**Research flags identify where deeper planning is needed:** Phase 5 needs a multi-select prototype before committing the GeneTable migration plan. Phase 2 and Phase 4 need visual testing checklists due to icon density and color mapping complexity respectively.

### Research Flags

Phases needing deeper investigation during planning:
- **Phase 5 (Data Tables):** Multi-select chip pattern (Combobox + TagsInput) is MEDIUM confidence — build an isolated prototype before planning the full GeneTable migration. URL sync from `parseUrlParams`/`updateUrl` → TanStack Table state needs explicit mapping documented before Phase 5 begins. Recommend a `research-phase` sub-task specifically for the GeneTable migration plan.
- **Phase 2 (App Shell):** Icon mapping for the 193 unique MDI icons (gap audit from Phase 0) feeds into Phase 2 planning. Phase 2 cannot be fully planned until the icon gap resolution decisions are made.

Phases with established patterns (skip additional research):
- **Phase 0:** All tooling setup is precisely specified in STACK.md and ARCHITECTURE.md with exact configurations.
- **Phase 1:** TypeScript migration of non-component files follows standard patterns; no novel decisions required.
- **Phase 3:** Basic Vuetify component → shadcn-vue mapping is HIGH confidence for all components in scope (Card, Badge, Button, Breadcrumb, Alert, Separator, Progress, Tooltip).
- **Phase 6:** Admin forms and dialogs use patterns established in Phase 2; admin tables use infrastructure from Phase 5.
- **Phase 7:** D3/Cytoscape wrappers only need layout class changes; no new component patterns needed.
- **Phase 8:** Mechanical cleanup with grep verification; no novel decisions.

---

## Confidence Assessment

| Area | Confidence | Notes |
|------|------------|-------|
| Stack | HIGH | All versions verified via npm registry as of 2026-02-28. Compatibility constraints are precise and documented (zod v3 lock, tailwind-merge v3, reka-ui vs radix-vue). No version is uncertain. |
| Features | HIGH (core), MEDIUM (complex) | Card/Button/Dialog/Form/Toast patterns are HIGH — verified from official shadcn-vue docs. Multi-select chip (Combobox+TagsInput composition) is MEDIUM — confirmed from community discussion #869, no official example. Dual-thumb range slider is MEDIUM — Radix Vue docs confirm array value, shadcn-vue wrapper behavior inferred. |
| Architecture | HIGH (TypeScript/Tailwind), MEDIUM (coexistence) | TypeScript tsconfig pattern, CSS layer architecture, and component structure are HIGH — verified from Vue official docs and Tailwind v4 release docs. Vuetify + Tailwind v4 coexistence via `@layer vuetify` is MEDIUM — the mechanism is correct (CSS spec) but based on community discussion (#21241), not official Vuetify documentation. |
| Pitfalls | HIGH (14 documented with code-level prevention) | Critical pitfalls have specific code fixes, grep commands, and phase assignments. TanStack pagination behavior (Pitfall 5/6) verified against TanStack docs and open issue #4797. Dark mode dual-system (Pitfall 9) is a known architectural reality with a clear synchronization solution. |

**Overall confidence:** HIGH for execution. The migration is technically well-understood. The one genuine unknown is the multi-select chip pattern's production behavior — a prototype in Phase 5 planning resolves this before GeneTable migration commits begin.

### Gaps to Address

- **Multi-select chip pattern production validation:** Build an isolated `MultiSelect.vue` prototype using Combobox + TagsInput before committing to the GeneTable migration plan. The pattern is MEDIUM confidence; verify keyboard accessibility, v-model integration with vee-validate, and mobile behavior.

- **Complete MDI icon gap resolution (193 unique icons, ~30-40 gaps):** The icon audit command (`grep -rn "mdi-" frontend/src/ --include="*.vue" | grep -o "mdi-[a-z-]*" | sort -u`) produces the full list. Each gap requires a design decision: closest Lucide icon, Lucide Lab icon, or custom SVG. This must be resolved in Phase 0 before any component migration begins. Estimated effort: 2-4 hours for mapping; 4-8 hours for custom SVG components if any are needed.

- **Evidence tier OKLCH color values:** The exact OKLCH values for kidney-primary (teal), dna-primary (sky blue), and Vuetify's semantic colors (success/warning/info/error) need to be agreed upon and hardcoded into `main.css` in Phase 0. The mapping from Vuetify hex values to OKLCH is documented in ARCHITECTURE.md but requires design sign-off. Mismatched colors in EvidenceTierBadge will be visible to medical users.

- **GeneTable URL sync with TanStack Table:** The existing `parseUrlParams`/`updateUrl` logic in GeneTable.vue syncs filter/pagination state to URL query parameters. This logic is in Vue script and does not use Vuetify; however, the translation from TanStack Table's `pageIndex` (0-based) to URL param `page` (1-based) and back requires explicit mapping. Document this mapping before Phase 5 planning.

- **Vitest coverage targets:** No existing unit tests exist for frontend code (only Playwright E2E). Phase 1 adds Vitest but no coverage requirements are defined. Recommend establishing minimum coverage targets for stores (80%+) and API modules (70%+) before Phase 1 begins.

---

## Sources

### Primary (HIGH confidence — official documentation)

- [Tailwind CSS v4.0 Release + Installation](https://tailwindcss.com/docs/installation) — @tailwindcss/vite plugin setup, `@theme` directive, no `tailwind.config.js`
- [shadcn-vue official site](https://www.shadcn-vue.com/) — component API, theming, dark mode, reka-ui switch
- [shadcn-ui Tailwind v4 docs](https://ui.shadcn.com/docs/tailwind-v4) — `@theme inline` pattern, OKLCH variables
- [Vue 3 TypeScript Overview](https://vuejs.org/guide/typescript/overview.html) — official `defineProps<T>()`, `withDefaults`, SFC patterns
- [vuejs/tsconfig](https://github.com/vuejs/tsconfig) — `@vue/tsconfig/tsconfig.dom.json` base config
- [TanStack Table Vue Pagination Guide](https://tanstack.com/table/v8/docs/guide/pagination) — `manualPagination`, `rowCount`, `autoResetPageIndex`
- [TanStack Table Pagination APIs](https://tanstack.com/table/v8/docs/api/features/pagination) — `pageCount` vs `rowCount`
- [VeeValidate Zod Integration](https://vee-validate.logaretm.com/v4/integrations/zod-schema-validation/) — `toTypedSchema()` usage
- [VueUse useColorMode](https://vueuse.org/core/useColorMode/) — dark mode implementation
- [Vitest Getting Started](https://vitest.dev/guide/) — configuration, `mergeConfig` pattern
- [Lucide Vue Next](https://lucide.dev/guide/packages/lucide-vue-next) — named imports, tree-shaking

### Secondary (MEDIUM confidence — community with strong signal)

- [Vuetify + Tailwind CSS Coexistence Discussion #21241](https://github.com/vuetifyjs/vuetify/discussions/21241) — `@layer vuetify` wrapping solution
- [TanStack Table Issue #4797](https://github.com/TanStack/table/issues/4797) — pageIndex not resetting on filter change (documented bug + workaround)
- [shadcn-vue GitHub Discussion #869](https://github.com/unovue/shadcn-vue/issues/869) — multi-select chip pattern (Combobox + TagsInput)
- [shadcn-vue Changelog](https://www.shadcn-vue.com/docs/changelog) — Feb 2025 reka-ui migration confirmation
- [Tailwind v4 preflight discussion #17481](https://github.com/tailwindlabs/tailwindcss/discussions/17481) — selective preflight import approach
- [vee-validate Issue #4588](https://github.com/logaretm/vee-validate/issues/4588) — computed schema loses TypeScript inference
- [vee-validate Issue #5027](https://github.com/logaretm/vee-validate/issues/5027) — zod v4 incompatibility confirmed

### Tertiary (LOW confidence — inferential or engineering blogs)

- [Mixmax JS→TS incremental migration](https://www.mixmax.com/engineering/incremental-migration-from-javascript-to-typescript-in-our-largest-service) — `allowJs/checkJs` strategy pattern (validated by official TypeScript docs, blog provides real-world context)
- Radix Vue Slider multi-thumb behavior inferred from shadcn-vue wrapping Radix primitives — MEDIUM/LOW, needs prototype verification for dual-thumb confirmation

---

*Research completed: 2026-02-28*
*Ready for roadmap: yes*
