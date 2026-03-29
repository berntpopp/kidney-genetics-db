# Mobile Accessibility & WCAG AA Fix — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Fix all P0 (critical) and P1 (high) mobile accessibility issues from the MOBILE-ACCESSIBILITY-AUDIT.md — 10 issues across 8 modules.

**Architecture:** Modular fixes grouped by shared concern (DRY). Each task is one module touching 1-3 files. No new components created — all changes are to existing files. CSS variable bump fixes contrast globally; remaining fixes are targeted class/attribute changes.

**Tech Stack:** Vue 3, Tailwind CSS v4 (OKLCH colors), shadcn-vue (reka-ui), TanStack Table, @vueuse/core

---

## File Map

| File | Changes |
|------|---------|
| `frontend/src/assets/main.css` | Bump `--muted-foreground` OKLCH values (light + dark), add `scroll-padding-bottom` |
| `frontend/src/App.vue` | Change `pb-16` → `pb-20` |
| `frontend/src/layouts/AppFooter.vue` | Hide dev controls on mobile, add safe-area inset |
| `frontend/src/layouts/AppHeader.vue` | Fix dark mode nav text, add `SheetDescription`, add `bg-background` |
| `frontend/src/views/NetworkAnalysis.vue` | Responsive grid, remove fixed widths, add aria-labels |
| `frontend/src/components/visualizations/UpSetChart.vue` | Lower min width threshold |
| `frontend/src/views/Dashboard.vue` | Tab overflow scroll, heading check |
| `frontend/src/components/GeneTable.vue` | Mobile column hiding, aria-labels on icon buttons |
| `frontend/src/views/Login.vue` | `autocomplete` attrs, password toggle aria-label |
| `frontend/src/views/About.vue` | Add underline to inline text links |
| `frontend/src/views/DataSources.vue` | Fix h1→h3 heading skip |
| `frontend/playwright.config.ts` | New — Playwright config for mobile testing |
| `frontend/e2e/mobile-accessibility.spec.ts` | New — E2E tests for all mobile fixes |
| `frontend/package.json` | Add test:e2e scripts |

---

### Task 1: Global CSS Contrast Fix

**Files:**
- Modify: `frontend/src/assets/main.css:37` (light `--muted-foreground`)
- Modify: `frontend/src/assets/main.css:102` (dark `--muted-foreground`)

Fixes audit issues: #5 (contrast ratio failures on badges, labels, placeholders across About, Dashboard, Data Sources, Network Analysis)

- [ ] **Step 1: Update light mode `--muted-foreground`**

In `frontend/src/assets/main.css`, line 37, change:
```css
--muted-foreground: oklch(0.552 0.016 285.938);
```
to:
```css
--muted-foreground: oklch(0.50 0.016 285.938);
```

- [ ] **Step 2: Update dark mode `--muted-foreground`**

In `frontend/src/assets/main.css`, line 102, change:
```css
--muted-foreground: oklch(0.705 0.015 286.067);
```
to:
```css
--muted-foreground: oklch(0.75 0.015 286.067);
```

- [ ] **Step 3: Add scroll-padding-bottom to html**

In `frontend/src/assets/main.css`, after the closing `}` of the `.dark` block (after line 139) and before the `@theme inline` section, add:

```css
  html {
    scroll-padding-bottom: 5rem;
  }
```

This should be added inside the `@layer theme` block, after the `.dark { ... }` closing brace.

- [ ] **Step 4: Verify build**

Run: `cd frontend && npm run build`
Expected: Build succeeds with no errors.

- [ ] **Step 5: Commit**

```bash
git add frontend/src/assets/main.css
git commit -m "fix(frontend): improve muted-foreground contrast for WCAG AA compliance

Bump --muted-foreground lightness: light 0.552→0.50, dark 0.705→0.75.
Add scroll-padding-bottom to html for footer clearance."
```

---

### Task 2: App Shell — Footer Padding + Mobile Dev Toolbar

**Files:**
- Modify: `frontend/src/App.vue:54`
- Modify: `frontend/src/layouts/AppFooter.vue:96-289`

Fixes audit issues: #3 (footer overlapping content), #13 (footer dev toolbar on mobile)

- [ ] **Step 1: Increase main content bottom padding**

In `frontend/src/App.vue`, line 54, change:
```html
<main class="flex-1 pb-16">
```
to:
```html
<main class="flex-1 pb-20">
```

- [ ] **Step 2: Add safe-area-inset to footer**

In `frontend/src/layouts/AppFooter.vue`, line 96, change:
```html
<footer class="fixed bottom-0 left-0 right-0 z-40 border-t bg-background/95 backdrop-blur-sm">
```
to:
```html
<footer class="fixed bottom-0 left-0 right-0 z-40 border-t bg-background/95 backdrop-blur-sm pb-[env(safe-area-inset-bottom)]">
```

- [ ] **Step 3: Hide dev-only controls on mobile — left side**

In `frontend/src/layouts/AppFooter.vue`, the left section (lines 99-157) contains the version popover, online indicator, and backend status. The version popover is useful on mobile, but the online/backend indicators are dev-focused.

