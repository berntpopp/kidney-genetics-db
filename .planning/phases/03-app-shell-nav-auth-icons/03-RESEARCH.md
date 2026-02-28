# Phase 3: App Shell, Navigation, Auth, Feedback, Icons — Research

**Researched:** 2026-02-28
**Domain:** App shell migration (Vuetify layout → Tailwind/shadcn-vue), auth forms, toast notifications, icon replacement
**Confidence:** HIGH (codebase directly inspected; prior research docs verified)

---

## Summary

Phase 3 replaces the entire application skeleton — header, footer, navigation, mobile drawer, dark mode, auth modals, toast notifications, and icons — with Tailwind/shadcn-vue equivalents. Everything inside the `<router-view>` (page content) stays unchanged. This research directly inspected every component that must migrate.

**What exists today:** `App.vue` is a single Vuetify monolith wrapping `<v-app>` with inline nav bar, navigation drawer, and `<v-main>`. `AppFooter.vue` uses `<v-footer>`. Auth modals use `<v-dialog>` + `<v-form>` with hand-rolled validation rules. Snackbars are local reactive state (`v-snackbar`) in 9 files plus `window.snackbar` calls in composables. Icons are all MDI (`v-icon`) throughout. Dark mode is Vuetify's `useTheme()`.

**Infrastructure from Phases 1–2 already in place:** TypeScript strict mode, Tailwind v4 + CSS layer coexistence, shadcn-vue initialized (components.json, lib/utils.ts, Button component + test), OKLCH color tokens, lucide-vue-next installed, @vueuse/core installed, Vitest pipeline working. **Still missing for this phase:** vue-sonner, vee-validate, @vee-validate/zod, zod.

**Primary recommendation:** Build the Tailwind layout shell first (App.vue replacement), then auth modals, then wire up toast provider + icon map — in that order. Each sub-plan should leave the app in a working state.

---

## Standard Stack

### Core (already installed — verified in node_modules)

| Library | Installed Version | Purpose | Status |
|---------|------------------|---------|--------|
| tailwindcss | 4.2.x | Utility-first CSS | INSTALLED |
| @tailwindcss/vite | 4.2.x | Vite plugin | INSTALLED |
| shadcn-vue CLI | latest | Component scaffolding | INITIALIZED (components.json exists) |
| reka-ui | 2.8.2 | Headless UI primitives | INSTALLED |
| lucide-vue-next | 0.475.0 | Icon set | INSTALLED |
| @vueuse/core | 14.2.1 | useColorMode() | INSTALLED |
| class-variance-authority | 0.7.x | Variant management | INSTALLED |
| clsx | 2.x | Class merging | INSTALLED |
| tailwind-merge | 3.5.0 | Tailwind deduplication | INSTALLED |

### Needs to be Installed (not in package.json or node_modules)

| Library | Version | Purpose | Install Command |
|---------|---------|---------|-----------------|
| vue-sonner | ^2.0.9 | Toast notifications | `npm install vue-sonner` |
| vee-validate | ^4.15.1 | Form validation | `npm install vee-validate` |
| @vee-validate/zod | ^4.15.1 | Zod adapter | `npm install @vee-validate/zod` |
| zod | ^3.24.x | Schema validation | `npm install zod@^3.24.0` |

