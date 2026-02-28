# Pitfalls Research

**Domain:** Frontend migration (Vuetify 3 → TypeScript + Tailwind CSS v4 + shadcn-vue)
**Researched:** 2026-02-28
**Confidence:** MEDIUM-HIGH (Tailwind v4 specifics HIGH, TanStack Table MEDIUM, TypeScript migration HIGH, icon gaps MEDIUM)

---

## Critical Pitfalls

### Pitfall 1: Tailwind v4 Preflight Destroys Vuetify Components During Coexistence

**What goes wrong:**
Tailwind v4's preflight (base reset) uses native CSS `@layer base` and applies a `*` selector reset that sets margins, padding, borders, and box-sizing to zero. When imported after Vuetify styles, this flattens Vuetify's component styles. When imported before, Vuetify's styles win over Tailwind utilities applied to new components. Either way, something breaks.

The specific failure modes:
- Buttons lose their height/padding (Vuetify uses explicit margin/padding; preflight zeros them)
- Form fields collapse (border-box sizing conflict)
- Data table rows lose row height
- Chips/badges lose their pill shape

**Why it happens:**
In Tailwind v4, the `important` configuration option was removed entirely. In v3, the escape hatch was `important: true` in `tailwind.config.js`. That option does not exist in v4. CSS cascade layers are now the primary tool, but Vuetify's styles ship outside any `@layer`, which means they have higher specificity than any layered Tailwind styles regardless of import order.

**How to avoid:**
Use the CSS `@layer` wrapping strategy to explicitly slot Vuetify into a named layer below Tailwind utilities:

```css
/* src/assets/main.css — import order matters */
@layer theme, base, vuetify, components, utilities;

@import "tailwindcss/theme.css" layer(theme);
@import "tailwindcss/preflight.css" layer(base);
@import "vuetify/styles" layer(vuetify);
@import "tailwindcss/utilities.css" layer(utilities);
```

This wraps Vuetify into a named layer that sits below `utilities`, so Tailwind utility classes override Vuetify styles when both are present.

If the above produces unexpected side effects, the fallback is the `prefix(tw)` syntax in v4:

```css
@import "tailwindcss" prefix(tw);
```

This changes all Tailwind classes to require the `tw:` variant prefix (e.g., `tw:flex`, `tw:bg-red-500`). No class name conflicts are possible, but every shadcn-vue component template needs the prefix added, which creates significant overhead. Use only if the layer approach fails.

**Warning signs:**
- Vuetify buttons, chips, or text fields visually collapse after adding Tailwind
- Tailwind utility classes appear to have no effect on newly created components
- Browser DevTools shows Tailwind rules crossed out (overridden by unlayered styles)

**Phase to address:** Phase 0 (Foundation Setup) — must be solved before any component work begins

---

### Pitfall 2: Tailwind v4 Has No `important` Config Option — Specificity Cannot Be Forced

**What goes wrong:**
Teams accustomed to Tailwind v3's `important: true` option (or the `important` selector strategy) try to add it to their v4 setup. This option was removed in v4 and will either silently fail or throw a configuration error depending on the tool.

Even worse: some teams use inline `!important` on individual classes (`!bg-red-500`) and discover this works inconsistently when fighting Vuetify's unlayered styles during coexistence.

**Why it happens:**
Tailwind v4 moved from JavaScript configuration to CSS-first configuration (`@theme` directive). The JS config file (`tailwind.config.js`) is deprecated. Any v3 configuration guide that says "set `important: true`" is invalid for v4.

**How to avoid:**
- Delete any `tailwind.config.js` or `tailwind.config.ts` files
- Use `@theme` in CSS for all customization
- Use native CSS `@layer` for specificity management (see Pitfall 1)
- Individual `!` prefixes on Tailwind classes still work in v4 for one-off overrides

**Warning signs:**
- Seeing `tailwind.config.js` referenced in documentation and assuming it applies
- Confusion when `important: '#app'` selector strategy is suggested in search results (v3-only)

**Phase to address:** Phase 0

---

### Pitfall 3: shadcn-vue v1 Uses Reka UI, Not Radix Vue — Documentation Is Fragmented

**What goes wrong:**
As of February 20, 2025, shadcn-vue switched its underlying primitive library from `radix-vue` to `reka-ui` (Reka UI v2). The package name changed. Documentation at `v3.shadcn-vue.com` refers to the old Radix-based version. Documentation at `www.shadcn-vue.com` refers to the new Reka-based version. Tutorials and Stack Overflow answers written before February 2025 use the old API.

Specific breakages:
- Component import paths differ between the two versions
- The `components.json` schema changed; old schema references (`https://shadcn-vue.com/schema.json`) point to the wrong registry
- Component props and slot names changed in some components between radix-vue and reka-ui

**Why it happens:**
The migration happened mid-2025 and a large body of tutorials, YouTube guides, and examples were written before it. The CLI distinguishes between versions: `shadcn-vue@latest` installs Reka-based v1; `shadcn-vue@radix` installs the old Radix-based version.