Wrap the online and backend indicator tooltips in a `hidden md:flex` container. Change lines 129-156 from:
```html
          <!-- Online indicator -->
          <Tooltip>
            <TooltipTrigger as-child>
              <div class="flex items-center">
                <Wifi v-if="isOnline" class="size-3 text-green-500" />
                <WifiOff v-else class="size-3 text-destructive" />
              </div>
            </TooltipTrigger>
            <TooltipContent side="top">
              <p>{{ isOnline ? 'Online' : 'Offline — some features unavailable' }}</p>
            </TooltipContent>
          </Tooltip>

          <!-- Backend status -->
          <Tooltip>
            <TooltipTrigger as-child>
              <div class="flex items-center">
                <Server
                  class="size-3"
                  :class="backendReachable ? 'text-green-500' : 'text-destructive'"
                />
              </div>
            </TooltipTrigger>
            <TooltipContent side="top">
              <p>Backend: {{ backendReachable ? `v${backendVersion}` : 'unreachable' }}</p>
            </TooltipContent>
          </Tooltip>
```
to:
```html
          <!-- Online + Backend indicators (hidden on mobile) -->
          <div class="hidden md:flex items-center gap-1.5">
            <Tooltip>
              <TooltipTrigger as-child>
                <div class="flex items-center">
                  <Wifi v-if="isOnline" class="size-3 text-green-500" />
                  <WifiOff v-else class="size-3 text-destructive" />
                </div>
              </TooltipTrigger>
              <TooltipContent side="top">
                <p>{{ isOnline ? 'Online' : 'Offline — some features unavailable' }}</p>
              </TooltipContent>
            </Tooltip>

            <Tooltip>
              <TooltipTrigger as-child>
                <div class="flex items-center">
                  <Server
                    class="size-3"
                    :class="backendReachable ? 'text-green-500' : 'text-destructive'"
                  />
                </div>
              </TooltipTrigger>
              <TooltipContent side="top">
                <p>Backend: {{ backendReachable ? `v${backendVersion}` : 'unreachable' }}</p>
              </TooltipContent>
            </Tooltip>
          </div>
```

- [ ] **Step 4: Hide dev-only controls on mobile — right side**

In the right section (lines 160-288), wrap the docs, license, issues, separator, disclaimer, and log viewer controls (everything after GitHub and FAQ) in `hidden md:flex`. Change from:

```html
      <div class="flex items-center gap-0.5">
        <TooltipProvider :delay-duration="300">
          <!-- GitHub -->
          ...
          <!-- Docs -->
          ...
          <!-- License -->
          ...
          <!-- FAQ -->
          ...
          <!-- Issues -->
          ...
          <Separator orientation="vertical" class="h-4 mx-0.5" />
          <!-- Disclaimer -->
          ...
          <!-- Log Viewer -->
          ...
        </TooltipProvider>
      </div>
```

To keep this surgical, wrap only the Docs, License, Issues, Separator, Disclaimer, and Log Viewer in a `hidden md:flex` div. Keep GitHub and FAQ visible on mobile since they're essential links. The restructured right section should be:

```html
      <div class="flex items-center gap-0.5">
        <TooltipProvider :delay-duration="300">
          <!-- GitHub (always visible) -->
          <Tooltip>
            <TooltipTrigger as-child>
              <Button variant="ghost" size="icon" class="size-6" as-child>
                <a
                  :href="GITHUB_URL"
                  target="_blank"
                  rel="noopener noreferrer"
                  aria-label="GitHub Repository"
                >
                  <Github class="size-3.5" />
                </a>
              </Button>
            </TooltipTrigger>
            <TooltipContent side="top"><p>GitHub Repository</p></TooltipContent>
          </Tooltip>

          <!-- FAQ (always visible) -->
          <Tooltip>
            <TooltipTrigger as-child>
              <Button variant="ghost" size="icon" class="size-6" as-child>
                <RouterLink to="/faq" aria-label="FAQ">
                  <HelpCircle class="size-3.5" />
                </RouterLink>
              </Button>
            </TooltipTrigger>
            <TooltipContent side="top"><p>FAQ</p></TooltipContent>
          </Tooltip>

          <!-- Desktop-only controls -->
          <div class="hidden md:flex items-center gap-0.5">
            <!-- Docs -->
            <Tooltip>
              <TooltipTrigger as-child>
                <Button variant="ghost" size="icon" class="size-6" as-child>
                  <a
                    :href="`${GITHUB_URL}#readme`"
                    target="_blank"
                    rel="noopener noreferrer"
                    aria-label="Documentation"
                  >
                    <BookOpen class="size-3.5" />
                  </a>
                </Button>
              </TooltipTrigger>
              <TooltipContent side="top"><p>Documentation</p></TooltipContent>
            </Tooltip>

            <!-- License -->
            <Tooltip>
              <TooltipTrigger as-child>
                <Button variant="ghost" size="icon" class="size-6" as-child>
                  <a
                    :href="`${GITHUB_URL}/blob/main/LICENSE`"
                    target="_blank"
                    rel="noopener noreferrer"
                    aria-label="License"
                  >
                    <Scale class="size-3.5" />
                  </a>
                </Button>
              </TooltipTrigger>
              <TooltipContent side="top"><p>License</p></TooltipContent>
            </Tooltip>

            <!-- Issues -->
            <Tooltip>
              <TooltipTrigger as-child>
                <Button variant="ghost" size="icon" class="size-6" as-child>
                  <a
                    :href="`${GITHUB_URL}/issues`"
                    target="_blank"
                    rel="noopener noreferrer"
                    aria-label="Issues"
                  >
                    <CircleAlert class="size-3.5" />
                  </a>
                </Button>
              </TooltipTrigger>
              <TooltipContent side="top"><p>Issues</p></TooltipContent>
            </Tooltip>

            <Separator orientation="vertical" class="h-4 mx-0.5" />

            <!-- Disclaimer -->
            <Tooltip>
              <TooltipTrigger as-child>
                <Button
                  variant="ghost"
                  size="icon"
                  class="size-6"
                  :class="disclaimerAcknowledged ? 'text-green-600' : 'text-amber-500'"
                  :aria-label="disclaimerAcknowledged ? 'Disclaimer acknowledged' : 'View disclaimer'"
                  @click="disclaimerOpen = true"
                >
                  <ShieldCheck v-if="disclaimerAcknowledged" class="size-3.5" />
                  <ShieldAlert v-else class="size-3.5" />
                </Button>
              </TooltipTrigger>
              <TooltipContent side="top">
                <p>{{ disclaimerAcknowledged ? 'Disclaimer acknowledged' : 'View disclaimer' }}</p>
              </TooltipContent>
            </Tooltip>

            <!-- Log Viewer -->
            <Tooltip>
              <TooltipTrigger as-child>
                <Button
                  variant="ghost"
                  size="icon"
                  class="size-6 relative"
                  aria-label="Log Viewer"
                  @click="logStore.showViewer"
                >
                  <Terminal class="size-3.5" />
                  <span
                    v-if="errorCount > 0"
                    class="absolute -top-0.5 -right-0.5 size-2 rounded-full bg-destructive"
                  />
                </Button>
              </TooltipTrigger>
              <TooltipContent side="top">
                <p>
                  Log Viewer
                  <kbd class="ml-1 text-[10px] opacity-60">Ctrl+Shift+L</kbd>
                </p>
              </TooltipContent>
            </Tooltip>
          </div>
        </TooltipProvider>
      </div>