**Critical constraint:** Install `zod@^3.24.0` explicitly — Zod v4 (4.3.6 on npm) is incompatible with `@vee-validate/zod` (peer dep pinned to `zod@^3.24.0`, issues #5027/#5024 unresolved as of Feb 2026).

```bash
cd /home/bernt-popp/development/kidney-genetics-db/frontend
npm install vue-sonner@^2.0.0 vee-validate@^4.15.0 @vee-validate/zod@^4.15.0 zod@^3.24.0
```

### shadcn-vue Components to Add (not yet scaffolded)

Only `button` is currently installed. This phase needs:

| Component | CLI Command | Used For |
|-----------|-------------|---------|
| NavigationMenu | `npx shadcn-vue@latest add navigation-menu` | Desktop nav bar |
| Sheet | `npx shadcn-vue@latest add sheet` | Mobile drawer |
| DropdownMenu | `npx shadcn-vue@latest add dropdown-menu` | User menu |
| Avatar | `npx shadcn-vue@latest add avatar` | User avatar in header |
| Breadcrumb | `npx shadcn-vue@latest add breadcrumb` | Page breadcrumbs |
| Dialog | `npx shadcn-vue@latest add dialog` | Auth modals |
| Form | `npx shadcn-vue@latest add form` | Validated form fields |
| Input | `npx shadcn-vue@latest add input` | Form text inputs |
| Label | `npx shadcn-vue@latest add label` | Form labels |
| Separator | `npx shadcn-vue@latest add separator` | Visual dividers |
| Badge | `npx shadcn-vue@latest add badge` | Role badge in user menu |
| Sonner | `npx shadcn-vue@latest add sonner` | Toast provider wrapper |
| Tooltip | `npx shadcn-vue@latest add tooltip` | Icon tooltips |

**Note:** shadcn-vue's `sonner` component wraps `vue-sonner`. Install `vue-sonner` as a dependency first, then add the shadcn-vue component.

---

## Architecture Patterns

### Target App Structure (replaces v-app/v-main)

```
src/
├── layouts/                  # NEW — extracted from App.vue
│   ├── AppHeader.vue         # Sticky header (Tailwind + shadcn NavigationMenu)
│   └── AppFooter.vue         # Footer (replaces components/AppFooter.vue)
├── components/
│   ├── auth/
│   │   ├── LoginModal.vue    # Migrated: Dialog + Form + vee-validate
│   │   ├── ForgotPasswordModal.vue
│   │   ├── ChangePasswordModal.vue
│   │   └── UserMenu.vue      # Migrated: DropdownMenu + Avatar
│   └── ui/
│       ├── button/           # Already installed
│       ├── navigation-menu/  # Install via CLI
│       ├── sheet/            # Install via CLI
│       ├── dropdown-menu/    # Install via CLI
│       ├── avatar/           # Install via CLI
│       ├── breadcrumb/       # Install via CLI
│       ├── dialog/           # Install via CLI
│       ├── form/             # Install via CLI
│       ├── input/            # Install via CLI
│       ├── label/            # Install via CLI
│       ├── separator/        # Install via CLI
│       ├── badge/            # Install via CLI
│       ├── sonner/           # Install via CLI
│       └── tooltip/          # Install via CLI
├── utils/
│   └── icons.ts              # NEW — MDI → Lucide mapping registry
App.vue                       # Replace v-app structure with Tailwind layout
```

### Pattern 1: App Shell Replacement

**Replace `<v-app>` with Tailwind layout:**

```vue
<!-- App.vue (new) -->
<template>
  <div class="min-h-screen flex flex-col bg-background text-foreground">
    <AppHeader />
    <main class="flex-1">
      <router-view v-slot="{ Component }">
        <transition name="fade" mode="out-in">
          <component :is="Component" />
        </transition>
      </router-view>
    </main>
    <AppFooter />
    <LogViewer />
    <Toaster />
  </div>
</template>
```

**Dark mode sync during coexistence:** The `<div>` element needs Vuetify dark mode to stay synchronized with the shadcn-vue `.dark` class on `<html>`. From PITFALLS.md:

```typescript
// In App.vue setup — sync Vuetify dark state to html.dark class
import { useTheme } from 'vuetify'
import { watch } from 'vue'

const theme = useTheme()
watch(
  () => theme.global.current.value.dark,
  (isDark) => {
    document.documentElement.classList.toggle('dark', isDark)
  },
  { immediate: true }
)
```

This runs during coexistence (Phases 3–7) so both Vuetify components and shadcn-vue components respond to the same toggle. In Phase 8, Vuetify is removed and `useColorMode()` becomes the sole authority.

### Pattern 2: Dark Mode Toggle (useColorMode + Vuetify sync)

**New `useAppTheme` composable:**

```typescript
// src/composables/useAppTheme.ts
import { computed, watch } from 'vue'
import { useColorMode } from '@vueuse/core'
import { useTheme } from 'vuetify'

export function useAppTheme() {
  const colorMode = useColorMode({
    attribute: 'class',
    modes: { light: 'light', dark: 'dark' },
    storageKey: 'kgdb-color-mode',
  })

  const vuetifyTheme = useTheme()

  const isDark = computed(() => colorMode.value === 'dark')

  // Sync VueUse colorMode → Vuetify theme (so Vuetify components respond too)
  watch(isDark, (dark) => {
    vuetifyTheme.change(dark ? 'dark' : 'light')
  }, { immediate: true })

  // Sync Vuetify → html class (so shadcn-vue components respond)
  // This handles the case where Vuetify theme is changed from other sources
  watch(
    () => vuetifyTheme.global.current.value.dark,
    (dark) => {
      document.documentElement.classList.toggle('dark', dark)
    },
    { immediate: true }
  )

  const toggleTheme = () => {
    colorMode.value = isDark.value ? 'light' : 'dark'
  }

  return { isDark, toggleTheme, colorMode }
}
```

**Storage key:** `kgdb-color-mode` (localStorage). System default handled by `useColorMode()` automatically — it reads `prefers-color-scheme` as initial value before any manual override.

### Pattern 3: Navigation Structure

**Current nav links (from App.vue inspection):**
- Gene Browser → `/genes`
- Data Overview → `/dashboard`
- Network Analysis → `/network-analysis`
- Data Sources → `/data-sources`
- About → `/about`

Per CONTEXT.md decision: desktop nav = text-only horizontal links, NO icons next to labels. Active state indicator required.

**Desktop nav active state pattern:**
```vue
<!-- Using router active class + Tailwind -->
<RouterLink
  v-for="link in navLinks"
  :key="link.to"
  :to="link.to"
  class="text-sm font-medium transition-colors hover:text-primary"
  :class="{
    'text-primary border-b-2 border-primary': isActive(link.to),
    'text-muted-foreground': !isActive(link.to)
  }"
>
  {{ link.label }}
</RouterLink>
```

**Active state detection** (App.vue currently uses `$route.path.startsWith('/genes')` for gene routes, exact match elsewhere):
```typescript
import { useRoute } from 'vue-router'
const route = useRoute()
const isActive = (path: string) => {
  if (path === '/genes') return route.path.startsWith('/genes')
  return route.path === path
}
```

### Pattern 4: Mobile Drawer (shadcn-vue Sheet)

Per CONTEXT.md: drawer side is Claude's Discretion. Use **left** side (`side="left"`) — this is the shadcn-vue Sheet default and the conventional position for navigation drawers on mobile (right side is used for context panels).

```vue
<!-- Mobile menu toggle (in AppHeader.vue) -->
<Button variant="ghost" size="icon" class="md:hidden" @click="drawerOpen = true">
  <Menu class="size-5" />
</Button>

<Sheet v-model:open="drawerOpen">
  <SheetContent side="left" class="w-72 px-0">
    <SheetHeader class="px-4 pb-4 border-b">
      <KGDBLogo size="32" variant="with-text" />
    </SheetHeader>
    <!-- nav links + user section + theme toggle -->
  </SheetContent>
</Sheet>
```

### Pattern 5: User Menu (DropdownMenu + Avatar)

Current `UserMenu.vue` uses `<v-menu>` with username display, role chip, My Profile, Admin Panel (conditional), and Logout. New structure:

```vue
<DropdownMenu>
  <DropdownMenuTrigger as-child>
    <Button variant="ghost" class="flex items-center gap-2">
      <Avatar class="size-8">
        <AvatarFallback>{{ userInitials }}</AvatarFallback>
      </Avatar>
      <span class="text-sm font-medium">{{ authStore.user?.username }}</span>
      <ChevronDown class="size-4 text-muted-foreground" />
    </Button>
  </DropdownMenuTrigger>
  <DropdownMenuContent align="end" class="w-56">
    <DropdownMenuLabel>
      <div class="font-medium">{{ authStore.user?.username }}</div>
      <div class="text-xs text-muted-foreground">{{ authStore.user?.email }}</div>
    </DropdownMenuLabel>
    <DropdownMenuSeparator />
    <DropdownMenuItem @click="router.push('/profile')">
      <CircleUser class="size-4 mr-2" /> My Profile
    </DropdownMenuItem>
    <DropdownMenuItem v-if="authStore.isAdmin" @click="router.push('/admin')">
      <ShieldEllipsis class="size-4 mr-2" /> Admin Panel
    </DropdownMenuItem>
    <DropdownMenuSeparator />
    <DropdownMenuItem @click="handleLogout">
      <LogOut class="size-4 mr-2" /> Logout
    </DropdownMenuItem>
  </DropdownMenuContent>
</DropdownMenu>
```

### Pattern 6: Auth Modals (Dialog + Form + vee-validate)

**Current state:** All 3 auth modals use `<v-dialog>` + `<v-form>` with hand-rolled validation rules (arrays of functions). No vee-validate currently installed.

**Migration pattern with vee-validate + Zod:**

```typescript
// Schema defined as static const (NOT in computed — see Pitfall 11 in PITFALLS.md)
import { z } from 'zod'
import { toTypedSchema } from '@vee-validate/zod'
import { useForm } from 'vee-validate'

const loginSchema = toTypedSchema(z.object({
  username: z.string().min(1, 'Required'),
  password: z.string().min(1, 'Required'),
}))

const { handleSubmit, defineField, errors } = useForm({
  validationSchema: loginSchema,
})

const [username, usernameAttrs] = defineField('username', {
  validateOnBlur: true,  // validates when user leaves field
  validateOnInput: true, // validates as user types (per CONTEXT.md requirement)
})
const [password, passwordAttrs] = defineField('password', {
  validateOnBlur: true,
  validateOnInput: true,
})
```

**Dialog open/close pattern (controlled externally with v-model):**

`LoginModal.vue` currently has its own activator button embedded in it (not in App.vue). The CONTEXT.md decision keeps both the header login button AND the standalone `/login` page. The modal variant should be triggerable from the header without embedding the trigger in the modal itself — use a prop-controlled `v-model:open` pattern:

```vue
<!-- LoginModal.vue: no internal activator -->
<Dialog :open="open" @update:open="$emit('update:open', $event)">
  <DialogContent class="sm:max-w-[400px]">
    <!-- form content -->
  </DialogContent>
</Dialog>
```

```vue
<!-- AppHeader.vue: controls the modal -->
<Button v-if="!authStore.isAuthenticated" variant="default" @click="loginModalOpen = true">
  <LogIn class="size-4 mr-2" />
  Login
</Button>
<LoginModal v-model:open="loginModalOpen" @login-success="handleLoginSuccess" />
```

**Login success flow (per CONTEXT.md):**
1. `authStore.login()` resolves successfully
2. Emit `login-success` event to parent (AppHeader)
3. AppHeader: toast success ("Logged in as [username]"), close modal, header re-renders with UserMenu
4. Do NOT use `router.go(0)` (full page reload) — current LoginModal does this but it's wrong. Header auth state is reactive via `authStore.isAuthenticated`, no reload needed.

### Pattern 7: Password Complexity Checklist (ChangePasswordModal)

Per CONTEXT.md: show all 5 complexity requirements upfront with live checkmarks.

Current `ChangePasswordModal.vue` has a `complexity` validation rule that checks all 4 conditions (uppercase, lowercase, number, special char) plus a minimum length rule. The new UX shows a requirements checklist:

```typescript
// Computed requirements display from password reactive value
const passwordRequirements = computed(() => [
  { label: 'At least 8 characters', met: password.value?.length >= 8 },
  { label: 'Uppercase letter (A–Z)', met: /[A-Z]/.test(password.value ?? '') },
  { label: 'Lowercase letter (a–z)', met: /[a-z]/.test(password.value ?? '') },
  { label: 'Number (0–9)', met: /[0-9]/.test(password.value ?? '') },
  { label: 'Special character (!@#$%...)', met: /[!@#$%^&*(),.?":{}|<>]/.test(password.value ?? '') },
])
```

```vue
<!-- Below new password field -->
<ul class="mt-2 space-y-1 text-xs">
  <li v-for="req in passwordRequirements" :key="req.label"
      class="flex items-center gap-2"
      :class="req.met ? 'text-green-600 dark:text-green-400' : 'text-muted-foreground'">
    <CheckCircle v-if="req.met" class="size-3" />
    <Circle v-else class="size-3" />
    {{ req.label }}
  </li>
</ul>
```

### Pattern 8: Toast System (vue-sonner)

**Provider setup (in App.vue):**
```vue
<!-- App.vue template -->
<Toaster position="bottom-right" :expand="false" rich-colors />
```

```typescript
// App.vue script
import { Toaster } from '@/components/ui/sonner'
```

**Usage from anywhere via `toast()`:**
```typescript
import { toast } from 'vue-sonner'

// Success (auto-dismiss ~5s per CONTEXT.md)
toast.success('Logged in as admin', { duration: 5000 })

// Error (persistent per CONTEXT.md)
toast.error('Login failed: Invalid credentials', { duration: Infinity })

// With action
toast.success('Gene deleted', {
  duration: 5000,
  action: { label: 'Undo', onClick: () => handleUndo() }
})

// Promise pattern (TFBK-03)
toast.promise(apiCall(), {
  loading: 'Saving...',
  success: 'Saved successfully',
  error: 'Failed to save'
})
```

**Global toast bridge for window.snackbar (for composables):**

Currently `useNetworkUrlState.ts` and `NetworkAnalysis.vue` call `window.snackbar.success()` and `window.snackbar.error()`. In Phase 3, set up a bridge in `main.ts`:

```typescript
// main.ts — bridge window.snackbar to vue-sonner
import { toast } from 'vue-sonner'

window.snackbar = {
  success: (msg: string) => toast.success(msg, { duration: 5000 }),
  error: (msg: string) => toast.error(msg, { duration: Infinity }),
}
```

This satisfies the existing type declaration in `env.d.ts` (`window.snackbar?: { success, error }`) without needing to refactor the 10 usages in this phase.

### Pattern 9: Icon Map Module

Per CONTEXT.md/REQUIREMENTS: create `src/utils/icons.ts` mapping MDI names to Lucide components.

**Full audit completed in Phase 1** (`.planning/phases/01-foundation-setup/01-icon-audit.md`): 198 unique MDI icons mapped, all have Lucide equivalents, 1 dropped (`mdi-vuejs`).

```typescript
// src/utils/icons.ts — centralized icon registry
import {
  User, CircleUser, Users, UserCheck, UserX, UserPlus, UserSearch,
  ChevronDown, ChevronRight, LogIn, LogOut, Sun, Moon, Menu, X,
  Dna, LayoutDashboard, ChartScatter, RefreshCw, Info, Search,
  Server, Database, Cloud, Github, FileSearch, Settings, Shield,
  ShieldCheck, ShieldEllipsis, Circle, CircleCheck, Check, CheckCheck,
  // ... all mapped icons
} from 'lucide-vue-next'
import type { Component } from 'vue'

export const MdiToLucide: Record<string, Component> = {
  'mdi-account': User,
  'mdi-account-circle': CircleUser,
  'mdi-account-group': Users,
  'mdi-chevron-down': ChevronDown,
  'mdi-chevron-right': ChevronRight,
  'mdi-login': LogIn,
  'mdi-logout': LogOut,
  'mdi-weather-sunny': Sun,
  'mdi-weather-night': Moon,
  'mdi-dna': Dna,
  'mdi-view-dashboard': LayoutDashboard,
  'mdi-chart-scatter-plot': ChartScatter,
  'mdi-database-sync': RefreshCw,
  'mdi-information': Info,
  'mdi-information-outline': Info,
  'mdi-github': Github,
  'mdi-server': Server,
  'mdi-database': Database,
  'mdi-cloud-outline': Cloud,
  'mdi-text-box-search-outline': FileSearch,
  'mdi-refresh': RefreshCw,
  'mdi-lock': Lock,
  'mdi-lock-plus': LockKeyholeOpen,
  'mdi-lock-check': ShieldCheck,
  'mdi-lock-reset': KeyRound,
  'mdi-eye': Eye,
  'mdi-eye-off': EyeOff,
  'mdi-email': Mail,
  'mdi-shield-crown': ShieldEllipsis,
  // ... complete set from 01-icon-audit.md
}

// Re-export Lucide components used directly (no mdi- prefix needed)
export {
  User, CircleUser, Users, ChevronDown, ChevronRight, LogIn, LogOut,
  Sun, Moon, Menu, X, Dna, LayoutDashboard, RefreshCw, Info, Search,
  // ... all others
} from 'lucide-vue-next'
```

**Decision from CONTEXT.md:** No custom SVGs. All 198 icons covered by Lucide equivalents from the icon audit.

### Pattern 10: Breadcrumb Component Usage

Breadcrumbs currently live in **page views**, not in the app shell. `publicBreadcrumbs.ts` and `adminBreadcrumbs.ts` generate `BreadcrumbItem[]` arrays for `v-breadcrumbs`. Phase 3 only migrates `AdminHeader.vue`'s breadcrumb (it's inside the shell). The 18+ other page-level `v-breadcrumbs` are migrated in later phases when those pages are touched.