**How to avoid:**
- Always use `npx shadcn-vue@latest init` (Reka UI / current)
- Verify `components.json` uses the current schema URL
- Cross-reference component API against `www.shadcn-vue.com` not `v3.shadcn-vue.com`
- When a tutorial's code differs from what the shadcn-vue CLI generates, trust the CLI output

**Warning signs:**
- Component imports from `radix-vue` appear in generated code (should be `reka-ui`)
- `components.json` `$schema` references an old URL
- Generated component code does not match tutorials from 2024 or early 2025

**Phase to address:** Phase 0

---

### Pitfall 4: Vuetify CSS Variables (`--v-theme-*`) in Scoped Styles Silently Break After Vuetify Removal

**What goes wrong:**
This codebase has 25+ scoped `<style>` blocks using `rgb(var(--v-theme-surface))`, `rgba(var(--v-theme-primary), 0.1)`, and similar patterns. It also has 18 selectors targeting `.v-theme--dark`. When Vuetify is removed in Phase 8, these CSS variable references resolve to `rgb(var(undefined))`, which renders as transparent or black — not a build error, just a visual breakage that may not be caught without manual review.

Specific patterns found in this codebase:
```css
/* These will silently break when Vuetify is removed */
background-color: rgb(var(--v-theme-surface-light));
border: 2px dashed rgb(var(--v-theme-grey-lighten-2));
background-color: rgba(var(--v-theme-primary), 0.1);
background-color: rgba(var(--v-theme-on-surface), 0.05);
.v-theme--dark .json-display { ... }
```

**Why it happens:**
These references are in `<style scoped>` blocks, not in templates. ESLint and vue-tsc do not check CSS property values. There is no compiler error — the build passes, but the styles silently degrade.

**How to avoid:**
Before Phase 8 removal, run:
```bash
grep -rn "v-theme\|--v-" frontend/src/ --include="*.vue"
grep -rn "v-theme--dark" frontend/src/ --include="*.vue"
```
Replace each with the shadcn-vue CSS variable equivalents. The mapping is:
- `--v-theme-primary` → `hsl(var(--primary))`
- `--v-theme-surface` → `hsl(var(--background))`
- `--v-theme-surface-variant` → `hsl(var(--muted))`
- `--v-theme-on-surface` → `hsl(var(--foreground))`
- `.v-theme--dark` → `.dark` (shadcn-vue uses `.dark` class on `<html>`)

**Warning signs:**
- Any gradient, border, or background defined in scoped `<style>` blocks referencing `--v-theme-*`
- Components that look fine in light mode but are invisible in dark mode after migration

**Phase to address:** Phase 2 (start tracking), Phase 8 (final audit before removal). Each component migration should replace its own scoped style variables.

---

### Pitfall 5: TanStack Table Server-Side Pagination Does Not Auto-Reset pageIndex When Filters Change

**What goes wrong:**
When `manualPagination: true` and `manualFiltering: true` are set together (which is required for server-side operations), `autoResetPageIndex` defaults to `false`. This is by design but is the opposite of Vuetify's `v-data-table-server` behavior.

In the current `GeneTable.vue`, when a user is on page 5 and changes the source filter or search query, the existing implementation handles this because the custom `debouncedSearch` function explicitly resets the page. In TanStack Table, there is no equivalent automatic behavior — the page index remains at 5 even though the new filter may only have 2 pages of results, producing an empty table with confusing pagination controls showing "page 5 of 2."

