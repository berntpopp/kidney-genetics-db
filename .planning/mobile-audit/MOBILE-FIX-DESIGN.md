# Mobile Accessibility & WCAG AA Fix Design

**Date:** 2026-03-29
**Scope:** P0 (Critical) + P1 (High) issues from MOBILE-ACCESSIBILITY-AUDIT.md
**Approach:** Modular by shared concern (DRY), not by page

---

## Decisions

| Decision | Choice | Rationale |
|----------|--------|-----------|
| Scope | P0 + P1 (10 issues) | Covers usability blockers + WCAG AA compliance; defers cosmetic polish |
| Gene table mobile | Column hiding via TanStack | Least code, works with existing setup |
| UpSet chart mobile | Lower threshold + horizontal scroll | One-line change, chart already has overflow-x: auto |
| Footer mobile | Increase padding + hide dev toolbar | Fixes overlap and tap targets in one pass |
| Contrast fix | Global CSS variable bump | Consistent fix, minimal visual change |

---

## Module 1: Global CSS Contrast Fix

**File:** `frontend/src/assets/main.css`
**Issues resolved:** #5 (contrast failures)

Changes to CSS custom properties:
- Light mode `--muted-foreground`: `oklch(0.552 0.016 285.938)` -> `oklch(0.50 0.016 285.938)`
- Dark mode `--muted-foreground`: `oklch(0.705 0.015 286.067)` -> `oklch(0.75 0.015 286.067)`

This fixes contrast on: badge text, form labels (`text-muted-foreground`), input placeholders (`placeholder:text-muted-foreground`), select trigger values, and Network Analysis labels.

**Verification:** Run Lighthouse accessibility audit on Dashboard, About, Data Sources, Network Analysis pages. All should score 95+.

---

## Module 2: App Shell (Footer + Layout)

**Files:** `frontend/src/App.vue`, `frontend/src/layouts/AppFooter.vue`
**Issues resolved:** #3 (footer overlap), #13 (footer dev toolbar)

### App.vue
- Change `pb-16` to `pb-20` on `<main>` element
- Add to `<html>` element (via `main.css`): `scroll-padding-bottom: 5rem`

### AppFooter.vue
- Wrap dev toolbar controls (WebSocket indicator, log viewer button, debug icons) in `hidden md:flex` container
- Keep visible on mobile: version number, essential links (GitHub, FAQ)
- Add `pb-[env(safe-area-inset-bottom)]` to footer for notched devices

**Verification:** On 375px viewport, no content is obscured by footer on any page. Footer shows only essential info on mobile.

---

## Module 3: Navigation Dark Mode

**File:** `frontend/src/layouts/AppHeader.vue`
**Issues resolved:** #1 (dark mode nav contrast), #15 (dialog aria-describedby)

Changes:
- Mobile drawer nav items: change `text-muted-foreground` to `text-foreground` for inactive items
- Add explicit `bg-background` class to `SheetContent` component
- Add `<SheetDescription>` (or `aria-describedby`) to satisfy Radix dialog requirement

**Verification:** In dark mode at 375px, all menu items are clearly readable. No console warning about missing aria-describedby.

---

## Module 4: Network Analysis Responsive Form

**File:** `frontend/src/views/NetworkAnalysis.vue` (lines 49-126)
**Issues resolved:** #4 (form overflow)

Changes:
- Replace grid: `grid-cols-[minmax(160px,280px)_auto_auto_auto_auto]` -> `grid-cols-1 sm:grid-cols-2 lg:grid-cols-5`
- Remove fixed widths: `w-24`, `w-40` -> `w-full` on all inputs
- Add `overflow-hidden` on the filter form parent container
- Each field's `space-y-1` wrapper gets `w-full` to fill grid cells

**Verification:** At 375px, all form fields are visible and stacked vertically. No horizontal overflow.

---

## Module 5: Dashboard Mobile

**Files:** `frontend/src/components/visualizations/UpSetChart.vue`, `frontend/src/views/Dashboard.vue`
**Issues resolved:** #2 (charts unusable), #8 (tab overflow)