For `AdminHeader.vue` breadcrumb migration:
```vue
<Breadcrumb>
  <BreadcrumbList>
    <template v-for="(item, index) in breadcrumbs" :key="item.title">
      <BreadcrumbItem>
        <BreadcrumbLink v-if="!item.disabled && item.to" :href="item.to">
          {{ item.title }}
        </BreadcrumbLink>
        <BreadcrumbPage v-else>{{ item.title }}</BreadcrumbPage>
      </BreadcrumbItem>
      <BreadcrumbSeparator v-if="index < breadcrumbs.length - 1">
        <ChevronRight class="size-3.5" />
      </BreadcrumbSeparator>
    </template>
  </BreadcrumbList>
</Breadcrumb>
```

### Pattern 11: Footer Preservation

The footer has these elements (from `AppFooter.vue` inspection):
1. **Version info button** — triggers a popover/card with frontend/backend/database versions + environment + timestamp + refresh button
2. **GitHub link** — icon button linking to https://github.com
3. **Log Viewer button** — icon button with error count badge, triggers `logStore.showViewer()`

**Notable:** The version card uses `<v-menu>` (popover on click). Migration to shadcn-vue `Popover` component (not listed in the "must add" list above — add it).

| Vuetify Component | shadcn-vue Replacement |
|------------------|----------------------|
| `v-footer` | `<footer>` with Tailwind classes |
| `v-menu` (version popover) | `Popover` + `PopoverContent` |
| `v-card` (version card) | `Card` + `CardContent` |
| `v-list`, `v-list-item` | Custom Tailwind list |
| `v-badge` (error count) | Custom Tailwind badge or shadcn `Badge` |
| `v-btn icon` | shadcn `Button` variant="ghost" size="icon" |

