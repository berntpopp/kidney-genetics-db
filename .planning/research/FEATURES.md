# Feature Research

**Domain:** Frontend migration (Vuetify 3 to shadcn-vue component patterns)
**Researched:** 2026-02-28
**Confidence:** HIGH (data tables, forms, dialogs, toasts); MEDIUM (navigation, animation transitions); LOW (range slider multi-thumb, complex multi-select)

---

## Context: What Is Being Migrated

The existing frontend has 73 Vue components built entirely on Vuetify 3. The migration replaces the Vuetify component layer with shadcn-vue + Tailwind CSS v4, while keeping Vue 3, Pinia, Vue Router, D3.js, Cytoscape, and UpSet.js unchanged.

Key Vuetify usage count (from codebase audit):
- 431 `v-icon` — migrate to `lucide-vue-next`
- 412 `v-btn` — migrate to shadcn-vue `Button`
- 396 `v-col` / `v-row` — replace with Tailwind CSS grid/flex utilities
- 350 `v-chip` — migrate to shadcn-vue `Badge`
- 254+ `v-card` — migrate to shadcn-vue `Card`
- 60 `v-dialog` — migrate to shadcn-vue `Dialog` / `AlertDialog`
- 29 `v-data-table` / `v-data-table-server` — migrate to TanStack Table + shadcn-vue `Table`
- 18 `v-form` — migrate to vee-validate + zod + shadcn-vue `Form`

---

## Feature Landscape

### Table Stakes (Must Have for Parity)

These features are required for functional equivalence with the current Vuetify implementation. Missing any of these means the migration is incomplete.

