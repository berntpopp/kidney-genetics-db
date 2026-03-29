# Mobile Accessibility & Responsiveness Audit Report

**Date:** 2026-03-29
**Resolution tested:** 375x667px (iPhone SE / standard mobile)
**Modes tested:** Light mode & Dark mode
**Tools used:** Playwright (visual inspection), Google Lighthouse (automated audit)
**Pages audited:** 10 (Home, Genes, Gene Detail, Dashboard x3 tabs, About, Data Sources, Network Analysis, FAQ, Login, Forgot Password, 404)

---

## Executive Summary

The KGDB frontend has significant mobile responsiveness and dark mode accessibility issues that prevent effective use on mobile devices. The most critical problems are:

1. **Dashboard charts are unusable on mobile** - shows "Screen too narrow" or broken chart renders
2. **Dark mode navigation menu has near-invisible text** - Login text and close button barely visible
3. **Persistent footer overlaps page content** across nearly every page
4. **Network Analysis form controls overflow the viewport** - STRING/Algorithm fields off-screen
5. **Contrast failures on 4 of 8 pages** (Lighthouse), with badge/label text below WCAG AA ratio
6. **Multiple buttons lack accessible names** (screen reader unusable)

---

## Lighthouse Scores Summary

| Page | Performance | Accessibility | Best Practices | SEO |
|------|:-----------:|:-------------:|:--------------:|:---:|
| Home | 55 | **100** | 100 | 100 |
| Genes | 53 | 95 | 100 | 100 |
| Gene Detail | *(not audited - requires dynamic route)* | | | |
| Dashboard | 54 | **90** | 100 | 100 |
| Data Sources | **38** | 95 | 100 | 100 |
| Network Analysis | 53 | **91** | 100 | 100 |
| About | 55 | 93 | 100 | 100 |
| FAQ | 54 | **100** | 100 | 100 |
| Login | 55 | 95 | 100 | 66 |

**Note:** Performance scores are affected by dev server (Vite) + Lighthouse CPU/network throttling. Production scores should be significantly better. The accessibility and SEO scores are the actionable items.

### Core Web Vitals (Mobile Throttled)

| Page | FCP | LCP | TBT | CLS |
|------|-----|-----|-----|-----|
| Home | 18.5s | 35.6s | 86ms | 0.000 |
| Data Sources | 18.8s | 36.5s | 99ms | **0.336** |
| Network Analysis | 21.7s | 42.0s | 173ms | 0.000 |

**CLS 0.336 on Data Sources** is a significant layout shift issue (threshold: good < 0.1).

---

## Critical Issues (P0 - Must Fix)

### 1. Dark Mode Navigation Menu - Near-Invisible Text
**Pages affected:** All (global component)
**Screenshot:** `screenshots/menu-open-dark.png`

The mobile hamburger menu in dark mode has critical contrast failures:
- "Login" text is nearly invisible (dark text on dark background)
- The close "X" button is barely visible
- Menu background doesn't fully opaque the underlying content, creating visual noise

**Root cause:** The mobile menu uses a `SheetContent` (Radix UI dialog-based) component in `src/layouts/AppHeader.vue`. Menu items use `text-muted-foreground` for inactive items which maps to `oklch(0.705 0.015 286.067)` in dark mode — this gives insufficient contrast against the dark card background `oklch(0.179 0.006 285.885)`. The "Login" button at the top is particularly bad.

**File:** `frontend/src/layouts/AppHeader.vue`

**Fix:**
- Change inactive menu item text from `text-muted-foreground` to `text-foreground` or a lighter muted variant
- Ensure the `SheetContent` background explicitly sets `bg-background` in dark mode
- Add `aria-describedby` to the `SheetContent` (console warning already fires about this)

### 2. Dashboard "Screen Too Narrow" - Charts Unusable on Mobile
**Pages affected:** `/dashboard` (all tabs)
**Screenshots:** `screenshots/dashboard-light.png`, `screenshots/dashboard-composition-light.png`, `screenshots/dashboard-distributions-light.png`