**Add to shadcn components list:** `npx shadcn-vue@latest add popover card`

### Recommended Project Structure Change

**New directory needed:** `src/layouts/`

Move header and footer out of App.vue (split extraction):
- `App.vue` → thin layout shell only, imports `AppHeader` and `AppFooter`
- `src/layouts/AppHeader.vue` — new file (header content)
- `src/layouts/AppFooter.vue` — new file (replaces `src/components/AppFooter.vue`)
- `src/components/AppFooter.vue` — delete after migration

### Anti-Patterns to Avoid

- **Do NOT use `router.go(0)` on login success.** Current `LoginModal.vue` does this. Auth state is reactive via Pinia — the header updates automatically when `authStore.isAuthenticated` changes.
- **Do NOT embed the Dialog trigger inside the Modal component.** Current `LoginModal.vue` has `<template #activator>`. New modals should be controlled by the parent via `v-model:open`.
- **Do NOT define Zod schemas inside `computed()`.** This breaks TypeScript type inference for `handleSubmit` (PITFALLS.md Pitfall 11).
- **Do NOT import all Lucide icons globally.** Always use named imports. `import * as LucideIcons` adds ~500KB to the bundle.
- **Do NOT keep `tailwindcss()` before `vue()` in Vite plugins.** Current `vite.config.ts` has `plugins: [tailwindcss(), vue()]` — STACK.md says `vue()` should come first. This discrepancy was established in Phase 1 and the build works, so do not change it now.