| Feature | Why Expected | Complexity | Notes |
|---------|--------------|------------|-------|
| Server-side data table (pagination, sorting, filtering) | GeneTable uses `v-data-table-server` with 571+ genes, URL-synced state | High | Requires TanStack Table + `useVueTable` with `manualPagination: true` and `manualSorting: true`; `rowCount` prop replaces Vuetify's `items-length` |
| Client-side data table | AdminUserManagement uses `v-data-table` with in-memory filtering | Medium | Same TanStack Table pattern; simpler because no `rowCount` needed |
| Custom cell slot rendering | Gene symbol as router-link, tier badges, chip groups per row | Medium | TanStack Table uses `cell: ({ row }) => h(Component, props)` — render functions or slot patterns |
| Dialog (modal) | 60 `v-dialog` usages across admin, auth, confirm-delete flows | Medium | shadcn-vue `Dialog` (dismissable) and `AlertDialog` (destructive confirmation) are separate components — significant; `AlertDialog` is the correct replace for "Confirm Delete" dialogs |
| Form validation | 18 `v-form` with inline `:rules` arrays | High | Must replace `v-form` + `:rules` prop pattern with vee-validate `useForm` + `toTypedSchema` (zod); shadcn-vue `FormField`/`FormItem`/`FormMessage` handle ARIA automatically |
| Text input / password input | `v-text-field` with `prepend-inner-icon`, `append-inner-icon` for password reveal | Medium | shadcn-vue `Input` is simpler; icon slots become wrapper divs with absolute positioning or `Input` variant with leading/trailing icon wrapper |
| Select (single) | `v-select` for sort options, role selection, log level | Medium | shadcn-vue `Select` with `SelectTrigger`, `SelectContent`, `SelectItem` |
| Multi-select with chips | `v-select` + `multiple` + `chips` for evidence sources, tiers | High | No native multi-select with chips in shadcn-vue; pattern is Combobox (Popover + Command) combined with TagsInput — see Component Pattern Reference |
| Range slider (dual thumb) | `v-range-slider` for evidence score and count filters | High | shadcn-vue `Slider` supports multiple thumbs via array value — `[min, max]`; requires custom display for min/max labels alongside |
| Toast notifications | `v-snackbar` used across all admin pages for success/error feedback | Low | shadcn-vue Sonner (`vue-sonner`) replaces this; old `Toast` component deprecated in shadcn-vue itself |
| Breadcrumb navigation | `v-breadcrumbs` in every page header | Low | shadcn-vue `Breadcrumb` with `BreadcrumbList`, `BreadcrumbItem`, `BreadcrumbLink`, `BreadcrumbSeparator`, `BreadcrumbPage` |
| Pagination controls | Custom pagination bar above GeneTable (top-positioned per style guide) | Medium | shadcn-vue `Pagination` component provides `PaginationRoot`, `PaginationList`, `PaginationListItem`, `PaginationFirst/Prev/Next/Last`; pairs with TanStack Table state |
| Progress indicator (circular) | `v-progress-circular` for loading states (gene detail, network analysis) | Low | shadcn-vue `Spinner` component (new in recent versions) or CSS Tailwind `animate-spin` border trick; confirmed available |
| Progress indicator (linear) | `v-progress-linear` for evidence strength bars in GeneTable cells | Low | shadcn-vue `Progress` component; `value` prop 0-100 |
| Tooltip | `v-tooltip` used 20+ times for inline help text and aliases | Low | shadcn-vue `Tooltip` with `TooltipProvider` wrapper (required at app level), `TooltipTrigger`, `TooltipContent` |
| Dropdown menu | `v-menu` used for overflow chip menus and actions menus (gene detail) | Medium | shadcn-vue `DropdownMenu` with `DropdownMenuTrigger`, `DropdownMenuContent`, `DropdownMenuItem` |
| Accordion / expansion panels | `v-expansion-panels` for evidence cards in GeneDetail | Medium | shadcn-vue `Accordion` with `AccordionItem`, `AccordionTrigger`, `AccordionContent` |
| Tabs | Gene detail likely has tabs; admin panel uses section tabs | Medium | shadcn-vue `Tabs` with `TabsList`, `TabsTrigger`, `TabsContent` |
| Card layout | 254+ `v-card` usages — filter panels, stat cards, evidence cards | Low | shadcn-vue `Card` with `CardHeader`, `CardTitle`, `CardDescription`, `CardContent`, `CardFooter` |
| Switch (boolean toggle) | `v-switch` for "Show genes with insufficient evidence" in GeneTable | Low | shadcn-vue `Switch` component; integrates with vee-validate via `componentField` |
| Checkbox | `v-checkbox` in user management forms (is_active, is_verified) | Low | shadcn-vue `Checkbox`; in forms use `FormField` with `componentField` binding |
| Avatar | `v-avatar` in navigation drawer user section, evidence cards | Low | shadcn-vue `Avatar` with `AvatarImage`, `AvatarFallback` |
| Badge / chip | 350 `v-chip` usages — evidence tiers, source names, status indicators | Low | shadcn-vue `Badge` for static labels; for interactive/closable chips, combine `Badge` with an X button or use `TagsInput` |
| Alert / inline error | `v-alert` for error states in login modal | Low | shadcn-vue `Alert` with `AlertTitle`, `AlertDescription`; variants: `default`, `destructive` |
| Navigation bar (app-bar) | `v-app-bar` with logo, nav links, theme toggle, auth controls | Medium | Tailwind-styled `<header>` element; no direct shadcn-vue equivalent — compose from shadcn-vue `Button`, `NavigationMenu`, `DropdownMenu` |
| Mobile drawer navigation | `v-navigation-drawer` for mobile menu | Medium | shadcn-vue `Sheet` component (slides in from side); `SheetContent`, `SheetHeader`, `SheetTitle` |
| Log viewer drawer | `v-navigation-drawer` used as right-side overlay log panel | Medium | shadcn-vue `Sheet` with `side="right"` — same pattern as mobile drawer |
| Dark / light theme toggle | `useTheme()` from Vuetify for global theme switching | Medium | `useColorMode()` from `@vueuse/core` + `VueUseHead` or manual class toggling on `<html>`; shadcn-vue theming uses CSS variable switching |
| Responsive grid layout | `v-row` / `v-col` used throughout for responsive layouts | Low | Tailwind CSS grid/flex utilities (`grid`, `grid-cols-*`, `md:grid-cols-*`, `gap-*`) replace Vuetify's 12-column grid |
| Skeleton loading | Not currently used but expected for data loading states | Low | shadcn-vue `Skeleton` component |
| Separator / divider | `v-divider` used in navigation drawer sections | Low | shadcn-vue `Separator` component |

---

### Differentiators (Improvements Over Vuetify)

Features where the target stack improves on Vuetify's approach.

| Feature | Value Proposition | Complexity | Notes |
|---------|-------------------|------------|-------|
| Full component ownership | shadcn-vue copies source into project; no dependency on upstream breaking changes | Low | Components live in `src/components/ui/`; no `vuetify` in node_modules at runtime |
| Smaller bundle size | Vuetify is ~1.2MB minified; shadcn-vue + Tailwind CSS v4 tree-shakes to only used components | Low | Lucide icons are ES-module tree-shakable — only imported icons ship |
| TypeScript-first forms | vee-validate + zod provides `toTypedSchema` giving compile-time safety on form values; Vuetify `:rules` arrays are untyped function arrays | High | Must convert all 18 `v-form` instances and their inline `:rules` to typed zod schemas |
| Accessible dialogs (ARIA) | shadcn-vue `Dialog` built on Radix Vue primitives; focus trap, `aria-modal`, keyboard dismiss all automatic | Low | Replaces manual Vuetify dialog accessibility handling |
| Headless table with full control | TanStack Table provides column definitions as pure TypeScript; cell render functions allow any Vue component without `:deep()` CSS overrides | Medium | Vuetify `v-data-table` requires `:deep()` CSS hacks for custom cell styling (currently 50+ lines of `:deep()` in GeneTable) |
| CSS variables theming (OKLCH) | shadcn-vue v4 uses OKLCH color space; CSS variables in `:root`/`.dark`; no JavaScript theme object needed at runtime | Medium | Replace Vuetify's JavaScript theme object with `@layer base { :root { --primary: oklch(...) } }` |
| Tailwind CSS v4 CSS-first config | No `tailwind.config.js` needed; `@theme` directive in CSS file; simpler mental model | Medium | Tailwind v4 uses `@import "tailwindcss"` and `@theme` block in CSS — replaces `tailwind.config.js` |
| Built-in server-side table URL sync | Custom implementation in GeneTable (parseUrlParams/updateUrl) stays unchanged — TanStack Table state is just reactive refs that the existing logic already manages | Low | No behavior change required; the URL sync logic is in Vue script, not in Vuetify |
| Composable sidebar for admin | shadcn-vue `Sidebar` with `SidebarProvider` handles collapsible state, keyboard shortcuts, and persisted open/close with CSS variables — replaces custom drawer management | High | Admin panel currently uses multiple `v-navigation-drawer` and nested layouts; Sidebar component provides a proper admin layout shell |
| Native `toast.promise()` | Sonner's `toast.promise()` handles async with loading/success/error states automatically; `v-snackbar` requires manual state management | Low | Replace snackbar success/error sequences in admin pages with single `toast.promise(apiCall, { loading: '...', success: '...', error: '...' })` |