```

- [ ] **Step 5: Verify build**

Run: `cd frontend && npm run build`
Expected: Build succeeds with no errors.

- [ ] **Step 6: Commit**

```bash
git add frontend/src/App.vue frontend/src/layouts/AppFooter.vue
git commit -m "fix(frontend): fix footer content overlap and hide dev controls on mobile

Increase main padding pb-16→pb-20 for footer clearance.
Add safe-area-inset-bottom for notched devices.
Hide network/backend indicators and dev toolbar on mobile."
```

---

### Task 3: Dark Mode Navigation Menu Contrast

**Files:**
- Modify: `frontend/src/layouts/AppHeader.vue:9,139,188-212`

Fixes audit issues: #1 (dark mode nav near-invisible text), #15 (dialog missing aria-describedby)

- [ ] **Step 1: Import SheetDescription**

In `frontend/src/layouts/AppHeader.vue`, line 9, change:
```typescript
import { Sheet, SheetContent, SheetHeader, SheetTitle } from '@/components/ui/sheet'
```
to:
```typescript
import { Sheet, SheetContent, SheetDescription, SheetHeader, SheetTitle } from '@/components/ui/sheet'
```

- [ ] **Step 2: Add SheetDescription and bg-background to SheetContent**

In `frontend/src/layouts/AppHeader.vue`, line 139, change:
```html
    <SheetContent side="left" class="w-72 px-0">
      <SheetHeader class="px-4 pb-4 border-b">
        <SheetTitle class="text-left">
          <KGDBLogo :size="28" variant="with-text" text-layout="horizontal" :animated="false" />
        </SheetTitle>
      </SheetHeader>
```
to:
```html
    <SheetContent side="left" class="w-72 px-0 bg-background">
      <SheetHeader class="px-4 pb-4 border-b">
        <SheetTitle class="text-left">
          <KGDBLogo :size="28" variant="with-text" text-layout="horizontal" :animated="false" />
        </SheetTitle>
        <SheetDescription class="sr-only">Navigation menu</SheetDescription>
      </SheetHeader>
```

- [ ] **Step 3: Fix Login button text contrast in dark mode**

In `frontend/src/layouts/AppHeader.vue`, line 188-194, the unauthenticated login button in the drawer. Change:
```html
      <div v-else class="px-4 py-3">
        <button
          class="flex items-center gap-2 rounded-md px-2 py-1.5 text-sm hover:bg-accent w-full"
          @click="openLoginFromDrawer"
        >
          <LogIn class="size-4" />
          Login
        </button>
```
to:
```html
      <div v-else class="px-4 py-3">
        <button
          class="flex items-center gap-2 rounded-md px-2 py-1.5 text-sm text-foreground hover:bg-accent w-full"
          @click="openLoginFromDrawer"
        >
          <LogIn class="size-4" />
          Login
        </button>