---

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| Form validation | Custom rule arrays | vee-validate + Zod | Error state management, blur/change triggers, type inference |
| Toast notifications | `v-snackbar` state | vue-sonner `toast()` | Stacking, positioning, auto-dismiss, promise patterns |
| Password visibility toggle | Custom logic | vee-validate `defineField` + Input type binding | Already handles all edge cases |
| Color mode persistence | Custom localStorage logic | `useColorMode()` from @vueuse/core | System default, manual override, localStorage key |
| Icon abstraction layer | Custom icon component | Lucide Vue Next direct imports | Tree-shakable, typed, no custom wrapper needed |
| Dark mode HTML class sync | Manual watch | `useColorMode({ attribute: 'class' })` | VueUse handles system detection + persistence + class toggle |

---

## Common Pitfalls

### Pitfall 1: Dark Mode Dual System — Two Themes Diverge

**What goes wrong:** New shadcn-vue header shows light theme while old Vuetify page content shows dark theme (or vice versa).

**Why it happens:** Vuetify uses `theme.change('dark')` which adds `.v-theme--dark` to the root element. shadcn-vue needs `.dark` on `<html>`. During coexistence they run independently.

**How to avoid:** Implement the `useAppTheme` composable (Pattern 2 above) with bidirectional sync. The `{ immediate: true }` option ensures sync on first render. Test by toggling the dark mode button and verifying both Vuetify components (still on the page) and new shadcn-vue components both update.