The UpSet plot (Gene Source Overlaps tab) shows "Screen too narrow - Please rotate to landscape or use a larger screen" instead of rendering. The Composition and Distribution tabs show:
- Charts rendering below the viewport with empty whitespace
- "classification_donut" raw text visible instead of actual chart on distributions tab
- Container heights too small for chart content

**Root cause:** `frontend/src/components/visualizations/UpSetChart.vue` line 415-426 has a hardcoded check: `if (containerWidth < 400)` that displays the "Screen too narrow" message. The dashboard container with padding gives only ~320-340px on a 375px screen, always triggering this block.

**File:** `frontend/src/components/visualizations/UpSetChart.vue` (line 415)

**Fix:**
- Lower the minimum width threshold or remove it entirely
- Replace with a mobile-friendly alternative visualization (simplified horizontal bar chart, summary table, or stacked bars)
- Set minimum chart container heights that account for mobile viewports
- For the UpSet plot specifically, consider a mobile-friendly matrix/heatmap representation
- Ensure chart text/labels are human-readable — `classification_donut` (raw visualization type name) should never be shown to users

### 3. Footer Overlapping Content
**Pages affected:** Nearly all pages
**Screenshots:** Visible in `screenshots/gene-detail-light.png`, `screenshots/faq-light.png`, `screenshots/data-sources-light.png`, etc.

The fixed footer bar (`position: fixed; bottom: 0; z-index: 40; height: 2rem`) overlaps page content. The main content area in `App.vue` already has `pb-16` (64px), but this is insufficient in some cases — particularly on pages with scroll-dependent content or when the footer's semi-transparent background (`bg-background/95 backdrop-blur-sm`) makes overlapped content hard to read.

**File:** `frontend/src/layouts/AppFooter.vue` (footer), `frontend/src/App.vue` (main padding)

**Fix:**
- Increase `pb-16` to `pb-20` or use CSS variable `padding-bottom: calc(var(--footer-height) + 1rem)`
- Add `scroll-padding-bottom` to `html` element to prevent focused elements from being obscured (WCAG 2.4.11)
- Consider making the footer non-sticky on mobile: use `@media (max-width: 768px) { position: relative; }` or hide in production
- Add `env(safe-area-inset-bottom)` for notched devices

### 4. Network Analysis Form Overflow
**Pages affected:** `/network-analysis`
**Screenshots:** `screenshots/network-analysis-light.png`, `screenshots/network-analysis-dark.png`

The filter controls use a fixed CSS grid: `grid-cols-[minmax(160px,280px)_auto_auto_auto_auto]` which requires ~600px+ for all inputs inline. Individual input widths are hardcoded (`w-24` = 96px for STRING, `w-40` = 160px for Algorithm). On a 375px screen with padding, only ~328px is available, causing massive overflow.

**File:** `frontend/src/views/NetworkAnalysis.vue` (lines 49-126)

**Fix:**
- Replace the fixed grid with a responsive layout: `grid grid-cols-2 sm:grid-cols-3 lg:grid-cols-5 gap-3`
- Remove fixed width classes (`w-24`, `w-40`) and let inputs fill their grid cells with `w-full`
- Add `overflow-hidden` to the parent container to prevent horizontal page scroll
- Consider collapsing filters into an expandable panel on mobile

---

## High Issues (P1 - Should Fix)

### 5. Contrast Ratio Failures (WCAG AA)
**Pages affected:** About, Dashboard, Data Sources, Network Analysis
**Lighthouse audit:** "Background and foreground colors do not have a sufficient contrast ratio"

Specific failing elements:
- **Badge components** (tier badges): `inline-flex items-center rounded-full border` - colored badges with text below 4.5:1 contrast ratio
- **Network Analysis labels**: `text-xs font-medium text-muted-foreground` - labels like "Evidence Tiers", "Min Score" etc. use `text-muted-foreground` which has insufficient contrast
- **Input placeholder text**: `placeholder:text-muted-foreground` - placeholder text too light
- **Select trigger values**: Text inside select dropdowns

**WCAG 2.2 AA Requirements:**
- Normal text (< 18px / < 14px bold): 4.5:1 minimum contrast ratio
- Large text (>= 18px / >= 14px bold): 3:1 minimum contrast ratio
- UI components and graphical objects: 3:1 minimum