---

### Anti-Features (Don't Replicate from Vuetify)

Vuetify patterns that should not be carried over.

| Feature | Why Requested | Why Problematic | Alternative |
|---------|---------------|-----------------|-------------|
| Vuetify's global `defaults` object | Convenient for setting density/variant everywhere | Creates invisible coupling; new developers don't know why components behave differently without reading the plugin config | Use Tailwind CSS utility classes inline; create project-specific wrapper components (e.g., `AppButton`) that encode the design system defaults explicitly |
| `:deep()` CSS overrides for table cells | Works but is the only way to style inside `v-data-table` | Creates fragile styles that break on Vuetify upgrades; hard to discover | TanStack Table `cell` render functions use plain HTML + Tailwind; no `deep` needed |
| Inline `:rules` validation arrays | `v-form` with `v-model="formValid"` + per-field `:rules` | Untyped; validation logic scattered across template; no schema reuse | Consolidate into zod schema objects in `<script setup>`; reuse schemas across create/edit dialogs |
| All-or-nothing Vuetify import | `import * as components from 'vuetify/components'` in plugin | Imports entire 1.2MB component library even if 20 components are used | shadcn-vue CLI adds only the components you request; no global import |
| `v-spacer` for flexbox layout | Used pervasively to push items apart | `v-spacer` is a Vuetify-only concept; not needed in CSS flex/grid | `ml-auto` or `justify-between` in Tailwind CSS |
| Vuetify color props on components | `color="primary"` / `color="error"` / `color="warning"` on chips, buttons | Maps to Vuetify's internal theme system; not portable | Use Tailwind CSS variant classes or CSS variable references: `bg-primary text-primary-foreground` |
| `density="compact"` global prop | Useful for information-dense medical data tables | Vuetify-specific prop; no equivalent in shadcn-vue | Use Tailwind spacing utilities (`py-1`, `px-2`, `text-sm`) applied consistently to achieve compact density |
| `v-progress-circular` with `indeterminate` as primary loading indicator | Works fine | Requires Vuetify | Use Tailwind CSS `animate-spin` on a border div, or shadcn-vue `Spinner`; consistent with new stack |
| MDI font CSS (`@mdi/font/css/materialdesignicons.css`) | Provides all 7000+ icons via CSS font | Loads all icons (300KB+) regardless of usage | Replace with `lucide-vue-next` which is fully tree-shakable; only imported icons included in bundle |
| `v-navigation-drawer` as multi-purpose overlay | Used for both mobile nav and log viewer overlay | Two different UX patterns forced into one component | Use shadcn-vue `Sheet` for overlay drawers and shadcn-vue `Sidebar` for persistent navigation |

---

## Feature Dependencies

The following dependency tree determines implementation order. A feature at a lower level cannot be fully implemented without its dependencies.