### UpSetChart.vue
- Change threshold: `containerWidth < 400` -> `containerWidth < 280`
- The existing `.upset-plot { overflow-x: auto; }` CSS handles horizontal scrolling

### Dashboard.vue
- Defensive check: ensure `visualizationType` values in `SourceDistributionsChart.vue` never render as raw text (add fallback for unmatched types)
- Add `overflow-x-auto` on `TabsList` container for horizontal scroll on narrow screens
- Optionally abbreviate tab labels on mobile using responsive text (full text hidden, short text shown below sm breakpoint)

**Verification:** At 375px, UpSet chart renders (scrollable) instead of "Screen too narrow". Tab bar is scrollable. No raw type names visible.

---

## Module 6: Gene Table Column Visibility

**File:** `frontend/src/components/GeneTable.vue`
**Issues resolved:** #7 (columns truncated)

Changes:
- Import `useMediaQuery` from `@vueuse/core`
- Create reactive `isMobile = useMediaQuery('(max-width: 640px)')`
- Watch `isMobile` and toggle column visibility:
  - Mobile: hide `hgnc_id` and `sources` columns
  - Desktop: show all columns
- Use TanStack Table's `column.toggleVisibility()` API

**Verification:** At 375px, table shows Gene + Tier + Evidence + Score. At 641px+, all columns visible.

---

## Module 7: Accessible Names (aria-labels)

**Files:** Multiple components
**Issues resolved:** #6 (buttons without accessible names)

Specific additions:
- `GeneTable.vue`: `aria-label="Download CSV"`, `aria-label="Toggle filters"`, `aria-label="Reset filters"` on icon-only toolbar buttons
- `Dashboard.vue`: `aria-label="Remove [source] filter"` on source filter remove buttons (dynamic label including source name)
- `Login.vue`: `aria-label="Toggle password visibility"` on eye/eye-off button
- `NetworkAnalysis.vue`: `aria-label` on select triggers, icon buttons
- All select triggers: ensure associated `<Label>` elements use `for` attribute or `aria-labelledby`

**Verification:** Lighthouse accessibility audit reports 0 "buttons without accessible name" findings.

---

## Module 8: Heading Hierarchy + Form Attributes + Link Styling

**Files:** `Dashboard.vue`, `DataSources.vue`, `Login.vue`, `About.vue`
**Issues resolved:** #9 (heading order), #10 (links rely on color), #14 (login autocomplete)

### Heading Hierarchy
- Audit heading levels in Dashboard and Data Sources views
- Fix any h1 -> h3 jumps by inserting h2 or demoting h3 to h2

### Login Form
- Add `autocomplete="username"` to username input
- Add `autocomplete="current-password"` to password input

### About Page Links
- Add `underline underline-offset-4` to inline text links (those within paragraph text, not button-styled links)

**Verification:** Lighthouse reports no heading order warnings. Login form autocomplete works with password managers. About page links distinguishable without color.

---

## Out of Scope (P2/P3, deferred)

- Card layout for gene table (#7 alternative approach)
- Data Sources CLS / skeleton loading (#11)
- Gene Detail action button layout (#12)
- 404 dark mode text contrast (#16)
- Home page source icon wrapping (#17)
- Login SEO score (#18)

---

## File Change Summary

| File | Modules | Type of Change |
|------|---------|----------------|
| `src/assets/main.css` | 1, 2 | CSS variable values, scroll-padding |
| `src/App.vue` | 2 | Padding class change |
| `src/layouts/AppFooter.vue` | 2 | Responsive visibility, safe-area |
| `src/layouts/AppHeader.vue` | 3 | Text classes, aria, bg class |
| `src/views/NetworkAnalysis.vue` | 4, 7 | Grid classes, widths, aria-labels |
| `src/components/visualizations/UpSetChart.vue` | 5 | Threshold value |
| `src/views/Dashboard.vue` | 5, 7, 8 | Tab overflow, aria-labels, headings |
| `src/components/GeneTable.vue` | 6, 7 | Column visibility, aria-labels |
| `src/views/Login.vue` | 7, 8 | aria-label, autocomplete attrs |
| `src/views/About.vue` | 8 | Link underlines |
| `src/views/DataSources.vue` | 8 | Heading hierarchy |