**Warning signs:** Toggling the theme button makes the nav dark but the page content stays light.

### Pitfall 2: LoginModal Activator vs. Controlled Pattern

**What goes wrong:** The current `LoginModal.vue` has its own `<template #activator>` with a login button. If you keep this pattern, App.vue cannot control the modal state (e.g., cannot close it programmatically after a login event from a different trigger).

**How to avoid:** Remove the activator from the modal. Use `v-model:open` controlled from the parent (AppHeader). The standalone `/login` page is a separate route — it does not use the modal.

### Pitfall 3: Zod v4 vs v3 Conflict

**What goes wrong:** `npm install zod` installs Zod v4 (latest). `@vee-validate/zod` fails with peer dep errors. `toTypedSchema()` produces `Record<string, any>` instead of typed form values.

**How to avoid:** Always specify `zod@^3.24.0` in the install command. Check `package.json` after install to verify `"zod": "^3.24.x"`.

### Pitfall 4: vite.config.ts Plugin Order

**Note:** The current `vite.config.ts` has `plugins: [tailwindcss(), vue()]`. STACK.md recommended `vue()` first. This was established in Phase 1 and works correctly. Do NOT reorder the plugins — it would be an unnecessary change and may introduce regressions.

### Pitfall 5: shadcn-vue Form Component vs useForm Composable

**What goes wrong:** Confusion between two vee-validate integration styles:
1. Composable API: `useForm()` + `defineField()` — used in `<script setup>`
2. Component API: `<Form>` + `<Field>` components — used in template

**How to avoid:** Use the composable API (`useForm` + `defineField`) for all auth forms. The shadcn-vue `Form` component wrappers (`FormField`, `FormItem`, `FormLabel`, `FormMessage`) provide the layout structure — they work with both APIs but are designed to complement the composable approach.

### Pitfall 6: vee-validate validateOnInput Triggers

**What goes wrong:** Setting `validateOnInput: true` without a debounce causes validation to fire on every keystroke, which is jarring if you show inline errors immediately while the user is still typing.

**How to avoid:** Use `validateOnBlur: true` + `validateOnInput: true` together — vee-validate will only show errors after the first blur, then continuously validate on subsequent input. This matches the CONTEXT.md requirement for "real-time" per-field errors.

### Pitfall 7: window.snackbar Before Toaster is Mounted

**What goes wrong:** `window.snackbar` bridge is set up in `main.ts`, but `vue-sonner`'s `toast()` function requires the `<Toaster>` component to be mounted in the Vue component tree to actually display toasts.

**How to avoid:** The `<Toaster>` component goes into `App.vue` template. The `window.snackbar` bridge in `main.ts` simply calls `toast()` from `vue-sonner` — the Sonner library queues toasts if the provider isn't mounted yet, displaying them once it mounts. No special ordering is required.

### Pitfall 8: AppHeader.vue in src/layouts/ vs src/components/

**What goes wrong:** The ARCHITECTURE.md target state shows `src/layouts/` directory. The current project doesn't have it. If the planner puts AppHeader.vue in `src/components/` instead, it violates the target architecture and adds tech debt.

**How to avoid:** Create `src/layouts/` directory as part of Plan 03-01. Place `AppHeader.vue` and `AppFooter.vue` there. `App.vue` imports from `@/layouts/`.

---

## Code Examples

### App.vue Shell Structure

```typescript
// Source: ARCHITECTURE.md Pattern 4 + current App.vue inspection
// src/App.vue — new shell (no v-app)
<script setup lang="ts">
import { onMounted, onUnmounted } from 'vue'
import { useTheme } from 'vuetify'
import { watch } from 'vue'
import AppHeader from '@/layouts/AppHeader.vue'
import AppFooter from '@/layouts/AppFooter.vue'
import LogViewer from '@/components/admin/LogViewer.vue'
import { Toaster } from '@/components/ui/sonner'
import { useAuthStore } from '@/stores/auth'
import { useLogStore } from '@/stores/logStore'

const authStore = useAuthStore()
const logStore = useLogStore()
const vuetifyTheme = useTheme()

// Keep Vuetify dark theme in sync with html.dark class during coexistence
watch(
  () => vuetifyTheme.global.current.value.dark,
  (isDark) => document.documentElement.classList.toggle('dark', isDark),
  { immediate: true }
)

// Ctrl+Shift+L shortcut for log viewer (moved from App.vue inline logic)
const handleKeyPress = (event: KeyboardEvent) => {
  if (event.ctrlKey && event.shiftKey && event.key === 'L') {
    event.preventDefault()
    logStore.toggleViewer()
  }
}

onMounted(() => {
  authStore.initialize()
  window.addEventListener('keydown', handleKeyPress)
})

onUnmounted(() => {
  window.removeEventListener('keydown', handleKeyPress)
})
</script>

<template>
  <div class="min-h-screen flex flex-col bg-background text-foreground">
    <AppHeader />
    <main class="flex-1">
      <router-view v-slot="{ Component }">
        <transition name="fade" mode="out-in">
          <component :is="Component" />
        </transition>
      </router-view>
    </main>
    <AppFooter />
    <LogViewer />
    <Toaster position="bottom-right" rich-colors />
  </div>
</template>

<style scoped>
.fade-enter-active,
.fade-leave-active {
  transition: opacity 0.2s ease;
}
.fade-enter-from,
.fade-leave-to {
  opacity: 0;
}
</style>
```