```
Level 0 (Foundation — no dependencies):
  - Tailwind CSS v4 setup (CSS variables, @theme directive)
  - TypeScript tsconfig + path aliases (@/components/ui/)
  - shadcn-vue CLI init (components.json)
  - lucide-vue-next icon package

Level 1 (Core primitives — depend on Level 0):
  - Button
  - Badge
  - Card (CardHeader, CardContent, CardFooter)
  - Separator
  - Avatar
  - Tooltip (needs TooltipProvider at app root)
  - Progress (linear)
  - Spinner / circular loading

Level 2 (Overlay + notification — depend on Level 1):
  - Dialog (needs Button for trigger/close)
  - AlertDialog (needs Button)
  - Sheet (needs Button for trigger)
  - Sonner / Toaster (needs placement in App.vue)
  - Alert (inline, no dependencies)
  - DropdownMenu (needs Button for trigger)
  - Popover (needs Button for trigger)

Level 3 (Form infrastructure — depend on Level 1-2):
  - vee-validate + @vee-validate/zod + zod (npm packages)
  - Form / FormField / FormItem / FormLabel / FormControl / FormMessage
  - Input (text, password, number)
  - Select (single)
  - Checkbox
  - Switch
  - Slider (including dual-thumb range)
  - Combobox (multi-select pattern: Popover + Command + TagsInput)

Level 4 (Navigation — depend on Level 2-3):
  - Breadcrumb
  - Pagination
  - Tabs
  - Accordion
  - NavigationMenu (top nav bar, desktop)
  - Sheet (repurposed for mobile nav drawer)
  - Sidebar (admin panel persistent nav)
  - Dark mode toggle (useColorMode from @vueuse/core)

Level 5 (Data table — depends on Level 1-4):
  - TanStack Table (@tanstack/vue-table)
  - Table (shadcn-vue primitive: Table, TableHeader, TableBody, TableRow, TableHead, TableCell)
  - DataTable wrapper component (uses Pagination from Level 4)
  - Server-side variant (manualPagination + manualSorting + rowCount)
  - Custom cell render components (uses Badge, Tooltip, Progress from Level 1-2)

Level 6 (Page assembly — depends on all above):
  - App shell (header + mobile Sheet + Sidebar for admin)
  - GeneTable (largest complexity: server-side DataTable + filter forms)
  - GeneDetail (Accordion evidence cards + Tabs)
  - Admin pages (Dialog forms + DataTable + Sidebar)
  - Auth modals (Dialog + Form)
```

**Critical blocking dependency:** The multi-select chip pattern (Combobox + TagsInput) must be solved at Level 3 before GeneTable can be fully migrated, as it replaces `v-select multiple chips` used in two filter fields.

---

## Migration Priority Matrix

| Feature Area | User Value | Migration Complexity | Priority | Risk |
|-------------|-----------|---------------------|----------|------|
| Tailwind CSS v4 + CSS variables theming | Foundation | Low | P0 | Low — well-documented |
| TypeScript setup (tsconfig, aliases) | Foundation | Low | P0 | Low — standard Vite TS setup |
| shadcn-vue CLI init + components.json | Foundation | Low | P0 | Low |
| Button, Badge, Card, Separator | Foundation | Low | P0 | Low |
| Lucide icons (replaces MDI font) | Foundation | Low | P0 | Medium — 431 icon usages need symbol mapping |
| Toast (Sonner) | High — all admin feedback | Low | P1 | Low |
| Dialog + AlertDialog | High — 60 usages | Medium | P1 | Low |
| Form + vee-validate + zod | High — all admin forms | High | P1 | Medium — schema authoring for 18 forms |
| Input, Select, Checkbox, Switch | High — all forms | Low | P1 | Low |
| Dark mode toggle | High — current feature | Medium | P1 | Low |
| Navigation bar (app-bar replacement) | High — global chrome | Medium | P2 | Low |
| Mobile drawer (Sheet) | High — mobile UX | Low | P2 | Low |
| Breadcrumb | Medium | Low | P2 | Low |
| Avatar, Tooltip, Alert | Medium | Low | P2 | Low |
| Accordion | Medium — evidence cards | Medium | P2 | Low |
| Tabs | Medium — gene detail | Low | P2 | Low |
| Pagination component | High — GeneTable | Medium | P3 | Low |
| TanStack Table (client-side) | High — admin tables | Medium | P3 | Medium |
| TanStack Table (server-side) | High — GeneTable | High | P3 | High — most complex single feature |
| Slider (range, dual-thumb) | Medium — filter UX | High | P3 | Medium — no direct v-range-slider equivalent |
| Multi-select with chips (Combobox) | High — GeneTable filters | High | P3 | High — requires composing 3 primitives |
| Sidebar (admin panel) | Medium — admin UX | Medium | P4 | Low |
| Admin panel pages (11 pages) | Admin-only | High | P4 | Medium |
| Progress (linear/circular) | Low | Low | P4 | Low |

---

## Component Pattern Reference

### 1. Data Tables: Server-Side with TanStack Table

This is the highest-complexity feature. The existing `v-data-table-server` pattern must be replaced with a TanStack Table + shadcn-vue `Table` primitive.

**Install:**
```bash
npx shadcn-vue@latest add table
npm install @tanstack/vue-table
```

**Column definition (TypeScript):**
```typescript
// columns.ts
import type { ColumnDef } from '@tanstack/vue-table'
import { h } from 'vue'
import { Badge } from '@/components/ui/badge'
import RouterLink from 'vue-router'

export const columns: ColumnDef<Gene>[] = [
  {
    accessorKey: 'approved_symbol',
    header: 'Gene Symbol',
    cell: ({ row }) =>
      h(RouterLink, { to: `/genes/${row.getValue('approved_symbol')}`, class: 'font-medium text-primary hover:underline' },
        () => row.getValue('approved_symbol')
      ),
  },
  {
    accessorKey: 'evidence_tier',
    header: 'Evidence Tier',
    cell: ({ row }) => h(EvidenceTierBadge, { tier: row.getValue('evidence_tier') }),
  },
]
```