**Fix:**
- Increase `--muted-foreground` HSL lightness in the CSS custom properties
- For tier badges, ensure text color meets 4.5:1 against the badge background
- Replace `text-muted-foreground` on form labels with `text-foreground` or a medium-contrast alternative
- Test all color combinations with a contrast checker tool

### 6. Buttons Without Accessible Names
**Pages affected:** Genes, Dashboard, Login, Network Analysis
**Lighthouse audit:** "Buttons do not have an accessible name"

Specific failing elements:
- **Source filter remove buttons** (Dashboard): `<button class="ml-1 rounded-full hover:bg-destructive/20">` - icon-only buttons to remove source filters have no aria-label
- **Icon-only toolbar buttons** (Genes): download, filter, reset buttons with only SVG icons
- **Select triggers** (Genes, Network): `<button data-slot="select-trigger">` missing accessible name
- **Password visibility toggle** (Login): icon-only button

**Fix:**
- Add `aria-label="Remove [source name]"` to all source filter remove buttons
- Add `aria-label` to all icon-only buttons (e.g., `aria-label="Download CSV"`, `aria-label="Toggle filters"`, `aria-label="Reset filters"`)
- Ensure select triggers have associated labels via `aria-labelledby` or wrapping `<label>` elements
- Add `aria-label="Toggle password visibility"` to the password eye button

### 7. Gene Browser Table Columns Truncated
**Pages affected:** `/genes`
**Screenshots:** `screenshots/genes-light.png`, `screenshots/genes-dark.png`

The table shows Gene, HGNC ID, Tier columns but the Evidence Score column is completely cut off. Tier badges are truncated ("Comprehensive Supp..."). The table has fixed pixel column sizes totaling 750px minimum (Gene: 140px, HGNC ID: 110px, Tier: 100px, Evidence Count: 100px, Score: 100px, Sources: 200px). All cells use `whitespace-nowrap` preventing text wrapping.

**Files:** `frontend/src/components/GeneTable.vue` (columns), `frontend/src/components/ui/table/TableCell.vue` (nowrap)

**Fix options (pick one or combine):**
- **Column prioritization**: Use TanStack Table's `column.toggleVisibility(false)` at mobile breakpoints via `useMediaQuery` — hide HGNC ID and Sources columns on mobile, show Gene + Tier + Score only
- **Responsive card layout**: Convert table rows to card layout on mobile (`@media (max-width: 640px)`)
- **Horizontal scroll with sticky first column**: Keep the Gene column sticky-left so users always see which gene they're looking at while scrolling
- **Abbreviate tier names on mobile**: "Comprehensive Support" -> "Comp." or use icon + tooltip

### 8. Dashboard Tab Bar Overflow
**Pages affected:** `/dashboard`
**Screenshots:** `screenshots/dashboard-light.png`

The three tabs ("Gene Source Overlaps", "Source Distributions", "Evidence Composition") overflow horizontally. The full text doesn't fit on mobile.

**Fix:**
- Use `overflow-x-auto` on the tab container with `whitespace-nowrap`
- Abbreviate tab labels on mobile: "Overlaps", "Distributions", "Composition"
- Or use icon + short label pattern at mobile breakpoint

---

## Medium Issues (P2 - Nice to Fix)

### 9. Heading Order (Dashboard, Data Sources)
**Lighthouse:** "Heading elements are not in a sequentially-descending order"

Headings skip levels (e.g., h1 -> h3 without h2), which confuses screen readers.

**Fix:** Ensure proper heading hierarchy: h1 -> h2 -> h3 in sequential order.

### 10. Links Rely on Color Alone (About page)
**Lighthouse:** "Links rely on color to be distinguishable"

Links within text blocks on the About page are only distinguishable by color, not by underline or other visual indicator.

**Fix:** Add `underline` or `underline-offset-4` to inline text links, or use a distinct style like bold + color.

### 11. Data Sources Layout Shift (CLS 0.336)
**Pages affected:** `/data-sources`

Large CLS caused by data loading - placeholder content shifts when real data arrives.

**Fix:**
- Add skeleton/placeholder cards with fixed dimensions matching loaded content
- Reserve space for the "Database Summary" section with min-height
- Use `aspect-ratio` or fixed heights on card containers