```

- [ ] **Step 4: Fix nav link text contrast in dark mode**

In `frontend/src/layouts/AppHeader.vue`, lines 200-212, change the inactive nav item class from `text-muted-foreground` to `text-foreground/70`. This provides better contrast in dark mode while still differentiating from active items:

Change:
```html
        <button
          v-for="link in navLinks"
          :key="link.to"
          class="flex items-center gap-3 rounded-md px-2 py-2 text-sm transition-colors hover:bg-accent"
          :class="{
            'bg-accent text-accent-foreground font-medium': isActive(link.to),
            'text-muted-foreground': !isActive(link.to)
          }"
          @click="navigateMobile(link.to)"
        >
```
to:
```html
        <button
          v-for="link in navLinks"
          :key="link.to"
          class="flex items-center gap-3 rounded-md px-2 py-2 text-sm transition-colors hover:bg-accent"
          :class="{
            'bg-accent text-accent-foreground font-medium': isActive(link.to),
            'text-foreground/70': !isActive(link.to)
          }"
          @click="navigateMobile(link.to)"
        >
```

- [ ] **Step 5: Verify build**

Run: `cd frontend && npm run build`
Expected: Build succeeds with no errors.

- [ ] **Step 6: Commit**

```bash
git add frontend/src/layouts/AppHeader.vue
git commit -m "fix(frontend): improve dark mode navigation menu contrast

Change inactive nav items from text-muted-foreground to text-foreground/70.
Add explicit bg-background to SheetContent for dark mode.
Add SheetDescription for aria-describedby compliance.
Add text-foreground to login button in mobile drawer."
```

---

### Task 4: Network Analysis Responsive Form

**Files:**
- Modify: `frontend/src/views/NetworkAnalysis.vue:49-126`

Fixes audit issues: #4 (form controls overflow viewport)

- [ ] **Step 1: Replace fixed grid with responsive layout**

In `frontend/src/views/NetworkAnalysis.vue`, line 49, change:
```html
        <div class="grid grid-cols-[minmax(160px,280px)_auto_auto_auto_auto] gap-3 items-end">
```
to:
```html
        <div class="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-5 gap-3 items-end">
```

- [ ] **Step 2: Remove fixed widths on form fields**

Change the Min Score field (line 79) from:
```html
          <div class="space-y-1 w-20">
```
to:
```html
          <div class="space-y-1">
```

Change the Max Genes field (line 90) from:
```html
          <div class="space-y-1 w-20">
```
to:
```html
          <div class="space-y-1">
```

Change the STRING field (line 101) from:
```html
          <div class="space-y-1 w-24">
```
to:
```html
          <div class="space-y-1">
```

Change the Algorithm field (line 113) from:
```html
          <div class="space-y-1 w-40">
```
to:
```html
          <div class="space-y-1">
```

- [ ] **Step 3: Add overflow-hidden to the control bar card content**

In `frontend/src/views/NetworkAnalysis.vue`, line 47, change:
```html
      <CardContent class="p-3">
```
to:
```html
      <CardContent class="p-3 overflow-hidden">
```

- [ ] **Step 4: Add aria-label to Algorithm select trigger**

In `frontend/src/views/NetworkAnalysis.vue`, line 116, change:
```html
              <SelectTrigger class="h-9">
```
to:
```html
              <SelectTrigger class="h-9" aria-label="Clustering algorithm">
```

- [ ] **Step 5: Verify build**

Run: `cd frontend && npm run build`
Expected: Build succeeds with no errors.

- [ ] **Step 6: Commit**

```bash
git add frontend/src/views/NetworkAnalysis.vue
git commit -m "fix(frontend): make network analysis form responsive on mobile