### Login Form with vee-validate + Zod

```typescript
// Source: vee-validate docs + PITFALLS.md Pitfall 11
// src/components/auth/LoginModal.vue <script setup lang="ts">
import { z } from 'zod'
import { toTypedSchema } from '@vee-validate/zod'
import { useForm } from 'vee-validate'

// Schema as static const (NOT in computed — prevents type inference loss)
const loginSchema = toTypedSchema(z.object({
  username: z.string().min(1, 'Required'),
  password: z.string().min(1, 'Required'),
}))

const { handleSubmit, defineField, errors, isSubmitting } = useForm({
  validationSchema: loginSchema,
})

// validateOnBlur: true + validateOnInput: true = real-time after first blur
const [username, usernameAttrs] = defineField('username', {
  validateOnBlur: true,
  validateOnInput: true,
})
const [password, passwordAttrs] = defineField('password', {
  validateOnBlur: true,
  validateOnInput: true,
})

const onSubmit = handleSubmit(async (values) => {
  // values is typed: { username: string, password: string }
  const success = await authStore.login(values.username, values.password)
  if (success) {
    emit('login-success', authStore.user?.username)
    // DO NOT call router.go(0) — auth state is reactive
  }
})
```

### Toast Usage Pattern

```typescript
// Source: vue-sonner docs
import { toast } from 'vue-sonner'

// Login success (per CONTEXT.md: success toast + modal close + header updates)
const handleLoginSuccess = (username: string) => {
  loginModalOpen.value = false
  toast.success(`Logged in as ${username}`, { duration: 5000 })
}

// Error (stays until dismissed)
toast.error('Login failed: Invalid credentials', { duration: Infinity })

// Promise pattern
toast.promise(authStore.changePassword(current, newPwd), {
  loading: 'Changing password...',
  success: 'Password changed successfully',
  error: (err) => `Failed: ${err.message}`
})
```

### Vitest Component Test Pattern (TEST-02)

```typescript
// Source: existing Button.spec.ts pattern + @vue/test-utils docs
// Tests go in: src/components/ui/__tests__/ComponentName.spec.ts
// For domain components: src/components/auth/__tests__/LoginModal.spec.ts

import { describe, it, expect, vi } from 'vitest'
import { mount } from '@vue/test-utils'
import { createTestingPinia } from '@pinia/testing'
import LoginModal from '@/components/auth/LoginModal.vue'

describe('LoginModal', () => {
  it('renders login form fields', () => {
    const wrapper = mount(LoginModal, {
      props: { open: true },
      global: {
        plugins: [createTestingPinia({ createSpy: vi.fn })]
      }
    })
    expect(wrapper.find('input[type="text"]').exists()).toBe(true)
    expect(wrapper.find('input[type="password"]').exists()).toBe(true)
  })
})
```

**Note:** `@pinia/testing` may need to be installed: `npm install -D @pinia/testing`

---

## State of the Art

| Old Approach | Current Approach | Status in Codebase |
|--------------|------------------|-------------------|
| `v-app` / `v-main` as root layout | `div.min-h-screen` with Tailwind | NOT YET — App.vue still uses v-app |
| `v-dialog` + `v-form` for auth | `Dialog` + vee-validate + Zod | NOT YET — all auth forms are Vuetify |
| `v-snackbar` reactive state per component | `toast()` from vue-sonner | NOT YET — 9 files use v-snackbar |
| `window.snackbar` bridge (placeholder) | Direct `toast()` calls | PARTIAL — bridge declared in env.d.ts but nothing implements it |
| `useTheme()` from Vuetify | `useColorMode()` from @vueuse/core | NOT YET — App.vue still uses useTheme() |
| `v-icon` with MDI font | `lucide-vue-next` named imports | NOT YET — all icons are v-icon/mdi |
| MDI icon strings in adminIcons.ts | Lucide component references | NOT YET — adminIcons.ts exports mdi-* strings |
| `v-navigation-drawer` | shadcn-vue `Sheet` | NOT YET |
| `v-menu` for user dropdown | `DropdownMenu` | NOT YET |
| `v-footer` | `<footer>` Tailwind | NOT YET |

---

## Open Questions

1. **@pinia/testing installation for TEST-02**
   - What we know: The test setup uses `@vue/test-utils` + `jsdom`; no Pinia testing utilities are installed yet.
   - What's unclear: Whether auth store tests for LoginModal need `@pinia/testing` or can be mocked with `vi.mock`.
   - Recommendation: Add `npm install -D @pinia/testing` to Plan 03-03 prerequisites and use it for auth component tests that exercise Pinia store actions.