### 12. Gene Detail Page - Action Buttons Cramped
**Pages affected:** `/genes/:symbol`
**Screenshots:** `screenshots/gene-detail-light.png`

The "Save", "Share", "Export" buttons and the back arrow are cramped together with the gene symbol, causing awkward text wrapping ("Gene information" wraps to next line).

**Fix:**
- Stack action buttons below the gene symbol on mobile
- Use an overflow menu (three dots) for secondary actions
- Move back arrow to breadcrumb navigation

### 13. Footer Developer Toolbar
**Pages affected:** All pages

The footer contains developer-oriented controls (v0.2.0, WebSocket indicator, various icon buttons) that:
- Take up valuable screen real estate on mobile
- Have small tap targets (icon buttons)
- May confuse end users

**Fix:**
- Hide the developer toolbar in production builds (behind `import.meta.env.DEV`)
- Or collapse to a single toggle button that expands the toolbar
- Ensure all footer icon buttons meet 44x44px touch target minimum

### 14. Login Page Missing autocomplete Attributes
**Lighthouse console warning:** "Input elements should have autocomplete attributes"

The login form inputs lack `autocomplete` attributes which help password managers and improve mobile UX.

**Fix:**
- Username field: `autocomplete="username"`
- Password field: `autocomplete="current-password"`

### 15. Dialog Missing aria-describedby
**Console warning:** "Missing Description or aria-describedby on DialogContent"

The mobile menu dialog component is missing required ARIA attributes.

**Fix:** Add `aria-describedby` to the `DialogContent` component or provide a `DialogDescription`.

---

## Low Issues (P3 - Consider)

### 16. 404 Dark Mode - Low Contrast Text
The "Page not found" and description text uses a low-contrast gray that's harder to read in dark mode.

### 17. Home Page - Source Icons Wrap Unpredictably
The data source icons row (PanelApp, ClinGen, etc.) wraps at mobile widths, with icon sizes potentially too small for touch targets.

### 18. Login SEO Score (66)
Login page is blocked from indexing (intentional, not an issue) but Lighthouse flags it. This is expected behavior.

---

## Best Practices Recommendations

### Mobile-First Responsive Design
1. **Use CSS Container Queries** for component-level responsiveness instead of only media queries
2. **Test at 320px minimum** (iPhone 5/SE first generation) - some users still use small devices
3. **Touch targets: minimum 44x44 CSS pixels** (WCAG 2.2 SC 2.5.8) for all interactive elements
4. **Avoid horizontal scroll on the page level** - only within specific containers like tables

### Dark Mode
1. **Don't use pure black (#000)** - use `hsl(0 0% 3.9%)` or similar (already done in CSS vars)
2. **Test every component** in dark mode separately - common issue is components inheriting light-mode-only colors
3. **Ensure 4.5:1 contrast minimum** for all text in both modes
4. **Use `prefers-color-scheme` media query** as default, with manual override

### Charts on Mobile
1. **Never block with "screen too narrow"** - always provide an alternative view
2. **Simplified mobile visualizations**: bar charts instead of complex plots, summary stats instead of full charts
3. **Lazy-load chart libraries** to improve mobile performance
4. **Provide data tables as alternative** to all charts (accessibility requirement)

### Data Tables on Mobile
1. **Card-based layout below 640px** - each row becomes a card with label-value pairs
2. **Column priority system** - define which columns are essential, secondary, optional
3. **Progressive disclosure** - show key info, expand for details

### Navigation
1. **Focus trap in mobile menu** - pressing Tab should cycle within the menu
2. **Close on Escape key** - already good if using Radix/reka-ui
3. **Full-width touch targets** for menu items (not just the text)
4. **Animated transitions** for menu open/close for perceived performance

### Performance
1. **Code-split route components** (already using lazy loading, good)
2. **Preload critical fonts**
3. **Optimize images** - use WebP/AVIF, proper `srcset` for responsive images
4. **Service worker** for offline capability and faster repeat visits

---

## Prioritized Action Plan