Replace fixed 5-column grid with responsive grid-cols-1/2/5.
Remove hardcoded w-20/w-24/w-40 widths on input fields.
Add overflow-hidden and aria-label for accessibility."
```

---

### Task 5: Dashboard Mobile — UpSet Threshold + Tab Overflow

**Files:**
- Modify: `frontend/src/components/visualizations/UpSetChart.vue:415`
- Modify: `frontend/src/views/Dashboard.vue:70-84`

Fixes audit issues: #2 (charts unusable on mobile), #8 (tab bar overflow)

- [ ] **Step 1: Lower UpSet chart minimum width threshold**

In `frontend/src/components/visualizations/UpSetChart.vue`, line 415, change:
```javascript
  if (containerWidth < 400) {
```
to:
```javascript
  if (containerWidth < 280) {
```

- [ ] **Step 2: Make dashboard tab list scrollable on mobile**

In `frontend/src/views/Dashboard.vue`, line 71, change:
```html
          <TabsList>
```
to:
```html
          <TabsList class="w-full overflow-x-auto justify-start">
```

- [ ] **Step 3: Add short mobile labels to tab triggers**

In `frontend/src/views/Dashboard.vue`, lines 72-84, change:
```html
            <TabsTrigger value="overlaps">
              <ChartScatter :size="16" class="mr-2" />
              Gene Source Overlaps
            </TabsTrigger>
            <TabsTrigger value="distributions">
              <ChartBar :size="16" class="mr-2" />
              Source Distributions
            </TabsTrigger>
            <TabsTrigger value="composition">
              <Circle :size="16" class="mr-2" />
              Evidence Composition
            </TabsTrigger>
```
to:
```html
            <TabsTrigger value="overlaps" class="whitespace-nowrap">
              <ChartScatter :size="16" class="mr-2" />
              <span class="hidden sm:inline">Gene Source </span>Overlaps
            </TabsTrigger>
            <TabsTrigger value="distributions" class="whitespace-nowrap">
              <ChartBar :size="16" class="mr-2" />
              <span class="hidden sm:inline">Source </span>Distributions
            </TabsTrigger>
            <TabsTrigger value="composition" class="whitespace-nowrap">
              <Circle :size="16" class="mr-2" />
              <span class="hidden sm:inline">Evidence </span>Composition
            </TabsTrigger>
```

- [ ] **Step 4: Verify build**

Run: `cd frontend && npm run build`
Expected: Build succeeds with no errors.

- [ ] **Step 5: Commit**

```bash
git add frontend/src/components/visualizations/UpSetChart.vue frontend/src/views/Dashboard.vue
git commit -m "fix(frontend): improve dashboard mobile usability

Lower UpSet chart minimum width from 400px to 280px.
Make tab list scrollable with abbreviated labels on mobile."
```

---

### Task 6: Gene Table Mobile Column Hiding

**Files:**
- Modify: `frontend/src/components/GeneTable.vue:1-5,104-222`

Fixes audit issues: #7 (gene browser columns truncated on mobile)

- [ ] **Step 1: Import useMediaQuery and add reactive mobile flag**

In `frontend/src/components/GeneTable.vue`, line 2, change:
```typescript
import { ref, computed, onMounted, watch, h } from 'vue'
```
to:
```typescript
import { ref, computed, onMounted, watch, h, nextTick } from 'vue'
```

After line 6 (the `RouterLink` import), add:
```typescript
import { useMediaQuery } from '@vueuse/core'
```

- [ ] **Step 2: Add isMobile reactive and column visibility state**

After the `const isNavigating = ref(false)` line (around line 76), add:

```typescript
// Mobile responsive: hide non-essential columns
const isMobile = useMediaQuery('(max-width: 640px)')
const columnVisibility = ref<Record<string, boolean>>({})
```

- [ ] **Step 3: Add a watcher to toggle column visibility on breakpoint change**

After the `isMobile`/`columnVisibility` declarations, add:

```typescript
watch(isMobile, (mobile) => {
  columnVisibility.value = {
    hgnc_id: !mobile,
    sources: !mobile,
  }
}, { immediate: true })
```

- [ ] **Step 4: Pass columnVisibility to TanStack Table options**

In `frontend/src/components/GeneTable.vue`, line 245, the `useVueTable` call has a `state` object (lines 256-266). Add `columnVisibility` as a getter inside the existing `state` block, and add the `onColumnVisibilityChange` handler.

Change lines 256-266 from:
```typescript
  state: {
    get pagination(): PaginationState {
      return { pageIndex: page.value - 1, pageSize: itemsPerPage.value }
    },
    get sorting(): SortingState {
      return sortBy.value.map(s => ({
        id: s.key,
        desc: s.order === 'desc'
      }))
    }
  },
```
to:
```typescript
  state: {
    get pagination(): PaginationState {
      return { pageIndex: page.value - 1, pageSize: itemsPerPage.value }
    },
    get sorting(): SortingState {
      return sortBy.value.map(s => ({
        id: s.key,
        desc: s.order === 'desc'
      }))
    },
    get columnVisibility() {
      return columnVisibility.value
    }
  },
```

Then add `onColumnVisibilityChange` after `onSortingChange` (after line 283):
```typescript
  onColumnVisibilityChange: (updater: unknown) => {
    columnVisibility.value = typeof updater === 'function' ? updater(columnVisibility.value) : updater as Record<string, boolean>
  }
```

- [ ] **Step 5: Add aria-labels to icon-only buttons**

In the template section, find the Download button (around line 697):
```html
            <Button
              variant="outline"
              size="icon-sm"
              class="h-9 w-9"
              :disabled="loading"
              @click="exportData"
            >
              <Download class="h-4 w-4" />
            </Button>
```
Add `aria-label="Download CSV"`:
```html
            <Button
              variant="outline"
              size="icon-sm"
              class="h-9 w-9"
              aria-label="Download CSV"
              :disabled="loading"
              @click="exportData"
            >
              <Download class="h-4 w-4" />
            </Button>
```

Find the Clear Filters button (around line 700):
```html
            <Button
              variant="outline"
              size="icon-sm"
              class="h-9 w-9"
              :disabled="!hasActiveFilters"
              @click="clearAllFilters"
            >
              <FilterX class="h-4 w-4" />
            </Button>
```
Add `aria-label="Clear all filters"`:
```html
            <Button
              variant="outline"
              size="icon-sm"
              class="h-9 w-9"
              aria-label="Clear all filters"
              :disabled="!hasActiveFilters"
              @click="clearAllFilters"
            >
              <FilterX class="h-4 w-4" />
            </Button>
```

Find the Refresh button (around line 709):
```html
            <Button variant="outline" size="icon-sm" class="h-9 w-9" @click="refreshData">
```
Add `aria-label="Refresh data"`:
```html
            <Button variant="outline" size="icon-sm" class="h-9 w-9" aria-label="Refresh data" @click="refreshData">
```

- [ ] **Step 6: Verify build**

Run: `cd frontend && npm run build`
Expected: Build succeeds with no errors.

- [ ] **Step 7: Commit**

```bash
git add frontend/src/components/GeneTable.vue
git commit -m "fix(frontend): hide non-essential gene table columns on mobile

Use useMediaQuery to hide HGNC ID and Sources columns below 640px.
Add aria-labels to icon-only toolbar buttons."
```

---

### Task 7: Login Form Accessibility

**Files:**
- Modify: `frontend/src/views/Login.vue:78-117`

Fixes audit issues: #6 (password toggle missing accessible name), #14 (missing autocomplete attributes)

- [ ] **Step 1: Add autocomplete to username input**

In `frontend/src/views/Login.vue`, line 78-87, change:
```html
              <Input
                id="page-login-username"
                v-model="username"
                v-bind="usernameAttrs"
                type="text"
                placeholder="Enter username or email"
                :disabled="authStore.isLoading"
                autofocus
                :class="{ 'border-destructive': errors.username }"
              />
```
to:
```html
              <Input
                id="page-login-username"
                v-model="username"
                v-bind="usernameAttrs"
                type="text"
                placeholder="Enter username or email"
                autocomplete="username"
                :disabled="authStore.isLoading"
                autofocus
                :class="{ 'border-destructive': errors.username }"
              />
```

- [ ] **Step 2: Add autocomplete to password input**

In `frontend/src/views/Login.vue`, lines 96-106, change:
```html
                <Input
                  id="page-login-password"
                  v-model="password"
                  v-bind="passwordAttrs"
                  :type="showPassword ? 'text' : 'password'"
                  placeholder="Enter password"
                  :disabled="authStore.isLoading"
                  class="pr-10"
                  :class="{ 'border-destructive': errors.password }"
                  @keyup.enter="onSubmit"
                />
```
to:
```html
                <Input
                  id="page-login-password"
                  v-model="password"
                  v-bind="passwordAttrs"
                  :type="showPassword ? 'text' : 'password'"
                  placeholder="Enter password"
                  autocomplete="current-password"
                  :disabled="authStore.isLoading"
                  class="pr-10"
                  :class="{ 'border-destructive': errors.password }"
                  @keyup.enter="onSubmit"
                />
```

- [ ] **Step 3: Add aria-label to password visibility toggle**

In `frontend/src/views/Login.vue`, lines 107-113, change:
```html
                <Button
                  type="button"
                  variant="ghost"
                  size="icon"
                  class="absolute right-0 top-0 h-full px-3 hover:bg-transparent"
                  :disabled="authStore.isLoading"
                  @click="showPassword = !showPassword"
                >
```
to:
```html
                <Button
                  type="button"
                  variant="ghost"
                  size="icon"
                  class="absolute right-0 top-0 h-full px-3 hover:bg-transparent"
                  :aria-label="showPassword ? 'Hide password' : 'Show password'"
                  :disabled="authStore.isLoading"
                  @click="showPassword = !showPassword"
                >
```

- [ ] **Step 4: Verify build**

Run: `cd frontend && npm run build`
Expected: Build succeeds with no errors.

- [ ] **Step 5: Commit**

```bash
git add frontend/src/views/Login.vue
git commit -m "fix(frontend): add autocomplete and aria-label to login form

Add autocomplete=username and autocomplete=current-password.
Add dynamic aria-label to password visibility toggle button."
```

---

### Task 8: Heading Hierarchy + About Page Link Styling

**Files:**
- Modify: `frontend/src/views/DataSources.vue:53`
- Modify: `frontend/src/views/About.vue:49,151`

Fixes audit issues: #9 (heading order), #10 (links rely on color alone)

- [ ] **Step 1: Fix DataSources heading hierarchy**

In `frontend/src/views/DataSources.vue`, line 53, the source card uses h3 directly under h1 (skipping h2). Change:
```html
                <h3 class="text-lg font-bold text-white">{{ source.name }}</h3>
```
to:
```html
                <h2 class="text-lg font-bold text-white">{{ source.name }}</h2>
```

- [ ] **Step 2: Add underline to About page inline links**

In `frontend/src/views/About.vue`, line 49, change:
```html
              <RouterLink to="/genes" class="text-primary hover:underline">Gene Browser</RouterLink>
```
to:
```html
              <RouterLink to="/genes" class="text-primary underline underline-offset-4 hover:text-primary/80">Gene Browser</RouterLink>
```

In `frontend/src/views/About.vue`, line 151, change:
```html
              <a href="/docs" target="_blank" class="text-primary hover:underline">/docs</a>
```
to:
```html
              <a href="/docs" target="_blank" class="text-primary underline underline-offset-4 hover:text-primary/80">/docs</a>
```

- [ ] **Step 3: Verify build**

Run: `cd frontend && npm run build`
Expected: Build succeeds with no errors.

- [ ] **Step 4: Commit**

```bash
git add frontend/src/views/DataSources.vue frontend/src/views/About.vue
git commit -m "fix(frontend): fix heading hierarchy and link accessibility

Change DataSources card headings from h3 to h2 (fixes h1→h3 skip).
Add persistent underline to inline text links on About page."
```

---

### Task 9: Playwright Mobile Accessibility Tests

**Files:**
- Create: `frontend/playwright.config.ts`
- Create: `frontend/e2e/mobile-accessibility.spec.ts`
- Modify: `frontend/package.json` (add test:e2e script)

This task adds automated Playwright tests to verify all mobile accessibility fixes. Requires the Vite dev server running on localhost:5173.

- [ ] **Step 1: Create Playwright config**

Create `frontend/playwright.config.ts`:

```typescript
import { defineConfig, devices } from 'playwright/test'

export default defineConfig({
  testDir: './e2e',
  fullyParallel: true,
  forbidOnly: !!process.env.CI,
  retries: process.env.CI ? 2 : 0,
  workers: process.env.CI ? 1 : undefined,
  reporter: 'html',
  use: {
    baseURL: 'http://localhost:5173',
    trace: 'on-first-retry',
  },
  projects: [
    {
      name: 'Mobile Chrome',
      use: { ...devices['iPhone SE'] },
    },
    {
      name: 'Mobile Chrome Dark',
      use: {
        ...devices['iPhone SE'],
        colorScheme: 'dark',
      },
    },
  ],
  webServer: {
    command: 'npm run dev',
    url: 'http://localhost:5173',
    reuseExistingServer: !process.env.CI,
  },
})
```

- [ ] **Step 2: Add test:e2e script to package.json**

In `frontend/package.json`, add to the `"scripts"` section:

```json
"test:e2e": "npx playwright test",
"test:e2e:ui": "npx playwright test --ui"
```

- [ ] **Step 3: Create mobile accessibility test file**

Create `frontend/e2e/mobile-accessibility.spec.ts`:

```typescript
import { test, expect } from 'playwright/test'

test.describe('Mobile Accessibility Fixes', () => {
  // Task 1: Global contrast — verified visually, no programmatic test needed

  // Task 2: Footer overlap + dev toolbar
  test.describe('Footer', () => {
    test('main content has sufficient bottom padding to clear footer', async ({ page }) => {
      await page.goto('/')
      const main = page.locator('main')
      const mainBox = await main.boundingBox()
      const footer = page.locator('footer')
      const footerBox = await footer.boundingBox()
      expect(mainBox).toBeTruthy()
      expect(footerBox).toBeTruthy()
      // Main content bottom edge should not overlap footer top edge
      expect(mainBox!.y + mainBox!.height).toBeLessThanOrEqual(footerBox!.y + 1)
    })

    test('dev controls are hidden on mobile', async ({ page }) => {
      await page.goto('/')
      // Log viewer button should not be visible on mobile
      const logViewer = page.locator('button[aria-label="Log Viewer"]')
      await expect(logViewer).toBeHidden()
      // GitHub link should still be visible
      const github = page.locator('a[aria-label="GitHub Repository"]')
      await expect(github).toBeVisible()
    })
  })

  // Task 3: Dark mode navigation
  test.describe('Navigation drawer', () => {
    test('mobile menu opens and nav items are visible', async ({ page }) => {
      await page.goto('/')
      // Open mobile menu
      const menuButton = page.locator('button:has-text("Toggle menu")')
      // Use sr-only text to find the button
      const menuToggle = page.locator('button', { has: page.locator('.sr-only:text("Toggle menu")') })
      await menuToggle.click()
      // Wait for drawer to open
      await page.waitForTimeout(300)
      // Check nav items are visible
      const geneLink = page.locator('button:has-text("Gene Browser")')
      await expect(geneLink).toBeVisible()
      const dashboardLink = page.locator('button:has-text("Data Overview")')
      await expect(dashboardLink).toBeVisible()
    })

    test('sheet has aria-describedby', async ({ page }) => {
      await page.goto('/')
      const menuToggle = page.locator('button', { has: page.locator('.sr-only:text("Toggle menu")') })
      await menuToggle.click()
      await page.waitForTimeout(300)
      // SheetDescription should exist (even if sr-only)
      const description = page.locator('[role="dialog"] .sr-only:text("Navigation menu")')
      await expect(description).toBeAttached()
    })
  })

  // Task 4: Network analysis form
  test.describe('Network Analysis form', () => {
    test('form fields do not overflow viewport', async ({ page }) => {
      await page.goto('/network-analysis')
      // Check no horizontal scrollbar
      const scrollWidth = await page.evaluate(() => document.documentElement.scrollWidth)
      const clientWidth = await page.evaluate(() => document.documentElement.clientWidth)
      expect(scrollWidth).toBeLessThanOrEqual(clientWidth + 1) // 1px tolerance
    })

    test('algorithm select has aria-label', async ({ page }) => {
      await page.goto('/network-analysis')
      const select = page.locator('[aria-label="Clustering algorithm"]')
      await expect(select).toBeAttached()
    })
  })

  // Task 5: Dashboard
  test.describe('Dashboard', () => {
    test('UpSet chart does not show "Screen too narrow" message', async ({ page }) => {
      await page.goto('/dashboard?tab=overlaps')
      // Wait for chart to load
      await page.waitForTimeout(2000)
      const narrowMessage = page.locator('text=Screen too narrow')
      await expect(narrowMessage).toBeHidden()
    })

    test('tab list does not overflow', async ({ page }) => {
      await page.goto('/dashboard')
      const tabsList = page.locator('[role="tablist"]')
      await expect(tabsList).toBeVisible()
      // Tabs should either fit or be scrollable
      const isOverflowing = await tabsList.evaluate((el) => el.scrollWidth > el.clientWidth + 1)
      if (isOverflowing) {
        // If overflowing, overflow-x should be auto/scroll
        const overflow = await tabsList.evaluate((el) => getComputedStyle(el).overflowX)
        expect(['auto', 'scroll']).toContain(overflow)
      }
    })
  })

  // Task 6: Gene table columns
  test.describe('Gene Table', () => {
    test('hides HGNC ID and Sources columns on mobile', async ({ page }) => {
      await page.goto('/genes')
      // Wait for table to load
      await page.waitForSelector('table', { timeout: 10000 })
      // HGNC ID column header should not be visible
      const hgncHeader = page.locator('th:has-text("HGNC ID")')
      await expect(hgncHeader).toBeHidden()
      // Sources column header should not be visible
      const sourcesHeader = page.locator('th:has-text("Sources")')
      await expect(sourcesHeader).toBeHidden()
      // Gene column should be visible
      const geneHeader = page.locator('th:has-text("Gene")')
      await expect(geneHeader).toBeVisible()
    })

    test('icon buttons have aria-labels', async ({ page }) => {
      await page.goto('/genes')
      await page.waitForSelector('table', { timeout: 10000 })
      await expect(page.locator('button[aria-label="Download CSV"]')).toBeAttached()
      await expect(page.locator('button[aria-label="Clear all filters"]')).toBeAttached()
      await expect(page.locator('button[aria-label="Refresh data"]')).toBeAttached()
    })
  })

  // Task 7: Login form
  test.describe('Login form', () => {
    test('has autocomplete attributes', async ({ page }) => {
      await page.goto('/login')
      const username = page.locator('#page-login-username')
      await expect(username).toHaveAttribute('autocomplete', 'username')
      const password = page.locator('#page-login-password')
      await expect(password).toHaveAttribute('autocomplete', 'current-password')
    })

    test('password toggle has aria-label', async ({ page }) => {
      await page.goto('/login')
      const toggle = page.locator('button[aria-label="Show password"]')
      await expect(toggle).toBeAttached()
    })
  })

  // Task 8: Headings + links
  test.describe('Heading hierarchy', () => {
    test('DataSources has no heading level skip', async ({ page }) => {
      await page.goto('/data-sources')
      await page.waitForTimeout(1000)
      const headings = await page.evaluate(() => {
        const hs = document.querySelectorAll('h1, h2, h3, h4, h5, h6')
        return Array.from(hs).map(h => ({
          level: parseInt(h.tagName.charAt(1)),
          text: h.textContent?.trim().substring(0, 50) || ''
        }))
      })
      // Verify no heading level is skipped
      for (let i = 1; i < headings.length; i++) {
        const gap = headings[i].level - headings[i - 1].level
        expect(gap, `Heading skip: "${headings[i - 1].text}" (h${headings[i - 1].level}) → "${headings[i].text}" (h${headings[i].level})`).toBeLessThanOrEqual(1)
      }
    })
  })

  test.describe('About page links', () => {
    test('inline links have underline decoration', async ({ page }) => {
      await page.goto('/about')
      const geneBrowserLink = page.locator('a:has-text("Gene Browser"), [href="/genes"]:has-text("Gene Browser")')
      const textDecoration = await geneBrowserLink.evaluate((el) =>
        getComputedStyle(el).textDecorationLine
      )
      expect(textDecoration).toContain('underline')
    })
  })
})
```

- [ ] **Step 4: Install Playwright browsers (if not already done)**

Run: `cd frontend && npx playwright install chromium`
Expected: Chromium browser downloaded for Playwright.

- [ ] **Step 5: Run the tests (with dev server running)**

Run: `cd frontend && npx playwright test --project="Mobile Chrome"`
Expected: All tests pass. Some tests may need the backend running for data-dependent pages (genes, dashboard). Tests that fail due to missing backend data are acceptable — the structural/accessibility checks are the priority.

- [ ] **Step 6: Commit**

```bash
git add frontend/playwright.config.ts frontend/e2e/mobile-accessibility.spec.ts frontend/package.json
git commit -m "test(frontend): add Playwright mobile accessibility e2e tests

Verify mobile fixes: footer overlap, nav drawer, form responsiveness,
column hiding, aria-labels, autocomplete, heading hierarchy, link styling."
```

---

## Verification Checklist

After all tasks are complete, run these checks:

- [ ] `cd frontend && npm run build` — Full build succeeds
- [ ] `cd frontend && npm run lint` — No lint errors
- [ ] `cd frontend && npm run test:run` — All existing tests pass
- [ ] Manual check at 375px viewport width in both light and dark mode:
  - Mobile nav drawer: all items clearly readable in dark mode
  - Footer: no content overlap, dev controls hidden
  - Network Analysis: form fields stack vertically, no horizontal overflow
  - Dashboard: UpSet chart renders (scrollable), tabs fit or scroll
  - Gene table: shows Gene + Tier + Evidence + Score only
  - Login: autocomplete works with browser password manager
  - About: links have underlines
  - DataSources: heading hierarchy is h1→h2