2. **LoginModal activator removal — login page context**
   - What we know: Current `LoginModal.vue` has an embedded `<template #activator>` button. The header has `<v-btn :to="'/login'">` — it goes to `/login` page, NOT modal. The modal is controlled by `UserMenu` (which imports `ForgotPasswordModal`) and other internal components.
   - What's unclear: In the current codebase, `LoginModal.vue` is NOT referenced in App.vue or any header component — the header uses `<v-btn :to="'/login'">` (standalone page route). So the modal only exists as a component but may not actually be wired up in the current header.
   - Recommendation: Confirm during Plan 03-01 by searching for `LoginModal` usage. If unused in the current header, the new header should add it as a proper modal trigger as per CONTEXT.md.

3. **vite.config.ts plugin order discrepancy**
   - What we know: STACK.md says `vue()` before `tailwindcss()`. Actual file has `tailwindcss()` before `vue()`. Phase 1 established this order and the build works.
   - What's unclear: Whether the reversed order could cause subtle HMR issues.
   - Recommendation: Leave as-is. The Phase 1 implementation works; changing it risks regressions. Flag for Phase 8 cleanup.

---

## Sources

### Primary (HIGH confidence — directly inspected)
- `/home/bernt-popp/development/kidney-genetics-db/frontend/src/App.vue` — current shell structure
- `/home/bernt-popp/development/kidney-genetics-db/frontend/src/components/AppFooter.vue` — footer content to preserve
- `/home/bernt-popp/development/kidney-genetics-db/frontend/src/components/auth/LoginModal.vue` — current auth modal
- `/home/bernt-popp/development/kidney-genetics-db/frontend/src/components/auth/ForgotPasswordModal.vue` — current modal
- `/home/bernt-popp/development/kidney-genetics-db/frontend/src/components/auth/ChangePasswordModal.vue` — complexity rules
- `/home/bernt-popp/development/kidney-genetics-db/frontend/src/components/auth/UserMenu.vue` — current user menu
- `/home/bernt-popp/development/kidney-genetics-db/frontend/src/views/Login.vue` — standalone login page
- `/home/bernt-popp/development/kidney-genetics-db/frontend/src/views/ForgotPassword.vue` — standalone forgot password
- `/home/bernt-popp/development/kidney-genetics-db/frontend/src/components/admin/AdminHeader.vue` — breadcrumb usage
- `/home/bernt-popp/development/kidney-genetics-db/frontend/src/main.ts` — current app bootstrap
- `/home/bernt-popp/development/kidney-genetics-db/frontend/src/assets/main.css` — CSS layer setup (confirmed OKLCH)
- `/home/bernt-popp/development/kidney-genetics-db/frontend/package.json` — installed packages
- `/home/bernt-popp/development/kidney-genetics-db/frontend/components.json` — shadcn-vue config
- `/home/bernt-popp/development/kidney-genetics-db/frontend/src/components/ui/button/` — existing Button component
- `/home/bernt-popp/development/kidney-genetics-db/frontend/env.d.ts` — window.snackbar type declaration
- `/home/bernt-popp/development/kidney-genetics-db/frontend/src/router/index.ts` — all routes
- `/home/bernt-popp/development/kidney-genetics-db/frontend/src/stores/auth.ts` — auth store API
- `/home/bernt-popp/development/kidney-genetics-db/frontend/src/utils/adminIcons.ts` — mdi-* string registry to replace
- `/home/bernt-popp/development/kidney-genetics-db/frontend/src/utils/publicBreadcrumbs.ts` — breadcrumb data structure

### Secondary (HIGH confidence — prior research docs verified)
- `.planning/research/STACK.md` — package versions, compatibility matrix
- `.planning/research/ARCHITECTURE.md` — CSS coexistence, dark mode migration pattern
- `.planning/research/PITFALLS.md` — Zod v3/v4 conflict, dual dark mode, vee-validate type inference
- `.planning/phases/01-foundation-setup/01-icon-audit.md` — complete MDI→Lucide mapping (198 icons)
- `.planning/phases/01-foundation-setup/01-02-SUMMARY.md` — confirmed Phase 1 CSS layer decisions
- `.planning/phases/03-app-shell-nav-auth-icons/03-CONTEXT.md` — locked user decisions

---

## Metadata

**Confidence breakdown:**
- Current codebase state: HIGH — all files directly inspected
- shadcn-vue component APIs: HIGH — verified via components.json + existing Button.vue patterns
- vue-sonner API: HIGH — STACK.md verified v2.0.9, consistent with research
- vee-validate + Zod integration: HIGH — PITFALLS.md documents known issues thoroughly
- Dark mode sync pattern: HIGH — PITFALLS.md Pitfall 9 explicitly documents this
- Icon mapping: HIGH — Phase 1 audit complete with 198 entries verified

**Research date:** 2026-02-28
**Valid until:** 2026-03-30 (stable libraries; vee-validate Zod v4 support may change, track issue #5027)