### Sprint 1 (Critical - blocks mobile usability)
- [ ] Fix dark mode navigation menu contrast
- [ ] Add padding-bottom to main content to clear footer
- [ ] Make network analysis form responsive (2-col grid on mobile)
- [ ] Replace dashboard "Screen too narrow" with mobile-friendly charts

### Sprint 2 (Accessibility compliance)
- [ ] Fix all contrast ratio failures (badge text, muted-foreground labels)
- [ ] Add aria-labels to all icon-only buttons
- [ ] Fix heading hierarchy (dashboard, data sources)
- [ ] Add autocomplete attributes to login form
- [ ] Fix dialog aria-describedby warning
- [ ] Add underline to inline text links (about page)

### Sprint 3 (Polish)
- [ ] Implement responsive table/card layout for gene browser on mobile
- [ ] Abbreviate dashboard tab labels on mobile
- [ ] Fix data sources CLS with skeleton loading
- [ ] Improve gene detail action button layout on mobile
- [ ] Consider hiding developer toolbar in production
- [ ] Fix 404 dark mode text contrast

---

## Files to Modify (Key Targets)

| Component | File | Issues |
|-----------|------|--------|
| Mobile nav/menu | `src/layouts/AppHeader.vue` | Dark mode contrast, aria-describedby, `text-muted-foreground` on menu items |
| App layout | `src/App.vue` | Footer padding (`pb-16` -> `pb-20`), `scroll-padding-bottom` |
| App footer | `src/layouts/AppFooter.vue` | Fixed position, `z-40`, `h-8`, production visibility |
| Network analysis | `src/views/NetworkAnalysis.vue` (L49-126) | Fixed grid `grid-cols-[minmax...]`, `w-24`/`w-40` overflow |
| UpSet chart | `src/components/visualizations/UpSetChart.vue` (L415) | `containerWidth < 400` hard block |
| Dashboard | `src/views/Dashboard.vue` | Tab overflow, chart container sizing |
| Gene table | `src/components/GeneTable.vue` (L104-222) | Fixed column `size` values, no responsive hiding |
| Table cell | `src/components/ui/table/TableCell.vue` | `whitespace-nowrap` preventing text wrap |
| CSS variables | `src/assets/main.css` | `--muted-foreground` OKLCH value needs higher lightness in dark mode |
| Badge component | `src/components/ui/badge/` | Text contrast in colored variants |
| Login form | `src/views/Login.vue` | `autocomplete` attrs, password toggle `aria-label` |
| Theme composable | `src/composables/useAppTheme.ts` | Dark mode toggle via `@vueuse/core` `useColorMode()` |

---

## Screenshots Index

### Light Mode
| Page | File |
|------|------|
| Home | `screenshots/home-light.png` |
| Genes | `screenshots/genes-light.png` |
| Gene Detail (PKD1) | `screenshots/gene-detail-light.png` |
| Dashboard - Overlaps | `screenshots/dashboard-light.png` |
| Dashboard - Composition | `screenshots/dashboard-composition-light.png` |
| Dashboard - Distributions | `screenshots/dashboard-distributions-light.png` |
| About | `screenshots/about-light.png` |
| Data Sources | `screenshots/data-sources-light.png` |
| Network Analysis | `screenshots/network-analysis-light.png` |
| FAQ | `screenshots/faq-light.png` |
| Login | `screenshots/login-light.png` |
| Forgot Password | `screenshots/forgot-password-light.png` |
| 404 | `screenshots/404-light.png` |
| Menu Open | `screenshots/menu-open-light.png` |

### Dark Mode
| Page | File |
|------|------|
| Home | `screenshots/home-dark.png` |
| Genes | `screenshots/genes-dark.png` |
| Gene Detail (PKD1) | `screenshots/gene-detail-dark.png` |
| Dashboard | `screenshots/dashboard-dark.png` |
| About | `screenshots/about-dark.png` |
| Data Sources | `screenshots/data-sources-dark.png` |
| Network Analysis | `screenshots/network-analysis-dark.png` |
| FAQ | `screenshots/faq-dark.png` |
| Login | `screenshots/login-dark.png` |
| 404 | `screenshots/404-dark.png` |
| Menu Open | `screenshots/menu-open-dark.png` |