**Server-side table composition (Vue 3):**
```typescript
// DataTable.vue <script setup lang="ts">
import { ref, computed } from 'vue'
import {
  useVueTable,
  getCoreRowModel,
  type SortingState,
  type PaginationState,
} from '@tanstack/vue-table'

const props = defineProps<{
  columns: ColumnDef<Gene>[]
  data: Gene[]
  rowCount: number  // replaces Vuetify's items-length
}>()

// Externally managed state — synced with URL params (existing logic unchanged)
const sorting = ref<SortingState>([{ id: 'evidence_score', desc: true }])
const pagination = ref<PaginationState>({ pageIndex: 0, pageSize: 10 })

const table = useVueTable({
  get data() { return props.data },
  get columns() { return props.columns },
  get rowCount() { return props.rowCount },
  state: {
    get sorting() { return sorting.value },
    get pagination() { return pagination.value },
  },
  manualPagination: true,   // server owns pagination
  manualSorting: true,      // server owns sorting
  onSortingChange: updater => {
    sorting.value = typeof updater === 'function' ? updater(sorting.value) : updater
    emit('sort-change', sorting.value)
  },
  onPaginationChange: updater => {
    pagination.value = typeof updater === 'function' ? updater(pagination.value) : updater
    emit('page-change', pagination.value)
  },
  getCoreRowModel: getCoreRowModel(),
})
```

**Key difference from Vuetify:** TanStack Table uses `pageIndex` (0-based) while Vuetify uses `page` (1-based). The existing GeneTable URL sync logic (`page.value = 1` resets) needs `pageIndex = 0` translation.

**Confidence:** HIGH (official TanStack Table Vue docs confirm this pattern)

---

### 2. Forms: vee-validate + zod + shadcn-vue Form

Replaces `v-form` + inline `:rules` arrays.

**Install:**
```bash
npm install vee-validate @vee-validate/zod zod
npx shadcn-vue@latest add form input select checkbox switch
```