This is a documented bug/design issue: [TanStack/table issue #4797](https://github.com/TanStack/table/issues/4797).

**Why it happens:**
The TanStack philosophy for manual pagination is: "your server knows the pagination state; the table doesn't reset what you don't tell it to reset." This is technically correct but differs from what users expect and from Vuetify's behavior.

**How to avoid:**
In every server-side TanStack Table component, add explicit page index resets in filter/sorting change handlers:

```typescript
// In your Vue component managing server-side table state
const sorting = ref<SortingState>([])
const columnFilters = ref<ColumnFiltersState>([])
const pagination = ref<PaginationState>({ pageIndex: 0, pageSize: 10 })

// Watch for filter changes and reset page
watch(columnFilters, () => {
  pagination.value = { ...pagination.value, pageIndex: 0 }
}, { deep: true })

watch(sorting, () => {
  pagination.value = { ...pagination.value, pageIndex: 0 }
})
```

Alternatively, use the `table.resetPageIndex()` method in your filter change handlers.

**Warning signs:**
- Empty table body after changing filters while on page > 1
- Pagination controls show "page N of M" where N > M
- No automatic page reset when search input changes

**Phase to address:** Phase 5 (Data Tables) — must be addressed for every server-side table

---

### Pitfall 6: TanStack Table Requires `pageCount` or `rowCount` — Not Optional for Server-Side

**What goes wrong:**
In Vuetify's `v-data-table-server`, you pass `:items-length="totalItems"` and pagination works automatically. In TanStack Table with `manualPagination: true`, you must provide either:
- `pageCount`: total number of pages (requires knowing this from the API), or
- `rowCount`: total number of rows (table calculates pages from this)

If neither is provided, the table renders with only "first page" and "previous/next" buttons but no total page count, no "go to page N" functionality, and the pagination component cannot determine if "next" is available.

The current API responses return `total` (total row count). This maps to `rowCount`, not `pageCount`. Passing the wrong one (or omitting both) produces silent failures in pagination UI.

**Why it happens:**
Vuetify abstracts this calculation internally. TanStack Table exposes the primitives directly. The property names differ between versions: TanStack Table versions below 8.13.0 require `pageCount` to be computed manually; 8.13.0+ supports `rowCount`.

**How to avoid:**
```typescript
const table = useVueTable({
  // ...
  manualPagination: true,
  rowCount: totalItems.value, // from API response.total
  // OR: pageCount: Math.ceil(totalItems.value / pageSize.value)
  onPaginationChange: (updater) => {
    pagination.value = typeof updater === 'function'
      ? updater(pagination.value)
      : updater
  },
  state: {
    get pagination() { return pagination.value }
  }
})
```

Verify the installed TanStack Table version supports `rowCount` (requires 8.13.0+). If using an older version, compute `pageCount` manually.

**Warning signs:**
- "Next" button always enabled even on last page
- Pagination shows "1 of ?" or "page 1 of undefined"
- Total count display shows incorrect number

**Phase to address:** Phase 5 (Data Tables) — establish this pattern in the shared DataTable component first

---

### Pitfall 7: TypeScript Strict Mode Rejects Existing JavaScript Patterns Pervasively

**What goes wrong:**
The migration plan calls for `strict: true` in `tsconfig.json` from day one. This is the right call, but it triggers errors across every file converted, not just the file being migrated. The most common failure patterns in this codebase's existing code:

1. **Vuex/Pinia state accessed without type narrowing:**
   ```typescript
   // Current pattern (works in JS, fails in strict TS)
   const user = authStore.user
   user.email.toLowerCase() // Error: Object is possibly 'null'
   ```

2. **API response objects typed as `any`:**
   ```typescript
   // Common implicit any from axios responses
   const response = await api.get('/genes') // response.data is any
   const genes = response.data.genes // No error, but no type safety either
   ```

3. **Event handlers in Vue templates:**
   ```typescript
   // defineProps with complex types from imported interfaces
   // Vue compiler cannot infer complex union types in templates
   const props = defineProps<{ tier: 'A' | 'B' | 'C' | 'D' | null }>()
   ```

4. **`defineProps` default values require `withDefaults`:**
   ```typescript
   // Error: defaults for type-based props require withDefaults
   const { size = 'medium' } = defineProps<{ size?: string }>()
   // Correct:
   const props = withDefaults(defineProps<{ size?: string }>(), { size: 'medium' })
   ```

**Why it happens:**
JavaScript code uses implicit `any` everywhere. TypeScript's strict mode enforces explicit type annotations. The Vue SFC type system adds additional constraints around `defineProps` generic inference that don't exist in plain TypeScript.

**How to avoid:**
- Start with the non-component files (stores, API modules, utils) where strict TypeScript is straightforward
- Create explicit interface types in `src/types/` before migrating components that use them
- Use `as` type assertions sparingly and only for genuinely safe casts (e.g., API responses with well-known shapes)
- Accept that the Phase 1 TypeScript migration will surface ~50-200 type errors that must be fixed incrementally

**Warning signs:**
- `vue-tsc --noEmit` produces hundreds of errors after adding `lang="ts"` to a single component
- Template expressions show red underlines in VS Code after strict mode is enabled
- `Object is possibly 'null'` or `'undefined'` errors throughout the auth store

**Phase to address:** Phase 0 (configure tsconfig), Phase 1 (bulk of fixes), ongoing in Phases 2-7

---

### Pitfall 8: 193 Unique MDI Icons — Approximately 30-40 Have No Direct Lucide Equivalent

**What goes wrong:**
The migration plan shows 431 `v-icon` usages with 193 unique icon names. The MDI icon set contains ~7,000 icons; Lucide has ~1,600. Many medical/scientific/pipeline-specific MDI icons used in this codebase do not exist in Lucide:

Icons with no direct Lucide equivalent (from this codebase):
- `mdi-dna` (19 uses) → Lucide has `Dna` — this one works
- `mdi-protein` → No Lucide equivalent; use custom SVG or `Atom`
- `mdi-virus` / `mdi-virus-outline` → No Lucide equivalent; use `Bug` or custom SVG
- `mdi-pipeline` → No Lucide equivalent; use `Workflow` or `GitBranch`
- `mdi-medical-bag` → No Lucide equivalent; use `Briefcase-Medical` or `Stethoscope`
- `mdi-speedometer` → No Lucide equivalent; use `Gauge`
- `mdi-chart-scatter-plot` → No Lucide equivalent; use `ScatterChart`
- `mdi-chart-box` → No Lucide equivalent; use `BarChart3`
- `mdi-database-sync` → No Lucide equivalent; use `DatabaseBackup` or `RefreshCw` + `Database`
- `mdi-database-import` → No Lucide equivalent; use `DatabaseIcon` with custom indicator
- `mdi-robot` → No Lucide equivalent; use `Bot`
- `mdi-test-tube` → Lucide has `TestTube` — this one works
- `mdi-weather-sunny` / `mdi-weather-night` → Use `Sun` / `Moon`
- `mdi-fit-to-screen` → Use `Maximize2`
- `mdi-select-all` → No Lucide equivalent; use `CheckSquare`
- `mdi-vuejs` → No Lucide equivalent; omit or use custom SVG

Teams commonly discover this during Phase 2 icon migration and spend 2-3x longer than estimated because each gap requires a design decision (use closest available icon, create custom SVG, or use Lucide Lab).

**Why it happens:**
Lucide is a minimal, clean icon set focused on general UI icons. MDI is a comprehensive icon set with thousands of domain-specific icons. Medical, scientific, and DevOps icons are heavily represented in MDI and underrepresented in Lucide.

**How to avoid:**
- Conduct a complete icon audit in Phase 0 using: `grep -rn "mdi-" frontend/src/ --include="*.vue" | grep -o "mdi-[a-z-]*" | sort -u`
- For each unmapped icon, decide: (a) closest Lucide icon, (b) Lucide Lab icon, or (c) custom SVG component
- Create `src/lib/icons.ts` as a central icon registry that can accommodate custom icons alongside Lucide imports
- Do not attempt to resolve all 193 icons in one sitting — the 19 most-used icons cover 60%+ of occurrences

**Warning signs:**
- Icon audit deferred until Phase 2 (find gaps too late, block component migration)
- Assuming every `mdi-*` has a matching Lucide name
- Missing icons render as blank space, not as an error

**Phase to address:** Phase 0 (audit), Phase 2 (icon infrastructure), Phases 3-7 (per-component replacement)

---

## Moderate Pitfalls

### Pitfall 9: Dark Mode Dual System — Vuetify (`useTheme()`) and shadcn-vue (`.dark` class) Conflict

**What goes wrong:**
This codebase uses Vuetify's `useTheme()` composable to manage dark mode. The current `App.vue` calls `theme.change('dark'/'light')`. Vuetify applies dark mode via a `.v-theme--dark` class on the root element.

shadcn-vue uses a completely different mechanism: it expects a `.dark` class on the `<html>` element (standard Tailwind dark mode convention). During coexistence phases, both systems run simultaneously. When the user toggles dark mode, Vuetify applies `.v-theme--dark` but the new shadcn-vue components are waiting for `.dark` — they don't switch.

**How to avoid:**
In Phase 2, when migrating the theme toggle, add synchronization logic:

```typescript
// When Vuetify theme changes, also update the html class
watch(() => theme.global.current.value.dark, (isDark) => {
  document.documentElement.classList.toggle('dark', isDark)
})
```

Then in Phase 8, remove Vuetify's theme system entirely and use only VueUse `useColorMode()`.

**Warning signs:**
- Navigation (migrated) stays light while page content (still Vuetify) switches to dark
- shadcn-vue components do not respond to the dark mode toggle

**Phase to address:** Phase 2 (add synchronization), Phase 8 (remove Vuetify theme)

---

### Pitfall 10: TanStack Table Custom Cell Renderers — No Slot-Based System Like Vuetify

**What goes wrong:**
Vuetify's data table uses Vue slots for custom cell rendering:
```html
<template #[`item.approved_symbol`]="{ item }">
  <router-link ...>{{ item.approved_symbol }}</router-link>
</template>
```

TanStack Table uses a JavaScript/TypeScript column definition with `cell` functions:
```typescript
const columns: ColumnDef<Gene>[] = [
  {
    accessorKey: 'approved_symbol',
    header: ({ column }) => h(DataTableColumnHeader, { column, title: 'Symbol' }),
    cell: ({ row }) => h(RouterLink, { to: `/genes/${row.original.approved_symbol}` },
      () => row.getValue('approved_symbol'))
  }
]
```

The `h()` render function approach is unfamiliar to developers who work primarily in Vue templates. Complex cells with multiple child components (the current GeneTable has cells with RouterLink + Tooltip + v-icon + conditional chip) become verbose render functions. The TypeScript types for `ColumnDef` are stricter than Vuetify's slot approach.

**How to avoid:**
- Create small single-purpose sub-components for complex cell content (e.g., `GeneSymbolCell.vue`, `EvidenceScoreCell.vue`)
- Import these as Vue components and render them with `h(GeneSymbolCell, { gene: row.original })`
- This keeps template syntax inside Vue SFCs instead of in render functions

**Warning signs:**
- Trying to use `<template>` slots inside TanStack Table column definitions (they don't work)
- Attempting to write HTML strings in cell functions
- Column definitions growing to 200+ lines of nested `h()` calls

**Phase to address:** Phase 5 (Data Tables)

---

### Pitfall 11: vee-validate + Zod Computed Schema Loses TypeScript Inference

**What goes wrong:**
When `toTypedSchema(zodSchema)` is wrapped in a `computed()`, TypeScript inference for form values degrades to `GenericObject` instead of the specific typed shape. This is a documented vee-validate issue ([#4588](https://github.com/logaretm/vee-validate/issues/4588)).

For forms that need dynamic schemas (e.g., changing validation rules based on user role or localization), this is a real constraint.

Additionally, the `<Form @submit>` component's submit handler type does not merge with the Zod-inferred type in all cases ([#5078](https://github.com/logaretm/vee-validate/issues/5078)).

**How to avoid:**
- Define Zod schemas as `const` outside of `computed()` whenever possible
- For dynamic validation (e.g., "required if admin"), use Zod's conditional `.superRefine()` or `.refine()` methods within a static schema definition
- Be aware that `refine()` and `superRefine()` do not execute when required fields are empty (Zod design choice); add `.min(1)` or `.nonempty()` constraints for required fields

**Warning signs:**
- `handleSubmit` callback receives `values` typed as `Record<string, any>` instead of `{ username: string; password: string }`
- Type errors in `<Form @submit="onSubmit">` where `onSubmit` is typed for the specific schema

**Phase to address:** Phase 2 (auth forms), Phase 6 (admin forms)

---

### Pitfall 12: Vitest Setup Requires `@vitejs/plugin-vue` Alignment With Production Config

**What goes wrong:**
The migration plan adds Vitest for component testing. The common mistake is configuring a separate `vitest.config.ts` that doesn't share the main `vite.config.ts` plugin setup. When the Vite config includes the `@tailwindcss/vite` plugin and path aliases, but the Vitest config does not extend from it, component tests fail to resolve CSS imports or `@/` path aliases.

**How to avoid:**
Use the `mergeConfig` pattern to ensure Vitest config inherits from Vite config:

```typescript
// vitest.config.ts
import { mergeConfig } from 'vite'
import { defineConfig } from 'vitest/config'
import viteConfig from './vite.config'

export default mergeConfig(viteConfig, defineConfig({
  test: {
    environment: 'jsdom',
    globals: true,
  }
}))
```

**Warning signs:**
- `Cannot find module '@/components/...'` in test files
- CSS import errors during test runs

**Phase to address:** Phase 1 (when Vitest is added)

---

### Pitfall 13: Tailwind v4 CSS-First Config — `@theme` Variables Do Not Auto-Generate Utilities for Custom Names

**What goes wrong:**
In Tailwind v3, adding a custom color to `tailwind.config.js` automatically generated all utility variants (`bg-kidney-primary`, `text-kidney-primary`, `border-kidney-primary`, etc.). In Tailwind v4 with `@theme`, you define CSS custom properties, but the utility generation follows a naming convention.

Specifically, Vuetify defines custom colors like `kidney-primary` and `dna-primary`. When mapping these to Tailwind v4:

```css
@theme {
  --color-kidney-primary: oklch(0.52 0.14 192);  /* teal */
  --color-dna-primary: oklch(0.62 0.15 213);     /* sky blue */
}
```

This works and generates `bg-kidney-primary`, `text-kidney-primary`, etc. But the naming of variables must match exactly — if you define `--color-kidney_primary` (underscore) instead of `--color-kidney-primary` (hyphen), the utility names differ.

For shadcn-vue's variables, the `@theme inline` directive is required to expose CSS variables as Tailwind utilities without OKLCH conversion issues:

```css
@theme inline {
  --color-background: var(--background);  /* maps to bg-background, text-background */
  --color-foreground: var(--foreground);
}
```

Missing the `inline` keyword causes shadcn-vue color utilities to work differently than expected.

**How to avoid:**
- Use hyphens (not underscores) in all `@theme` variable names
- Use `@theme inline` for all shadcn-vue CSS variable mappings
- Verify each custom color generates the expected utilities with a build test after Phase 0

**Warning signs:**
- `bg-kidney-primary` class appears in markup but has no CSS output
- shadcn-vue components show wrong colors in dark mode
- Tailwind IntelliSense doesn't suggest custom color names in VS Code

**Phase to address:** Phase 0

---

### Pitfall 14: Working State Requirement Conflicts With Large Phase Scope

**What goes wrong:**
The migration plan requires each phase to end in a "working, buildable state." This becomes difficult in Phase 5 (Data Tables) because there are 12 data table usages across admin and public components. If Phase 5 migrates 6 of 12 tables and leaves 6 on Vuetify, the coexistence period extends. During this extended coexistence, the CSS conflict mitigation from Phase 0 must hold perfectly — any Tailwind v4 preflight update or Vuetify update could reintroduce conflicts.

Specifically, admin views like `AdminAnnotations.vue` and `AdminGeneStaging.vue` use `v-data-table` with complex cell templates that are tightly coupled to Vuetify-specific features (`:loading` slot, `@update:options` event, `density="compact"` prop). These cannot be migrated atomically.

**How to avoid:**
- In Phase 5, migrate the shared DataTable wrapper infrastructure first (non-breaking)
- Migrate tables one at a time, verifying each works before proceeding
- Add Vitest tests for each migrated table's server-side behavior before moving to the next
- Keep the phase exit criteria as "all tables in the phase work" not "all tables in the app work"

**Warning signs:**
- Phase 5 PR has 12 files changed simultaneously (red flag: too large)
- Untested tables left in partially-migrated state

**Phase to address:** Phase 5

---

## Technical Debt Patterns

| Shortcut | Immediate Benefit | Long-term Cost | When Acceptable |
|----------|-------------------|----------------|-----------------|
| Using `as any` for API response typing | Faster TypeScript migration | No type safety for API calls; runtime errors not caught | Never — create proper interfaces instead |
| Keeping `<script>` (no `lang="ts"`) on untouched components | Skip migration of non-blocking components | Mixed codebase is harder to maintain; IDE loses type checking | Acceptable for D3/Cytoscape wrapper components migrated in Phase 7 |
| Using Tailwind `prefix(tw)` instead of `@layer` for coexistence | Eliminates all CSS conflicts instantly | Every shadcn-vue component template needs `tw:` prefix; significant code bloat | Only if `@layer` approach has irresolvable conflicts |
| Deferring `withDefaults()` for props | Faster component migration | Runtime warnings for missing required props | Never for production components |
| Skipping Vitest for admin table components | Faster Phase 6 | Hard to verify server pagination correctness; regressions hard to detect | Acceptable if manual E2E testing is thorough, but add tests in Phase 8 |
| Using `//  @ts-ignore` to suppress errors | Unblocks migration of a specific file | Masks real type errors; accumulates technical debt | Only as a temporary measure with a TODO comment for resolution |
| Keeping MDI icons via CDN for unmapped icons | Zero time spent on icon gaps | CDN dependency; icon mismatch between MDI and Lucide visual styles | Unacceptable — creates visual inconsistency |

---

## CSS Coexistence Gotchas

### The Core Problem: Vuetify Is Unlayered
Vuetify 3's CSS ships without any `@layer` declarations. In the CSS cascade, unlayered styles have higher specificity than layered styles. This means any Tailwind utility inside `@layer utilities` loses to any Vuetify rule in the same specificity contest.

**Solution verified to work for Vuetify + Tailwind v4:**
```css
/* Declare layer order: theme < base < vuetify < components < utilities */
@layer theme, base, vuetify, components, utilities;

/* Import Tailwind layers explicitly */
@import "tailwindcss/theme.css" layer(theme);
@import "tailwindcss/preflight.css" layer(base);

/* Wrap Vuetify into the vuetify layer — now below utilities */
@import "vuetify/styles" layer(vuetify);

/* Tailwind utilities come last and win over everything */
@import "tailwindcss/utilities.css" layer(utilities);
```

**Critical: This CSS must be in a single file.** Splitting the Tailwind imports across multiple CSS files (e.g., having `@import "tailwindcss"` in both `tailwind.css` and a component's `<style>`) causes duplicate layer declarations, breaking cascade order. See [issue #16517](https://github.com/tailwindlabs/tailwindcss/discussions/16517).

### Vuetify Global CSS Classes That Conflict With Tailwind Utilities

Vuetify adds global utility classes that share names with Tailwind:
- `.d-flex` (Vuetify) conflicts with nothing directly, but during coexistence adds ambiguity
- `.elevation-N` (Vuetify) may conflict with `shadow-*` if applied to the same element
- Vuetify's `text-body-2`, `text-caption` etc. conflict with Tailwind's `text-*` size utilities

**Prevention:** When an element is being migrated from Vuetify to Tailwind, remove ALL Vuetify utility classes from it simultaneously. Never leave an element with mixed Vuetify + Tailwind utility classes — the cascade behavior is unpredictable.

### shadcn-vue CSS Variables and Vuetify CSS Variables: No Direct Name Conflicts
Vuetify uses `--v-theme-*` prefix. shadcn-vue uses unprefixed names like `--background`, `--foreground`, `--primary`. These do not collide by name. However:

- Vuetify sets `--v-theme-primary: 14,165,233` (RGB values, space-separated, no color function)
- shadcn-vue sets `--primary: 199 89% 48%` (HSL values for `hsl()` wrapper)
- If any component reads `var(--primary)` and Vuetify happens to define a `--primary` variable at a different scope, the values would be incompatible

**Prevention:** Check the browser DevTools for any `--primary` or `--background` variables defined by Vuetify on `:root`. Vuetify's variables all start with `--v-`, so actual name collision is unlikely but not impossible with custom Vuetify themes.

### The `@mdi/font` CSS Global Glyph Map
Currently `@mdi/font/css/materialdesignicons.css` is imported in `src/plugins/vuetify.js`. This adds ~250KB of CSS and a global `.mdi` class with icon glyph mappings. This file must stay until Phase 8. It does not conflict with Tailwind, but it inflates the CSS bundle during the entire migration period.

---

## Performance Traps

| Trap | Symptoms | Prevention | When It Breaks |
|------|----------|------------|----------------|
| TanStack Table re-renders on every parent state change | Table flickers on any state update; high CPU in DevTools profiler | Use `computed()` for stable column definitions; avoid defining `columns` inside the template | Phase 5 when first implementing DataTable |
| Importing all Lucide icons globally | +500KB JS bundle; slow initial load | Always use named imports: `import { Dna, Search } from 'lucide-vue-next'` — never `import * as LucideIcons` | Phase 2 if shortcut taken during icon setup |
| D3/Cytoscape components receiving Tailwind CSS resets | Visualization SVG elements lose computed styles; charts render with wrong dimensions | D3/Cytoscape components use direct DOM manipulation; wrap them in a container with `@layer components` isolation or specific CSS resets | Phase 7 if preflight bleeds into SVG elements |
| Duplicate Tailwind imports in component `<style>` blocks | Build warnings; duplicate CSS in output; layer order broken | Never use `@import "tailwindcss"` inside `<style>` blocks; the `@tailwindcss/vite` plugin handles this at build time | Phase 0 if setup is misunderstood |
| vue-tsc running on all files for every save | VS Code freezes; type checking takes 30+ seconds | Configure `vue-tsc` to check only changed files; use `.vscode/settings.json` `"typescript.tsdk"` to point to the project's TS | Phase 1 after strict mode is enabled |
| Loading all 73 components in Vitest without proper mocking | Slow test suite; Axios calls made during tests | Mock API modules in `vitest.config.ts` global setup; use `vi.mock('@/api/genes')` | When tests are first added |

---

## "Looks Done But Isn't" Checklist

These are the failure modes that pass visual inspection but break under specific conditions:

- [ ] **Dark mode toggle**: Only tested in light→dark direction — verify dark→light also works for all migrated components
- [ ] **Server-side pagination**: Test navigation to page 3, apply a filter, verify page resets to 1
- [ ] **Server-side sorting**: Verify sort direction cycle (asc → desc → none) triggers correct API calls, especially when combined with active filters
- [ ] **Form validation**: Verify that empty required fields show validation errors on submit (not just on blur)
- [ ] **Icon rendering**: Verify every migrated component's icons in both light AND dark mode (some icons use `currentColor` which changes with theme)
- [ ] **TypeScript build**: `npm run build` passes but `vue-tsc --noEmit` may still report errors — run both
- [ ] **Mobile responsive**: Tailwind's `grid` and `flex` replacements for `v-row`/`v-col` need explicit breakpoint classes; verify at 320px, 768px, and 1280px
- [ ] **URL state persistence**: `GeneTable.vue` syncs filters/pagination to URL query params; verify this survives the TanStack Table migration
- [ ] **Tooltip accessibility**: Verify Radix/Reka Tooltip works with keyboard navigation (the ARIA attributes differ from Vuetify tooltips)
- [ ] **scoped styles after migration**: After migrating a component's template, verify its `<style scoped>` block no longer references any `--v-theme-*` variables
- [ ] **Bundle size**: Confirm `@mdi/font` is not in the final bundle after Phase 8 (it's ~250KB); check with `npm run build -- --report`
- [ ] **WebSocket reconnection**: `services/websocket.ts` uses real-time updates for pipeline progress; verify it works after TypeScript migration (event type changes)
- [ ] **AdminLogViewer dark mode styles**: This component has hardcoded `.v-theme--dark` CSS selectors — verify these are replaced before Phase 8

---

## Pitfall-to-Phase Mapping

| Pitfall | Prevention Phase | Verification |
|---------|------------------|--------------|
| Tailwind preflight destroys Vuetify components | Phase 0 | Both Vuetify and Tailwind classes render correctly on test page |
| `important` config option removed in v4 | Phase 0 | No `tailwind.config.js` in repo; `@theme` in CSS only |
| shadcn-vue v1 uses Reka UI (not Radix Vue) | Phase 0 | `components.json` has correct schema URL; imports from `reka-ui` |
| `--v-theme-*` scoped styles silently break | Phases 2-7 (per component) + Phase 8 audit | `grep -rn "v-theme" frontend/src/ --include="*.vue"` returns 0 results |
| TanStack pageIndex not resetting on filter change | Phase 5 | Manual test: navigate to page 3, change filter, verify reset to page 1 |
| TanStack requires `rowCount` or `pageCount` | Phase 5 | Pagination shows correct total; "next" disabled on last page |
| TypeScript strict mode errors | Phase 1 (bulk), Phases 2-7 (ongoing) | `vue-tsc --noEmit` exits 0 |
| 193 icons, ~30-40 without Lucide equivalents | Phase 0 (audit), Phase 2 (registry) | `grep -rn "mdi-" frontend/src/` returns 0 results after Phase 8 |
| Dark mode dual system (Vuetify + shadcn-vue) | Phase 2 (sync), Phase 8 (remove Vuetify) | Theme toggle affects both old and new components simultaneously |
| TanStack custom cell renderers (no slots) | Phase 5 | All cell types render correctly; no blank cells |
| vee-validate computed schema loses types | Phases 2, 6 | Form submit handler receives correctly typed values |
| Vitest config not inheriting Vite config | Phase 1 | `npm run test` passes with path aliases and CSS imports |
| `@theme inline` missing for shadcn-vue vars | Phase 0 | `bg-background` and `text-foreground` utilities apply correct colors |
| Working state requirement in large phases | Phase 5 (split tables) | Each table migrated individually; no "half-done" tables in a PR |

---

## Sources

**Tailwind CSS v4:**
- [Tailwind CSS v4.0 announcement](https://tailwindcss.com/blog/tailwindcss-v4) — CSS-first config, OKLCH colors, no `important` option
- [Tailwind v4 has no `important` option support](https://github.com/tailwindlabs/tailwindcss/discussions/15866) — confirmed removal
- [Adding a custom prefix for Tailwind v4](https://github.com/tailwindlabs/tailwindcss/discussions/16046) — `prefix(tw)` syntax (no hyphens)
- [Disabling Preflight on Tailwind v4](https://github.com/tailwindlabs/tailwindcss/discussions/17481) — selective import approach
- [Upgrading to Tailwind v4: Missing Defaults, Broken Dark Mode](https://github.com/tailwindlabs/tailwindcss/discussions/16517) — duplicate import issue
- [Tailwind v4 issue: @layer component order change](https://github.com/tailwindlabs/tailwindcss/issues/16104) — layer behavior change from v3

**Vuetify + Tailwind Coexistence:**
- [How to solve style conflicts between Vuetify and TailwindCSS](https://github.com/vuetifyjs/vuetify/discussions/21241) — `@layer vuetify` wrapping solution (MEDIUM confidence — community discussion, not official doc)
- [tailwindcss-scoped-preflight plugin](https://github.com/Roman86/tailwindcss-scoped-preflight) — alternative scoped preflight approach

**shadcn-vue:**
- [shadcn-vue Changelog](https://www.shadcn-vue.com/docs/changelog) — v1 release with Reka UI switch (February 2025)
- [shadcn-vue v3 docs (Radix-based)](https://v3.shadcn-vue.com/docs/installation/vite) — OLD version, kept for reference
- [shadcn-ui Tailwind v4 guide](https://ui.shadcn.com/docs/tailwind-v4) — `@theme inline` usage, OKLCH migration

**TanStack Table:**
- [TanStack Table Pagination Guide](https://tanstack.com/table/v8/docs/guide/pagination) — `manualPagination`, `rowCount`, `autoResetPageIndex`
- [TanStack Table Pagination APIs](https://tanstack.com/table/v8/docs/api/features/pagination) — `pageCount` vs `rowCount` distinction
- [Issue #4797: pageIndex not resetting with manualPagination + manualFiltering](https://github.com/TanStack/table/issues/4797) — documented bug and workaround
- [Table State (Vue) Guide](https://tanstack.com/table/v8/docs/framework/vue/guide/table-state) — Vue-specific state management patterns

**vee-validate + Zod:**
- [vee-validate Zod Schema Validation](https://vee-validate.logaretm.com/v4/integrations/zod-schema-validation/) — `toTypedSchema` usage
- [Issue #4588: computed schema loses typing](https://github.com/logaretm/vee-validate/issues/4588) — confirmed bug
- [Issue #5078: Form @submit type inference issue](https://github.com/logaretm/vee-validate/issues/5078) — confirmed limitation

**Vue 3 TypeScript:**
- [Using Vue with TypeScript](https://vuejs.org/guide/typescript/overview.html) — official guide for SFC TypeScript
- [TypeScript with Composition API](https://vuejs.org/guide/typescript/composition-api) — `defineProps` generic inference and `withDefaults`

**Icon Research:**
- [Lucide Vue Next](https://lucide.dev/guide/packages/lucide-vue-next) — installation and named imports
- [Lucide Icons](https://lucide.dev/icons/) — complete icon listing

---

*Pitfalls research for: Frontend migration (Vuetify 3 → TypeScript + Tailwind CSS v4 + shadcn-vue)*
*Researched: 2026-02-28*