**Pattern (replaces LoginModal's v-form):**
```typescript
// LoginModal.vue <script setup lang="ts">
import { useForm } from 'vee-validate'
import { toTypedSchema } from '@vee-validate/zod'
import * as z from 'zod'

const formSchema = toTypedSchema(z.object({
  username: z.string().min(1, 'Username is required'),
  password: z.string().min(1, 'Password is required'),
}))

const { handleSubmit, isSubmitting } = useForm({
  validationSchema: formSchema,
})

const onSubmit = handleSubmit(async (values) => {
  // values is typed: { username: string, password: string }
  await authStore.login(values.username, values.password)
})
```

```vue
<!-- Template -->
<form @submit="onSubmit">
  <FormField v-slot="{ componentField }" name="username">
    <FormItem>
      <FormLabel>Username or Email</FormLabel>
      <FormControl>
        <Input placeholder="Username" v-bind="componentField" />
      </FormControl>
      <FormMessage />  <!-- Auto-displays zod error messages -->
    </FormItem>
  </FormField>

  <FormField v-slot="{ componentField }" name="password">
    <FormItem>
      <FormLabel>Password</FormLabel>
      <FormControl>
        <Input type="password" v-bind="componentField" />
      </FormControl>
      <FormMessage />
    </FormItem>
  </FormField>

  <Button type="submit" :disabled="isSubmitting">Login</Button>
</form>
```

**Key migration note:** The existing `formValid` ref pattern (`v-model="formValid"` on `v-form`) is replaced by `handleSubmit` — the form only calls the handler if validation passes. No separate `formValid` boolean needed.

**Confidence:** HIGH (verified against shadcn-vue official form documentation)

---

### 3. Dialogs: Dialog and AlertDialog

Replaces `v-dialog`.

**Pattern (create/edit dialog — replaces AdminUserManagement's v-dialog):**
```vue
<Dialog v-model:open="showCreateDialog">
  <DialogContent class="sm:max-w-[600px]">
    <DialogHeader>
      <DialogTitle>{{ editingUser ? 'Edit User' : 'Create New User' }}</DialogTitle>
    </DialogHeader>
    <!-- form content -->
    <DialogFooter>
      <Button variant="outline" @click="showCreateDialog = false">Cancel</Button>
      <Button @click="saveUser" :disabled="isSubmitting">
        {{ editingUser ? 'Update' : 'Create' }}
      </Button>
    </DialogFooter>
  </DialogContent>
</Dialog>
```

**Pattern (destructive confirmation — replaces showDeleteDialog):**
```vue
<AlertDialog v-model:open="showDeleteDialog">
  <AlertDialogContent>
    <AlertDialogHeader>
      <AlertDialogTitle>Confirm Delete</AlertDialogTitle>
      <AlertDialogDescription>
        Delete user "{{ deletingUser?.username }}"? This cannot be undone.
      </AlertDialogDescription>
    </AlertDialogHeader>
    <AlertDialogFooter>
      <AlertDialogCancel>Cancel</AlertDialogCancel>
      <AlertDialogAction @click="deleteUser">Delete</AlertDialogAction>
    </AlertDialogFooter>
  </AlertDialogContent>
</AlertDialog>
```

**Key difference:** `AlertDialog` separates destructive confirmation from regular dialogs — no custom red styling needed. Automatically handles ARIA `role="alertdialog"`.

**Confidence:** HIGH (verified from shadcn-vue docs)

---

### 4. Toast Notifications: Sonner

Replaces `v-snackbar`.

**Setup (App.vue):**
```vue
<script setup>
import { Toaster } from '@/components/ui/sonner'
</script>
<template>
  <div>
    <RouterView />
    <Toaster />  <!-- Place once at app root -->
  </div>
</template>
```

**Usage (anywhere in app):**
```typescript
import { toast } from 'vue-sonner'

// Replaces showSnackbar('User created', 'success')
toast.success('User created successfully')
toast.error('Failed to delete user')
toast.info('Pipeline started')
toast.warning('Session expiring')

// For async operations (replaces loading + success/error snackbar sequence)
toast.promise(authStore.deleteUser(userId), {
  loading: 'Deleting user...',
  success: 'User deleted successfully',
  error: 'Failed to delete user',
})
```

**Confidence:** HIGH (verified from shadcn-vue sonner docs)

---

### 5. Navigation Bar: Tailwind + shadcn-vue components

Replaces `v-app-bar`. No direct shadcn-vue equivalent exists — build from primitives.

```vue
<!-- App.vue — replaces v-app-bar -->
<header class="sticky top-0 z-50 w-full border-b bg-background/95 backdrop-blur">
  <div class="container flex h-14 items-center">
    <!-- Logo -->
    <KGDBLogo @click="router.push('/')" class="cursor-pointer" />

    <!-- Desktop nav links -->
    <nav class="hidden md:flex items-center gap-1 ml-6">
      <Button as-child variant="ghost"
        v-for="link in navLinks" :key="link.to"
        :class="{ 'text-primary': route.path.startsWith(link.to) }">
        <RouterLink :to="link.to">
          <component :is="link.icon" class="mr-1 h-4 w-4" />
          {{ link.label }}
        </RouterLink>
      </Button>
    </nav>

    <div class="ml-auto flex items-center gap-2">
      <!-- Theme toggle -->
      <Button variant="ghost" size="icon" @click="toggleColorMode">
        <SunIcon v-if="colorMode === 'dark'" class="h-4 w-4" />
        <MoonIcon v-else class="h-4 w-4" />
      </Button>

      <!-- Mobile menu trigger -->
      <Sheet v-model:open="mobileOpen" class="md:hidden">
        <SheetTrigger as-child>
          <Button variant="ghost" size="icon">
            <MenuIcon class="h-4 w-4" />
          </Button>
        </SheetTrigger>
        <SheetContent side="right">
          <!-- mobile nav list -->
        </SheetContent>
      </Sheet>
    </div>
  </div>
</header>
```

**Confidence:** MEDIUM (pattern derived from shadcn-vue Block examples and navigation examples; specifics of `as-child` prop and RouterLink composition verified)

---

### 6. Multi-Select with Chips (Complex)

Replaces `v-select multiple chips closable-chips`. No direct equivalent in shadcn-vue.

**Recommended pattern:** Combobox (Popover + Command) + TagsInput

```vue
<!-- MultiSelect.vue — reusable component for GeneTable filters -->
<template>
  <TagsInput v-model="selectedValues" class="w-full">
    <TagsInputItem v-for="item in selectedValues" :key="item" :value="item">
      <TagsInputItemText />
      <TagsInputItemDelete />
    </TagsInputItem>

    <ComboboxRoot v-model="open" :filter-function="filterFunction">
      <ComboboxAnchor>
        <TagsInputInput placeholder="Select sources..." as-child>
          <ComboboxInput />
        </TagsInputInput>
      </ComboboxAnchor>
      <ComboboxPortal>
        <ComboboxContent>
          <ComboboxViewport>
            <ComboboxItem v-for="option in filteredOptions" :key="option.value" :value="option.value">
              {{ option.label }}
            </ComboboxItem>
          </ComboboxViewport>
        </ComboboxContent>
      </ComboboxPortal>
    </ComboboxRoot>
  </TagsInput>
</template>
```

**Install:**
```bash
npx shadcn-vue@latest add tags-input combobox command popover
```

**Confidence:** MEDIUM (pattern confirmed from shadcn-vue GitHub discussion #869 and community examples; no single-component equivalent exists in shadcn-vue)

---

### 7. Range Slider (Dual Thumb)

Replaces `v-range-slider`.

```vue
<!-- RangeFilter.vue -->
<script setup lang="ts">
import { Slider } from '@/components/ui/slider'
const props = defineProps<{ min: number; max: number; modelValue: [number, number] }>()
const emit = defineEmits(['update:modelValue'])
</script>
<template>
  <div class="flex items-center gap-2">
    <span class="text-xs tabular-nums w-8 text-right">{{ modelValue[0] }}</span>
    <Slider
      :min="min"
      :max="max"
      :step="1"
      :model-value="modelValue"
      @update:model-value="emit('update:modelValue', $event)"
      class="flex-1"
    />
    <span class="text-xs tabular-nums w-8">{{ modelValue[1] }}</span>
  </div>
</template>
```

**Key note:** The shadcn-vue `Slider` passes an array for multi-thumb. Confirm whether `model-value` with array produces two thumbs — this is documented in Radix Vue's Slider primitive (verified: `defaultValue: [25, 75]` creates range slider).

**Confidence:** MEDIUM (Radix Vue docs confirm array value creates dual thumb; shadcn-vue wraps Radix Vue slider — behavior should be identical)

---

### 8. Accordion (Expansion Panels for Evidence Cards)

Replaces `v-expansion-panels`.

```vue
<!-- EvidenceCard.vue -->
<Accordion type="single" collapsible class="w-full">
  <AccordionItem :value="evidence.source_name">
    <AccordionTrigger class="py-3">
      <div class="flex items-center justify-between w-full mr-2">
        <div class="flex items-center gap-3">
          <Avatar class="h-8 w-8">
            <AvatarFallback :class="sourceColorClass">
              <component :is="sourceIcon" class="h-4 w-4 text-white" />
            </AvatarFallback>
          </Avatar>
          <div class="text-left">
            <p class="text-sm font-medium">{{ evidence.source_name }}</p>
            <p class="text-xs text-muted-foreground">{{ evidenceSummary }}</p>
          </div>
        </div>
        <Badge variant="outline" v-if="evidence.normalized_score">
          Score: {{ formatScore(evidence.normalized_score) }}
        </Badge>
      </div>
    </AccordionTrigger>
    <AccordionContent>
      <component :is="evidenceComponent" :evidence-data="evidence.evidence_data" />
    </AccordionContent>
  </AccordionItem>
</Accordion>
```

**Confidence:** HIGH (verified from shadcn-vue Accordion docs)

---

### 9. Dark Mode Toggle

Replaces Vuetify's `useTheme()`.

```typescript
// composables/useTheme.ts
import { useColorMode } from '@vueuse/core'

export function useAppTheme() {
  const colorMode = useColorMode()

  function toggleTheme() {
    colorMode.value = colorMode.value === 'dark' ? 'light' : 'dark'
  }

  return { colorMode, toggleTheme }
}
```

**CSS setup (main.css):**
```css
@layer base {
  :root {
    --primary: oklch(0.55 0.19 200);  /* sky blue */
    /* ... all other CSS variables */
  }
  .dark {
    --primary: oklch(0.75 0.19 200);  /* lighter for dark mode */
    /* ... dark mode overrides */
  }
}
```

**Note:** `@vueuse/core` must be added as a dependency. It is not currently in package.json.

**Confidence:** HIGH (verified from shadcn-vue Vite dark mode docs)

---

### 10. Breadcrumb

Replaces `v-breadcrumbs`.

```vue
<Breadcrumb>
  <BreadcrumbList>
    <BreadcrumbItem>
      <BreadcrumbLink as-child>
        <RouterLink to="/">Home</RouterLink>
      </BreadcrumbLink>
    </BreadcrumbItem>
    <BreadcrumbSeparator />
    <BreadcrumbItem>
      <BreadcrumbLink as-child>
        <RouterLink to="/genes">Genes</RouterLink>
      </BreadcrumbLink>
    </BreadcrumbItem>
    <BreadcrumbSeparator />
    <BreadcrumbItem>
      <BreadcrumbPage>{{ gene.approved_symbol }}</BreadcrumbPage>
    </BreadcrumbItem>
  </BreadcrumbList>
</Breadcrumb>
```

**Confidence:** HIGH (verified from shadcn-vue docs)

---

### 11. Icon System Migration

**From:** `@mdi/font` CSS font + `v-icon icon="mdi-..."` (431 usages)
**To:** `lucide-vue-next` individual SVG components

**Install:**
```bash
npm install lucide-vue-next
npm uninstall @mdi/font
```

**Pattern:**
```vue
<!-- Before -->
<v-icon icon="mdi-dna" />

<!-- After -->
<DnaIcon class="h-4 w-4" />
```

**Import (named, tree-shakable):**
```typescript
import { Dna as DnaIcon, Database, ChevronRight, Search, X, Check } from 'lucide-vue-next'
```

**MDI-to-Lucide mapping required for all 431 usages.** Common mappings:
- `mdi-dna` → `Dna`
- `mdi-magnify` → `Search`
- `mdi-account` → `User`
- `mdi-delete` → `Trash2`
- `mdi-pencil` → `Pencil`
- `mdi-refresh` → `RefreshCw`
- `mdi-chevron-right` → `ChevronRight`
- `mdi-information-outline` → `Info`
- `mdi-check-circle` → `CheckCircle2`
- `mdi-alert-circle` → `AlertCircle`
- `mdi-download` → `Download`
- `mdi-close` → `X`
- `mdi-filter` → `Filter`
- `mdi-login` → `LogIn`
- `mdi-logout` → `LogOut`
- `mdi-eye` / `mdi-eye-off` → `Eye` / `EyeOff`
- `mdi-open-in-new` → `ExternalLink`
- `mdi-dots-vertical` → `MoreVertical`
- `mdi-view-dashboard` → `LayoutDashboard`
- `mdi-database-sync` → `DatabaseZap`
- `mdi-chart-scatter-plot` → `ScatterChart`

**Note:** Lucide does not have a 1:1 mapping for every MDI icon. Scientific/medical icons like `mdi-dna` have direct Lucide equivalents, but some may need alternatives or custom SVGs.

**Confidence:** MEDIUM (Lucide icon names verified; completeness of MDI mapping for all 431 usages is LOW confidence — requires per-icon audit)

---

## Missing Vuetify Features Without shadcn-vue Equivalents

These features have no direct shadcn-vue component and require custom implementation:

| Vuetify Feature | Usage Count | Custom Solution |
|----------------|-------------|-----------------|
| `v-progress-linear` determinate | GeneTable evidence strength bars | shadcn-vue `Progress` component (`value` prop) |
| `v-expand-transition` | GeneDetail filter panel show/hide | Vue `<Transition>` with CSS `grid-template-rows: 0fr → 1fr` trick, or `vue-collapsed` npm package |
| `v-app-bar` | App-level sticky header | Plain `<header>` with Tailwind `sticky top-0 z-50 backdrop-blur` |
| `v-toolbar` | LogViewer drawer header | Plain `<div>` with Tailwind styling |
| `v-list` / `v-list-item` | Navigation drawer menus | Plain HTML list with Tailwind + shadcn-vue `Button variant="ghost"` |
| `v-container` / `v-row` / `v-col` | Layout grid (396 usages) | Tailwind CSS `container`, `grid`, `flex` utilities |
| `v-spacer` | Flex spacing | Tailwind `ml-auto` or `justify-between` |
| `v-divider` | Section separators | shadcn-vue `Separator` |
| `v-menu` activator pattern | Overflow chip menu in table cells | shadcn-vue `Popover` with `PopoverTrigger` + `PopoverContent` |

---

## Sources

- [shadcn-vue official site](https://www.shadcn-vue.com/) — component list, theming, dark mode
- [shadcn-vue GitHub (unovue/shadcn-vue)](https://github.com/unovue/shadcn-vue) — issues, discussions, multi-select discussion #869
- [shadcn-vue data table docs](https://next.shadcn-vue.com/docs/components/data-table) — TanStack Table integration pattern
- [TanStack Table Vue pagination guide](https://tanstack.com/table/v8/docs/framework/vue/examples/pagination) — server-side pagination
- [TanStack Table sorting guide](https://tanstack.com/table/v8/docs/api/features/sorting) — manualSorting, onSortingChange
- [TanStack Table pagination APIs](https://tanstack.com/table/v8/docs/api/features/pagination) — manualPagination, rowCount, pageCount
- [shadcn-vue Form (VeeValidate) docs](https://radix.shadcn-vue.com/docs/components/form) — FormField API, useForm pattern
- [VeeValidate Zod integration](https://vee-validate.logaretm.com/v4/integrations/zod-schema-validation/) — toTypedSchema
- [shadcn-vue Sonner docs](https://www.shadcn-vue.com/docs/components/sonner) — toast API
- [shadcn-vue Tailwind v4 migration](https://v3.shadcn-vue.com/docs/tailwind-v4) — CSS variable changes, OKLCH
- [shadcn-vue Dark Mode Vite](https://www.shadcn-vue.com/docs/dark-mode/vite) — useColorMode pattern
- [shadcn-vue Sidebar](https://next.shadcn-vue.com/docs/components/sidebar) — admin layout pattern
- [Radix Vue Slider](https://www.radix-vue.com/components/slider) — multi-thumb slider (array value)
- [Lucide Vue Next](https://lucide.dev/guide/packages/lucide-vue-next) — tree-shakable icon system
- [vue-sonner on CodeSandbox](https://codesandbox.io/examples/package/vue-sonner) — usage examples

---

*Feature research for: Frontend migration (Vuetify 3 to shadcn-vue)*
*Researched: 2026-02-28*
