# Stack Research

**Domain:** Frontend migration (Vuetify 3 → TypeScript + Tailwind CSS v4 + shadcn-vue)
**Researched:** 2026-02-28
**Confidence:** HIGH (all versions verified via npm registry and official docs)

---

## Context

This is a subsequent-milestone research. The existing stack (Vue 3.5.x, Vite 7.x, Pinia 3.x, Vue Router 4.x, Axios 1.x, D3 7.9, Cytoscape 3.33, UpSet.js 1.11, Playwright 1.58) is validated and NOT re-researched. Only the new migration-specific packages are documented here.

Current `vite.config.js` uses no TypeScript (`vite.config.js`, JS-only). Current frontend has **0 TypeScript files**, **73 Vue components in JS**, **40 JS files**.

---

## Recommended Stack

### Core Technologies (New)

| Technology | Version | Purpose | Why Recommended |
|------------|---------|---------|-----------------|
| TypeScript | ^5.7.x | Type safety across entire codebase | Latest 5.x stable; required by vue-tsc 2.x. Vue 3 has first-class TS support. Enables typed props via `defineProps<T>()`, typed stores, typed API layer. |
| vue-tsc | ^2.2.x | Vue SFC type checking (CLI) | v2.x is current generation (v1 is obsolete). Wraps `tsc` to understand `.vue` files. Required for `npm run type-check` script. Requires TypeScript >=5.0. |
| @vue/tsconfig | ^0.8.x | Official Vue 3 base tsconfig | Maintained by Vue core team. Sets `strict: true`, `verbatimModuleSyntax: true`, `isolatedModules: true` correctly for Vite+esbuild. Eliminates manual tsconfig boilerplate. |
| tailwindcss | ^4.2.x | Utility-first CSS framework | v4.2.1 current (Feb 2026). CSS-first config, no `tailwind.config.js` needed. 10x faster builds than v3 via Rust engine. Uses `@theme` directive, OKLCH colors. |
| @tailwindcss/vite | ^4.2.x | Vite plugin for Tailwind v4 | First-party Vite integration. Do NOT use PostCSS approach for v4. Plugin handles HMR, auto content scanning. Same version as tailwindcss package. |
| shadcn-vue (CLI) | latest | Component scaffolding CLI | Run via `npx shadcn-vue@latest`. Copies component source into `src/components/ui/`. Full ownership model — no runtime import from node_modules. As of Feb 2025, installs **reka-ui** primitives (not radix-vue). |
| reka-ui | ^2.8.x | Headless accessible UI primitives | Auto-installed by shadcn-vue. Previously called radix-vue; renamed in Feb 2025 when shadcn-vue@latest switched. v2.8.0 current (Feb 2026). Do NOT manually install radix-vue for new components. |

### Supporting Libraries (New)

| Library | Version | Purpose | When to Use |
|---------|---------|---------|-------------|
| lucide-vue-next | ^0.475.x | Icon set replacing @mdi/font | v0.475.0 is a safe minimum; current is 0.575.0 (Feb 2026). ~1500 icons, tree-shakable, typed. Use for all icon replacements. Import individually: `import { Home } from 'lucide-vue-next'`. |
| @tanstack/vue-table | ^8.21.x | Headless data table engine | v8.21.3 current. Replaces `v-data-table`. Composable API using Vue refs. Supports `manualPagination: true` for server-side pagination, `manualSorting: true` for server-side sort. Requires building wrapper components. |
| vee-validate | ^4.15.x | Form validation | v4.15.1 current stable. Use v4 (NOT v5 beta). Composition API based (`useForm`, `useField`). Integrates with shadcn-vue Form components via `FormField`, `FormItem`, `FormLabel`, `FormMessage`. |
| @vee-validate/zod | ^4.15.x | Zod adapter for vee-validate | v4.15.1 current. Provides `toTypedSchema()` for type-safe form values. Use with **Zod v3 only** (peer dep: `zod@^3.24.0`). |
| zod | ^3.24.x | Schema validation | Use Zod **v3**, not v4. Zod 4.3.6 is on npm but `@vee-validate/zod` has NOT updated peer deps to support v4 (open issues #5027, #5024 as of Feb 2026). Install exactly `zod@^3.24.0` to avoid peer dep conflicts. |
| vue-sonner | ^2.0.x | Toast notifications | v2.0.9 current (Oct 2025). Replaces `v-snackbar`. Wraps the Sonner library for Vue. shadcn-vue's Sonner component uses this. Used via `toast()` function calls. |
| @vueuse/core | ^14.2.x | Vue composition utilities | v14.2.1 current (Feb 2026). Use `useColorMode()` for dark mode (replaces Vuetify `useTheme()`). Also: `useLocalStorage`, `useDebounce`, `useBreakpoints`, `onClickOutside`. |
| class-variance-authority | ^0.7.x | Component variant management | Auto-installed by shadcn-vue. Used in shadcn component source files for variant props. Do not configure manually. |
| clsx | ^2.x | Conditional class merging | Auto-installed by shadcn-vue. Used in `cn()` utility in `src/lib/utils.ts`. |
| tailwind-merge | ^3.5.x | Tailwind class deduplication | v3.5.0 current (Feb 2026). Supports Tailwind v4.0-v4.2. **Use v3.x for Tailwind v4**. v2.x is for Tailwind v3 only. |

### Development Tools (New)

| Tool | Version | Purpose | Notes |
|------|---------|---------|-------|
| @types/node | ^22.x | Node.js type definitions | Required for `path.resolve(__dirname, ...)` in `vite.config.ts`. Install as dev dependency. |
| vitest | ^4.0.x | Unit and component testing | v4.0.18 current (Jan 2026). Vite-native, zero config for Vue projects. Replaces Jest entirely. Add when introducing component unit tests in Phase 0. Currently frontend has only Playwright E2E. |
| @vue/test-utils | ^2.x | Vue component test utilities | Companion to vitest for mounting Vue components. Install alongside vitest if component tests are added. |
| happy-dom | ^x | DOM environment for vitest | Lighter than jsdom. Recommended vitest environment for Vue component tests. |

---

## Installation

### Step 1: TypeScript foundation

```bash
cd /home/bernt-popp/development/kidney-genetics-db/frontend

# TypeScript compiler + Vue SFC type checker + Vue base tsconfig
npm install -D typescript@^5.7.0 vue-tsc@^2.2.0 @vue/tsconfig@^0.8.0

# Node types (needed in vite.config.ts)
npm install -D @types/node@^22.0.0
```

### Step 2: Tailwind CSS v4

```bash
# Tailwind v4 + Vite plugin (same version number)
npm install tailwindcss@^4.2.0 @tailwindcss/vite@^4.2.0
```

### Step 3: shadcn-vue init (interactive CLI)

Run AFTER Tailwind is installed and tsconfig/vite.config.ts are configured:

```bash
npx shadcn-vue@latest init
```

The CLI will ask: base color (select Neutral or Slate), TypeScript (yes), components path, etc. This installs `reka-ui` and creates `src/components/ui/`, `src/lib/utils.ts`, and `components.json`.

### Step 4: Supporting runtime libraries

```bash
# Icons
npm install lucide-vue-next@^0.475.0

# Data tables
npm install @tanstack/vue-table@^8.21.0

# Form validation — use Zod v3, NOT v4
npm install vee-validate@^4.15.0 @vee-validate/zod@^4.15.0 zod@^3.24.0

# Toasts
npm install vue-sonner@^2.0.0

# Vue utilities
npm install @vueuse/core@^14.2.0
```

### Step 5: Vitest (optional, add when starting component tests)

```bash
npm install -D vitest@^4.0.0 @vue/test-utils@^2.4.0 happy-dom@^x
```

---

## Configuration

### tsconfig.json (root — references only)

```json
{
  "files": [],
  "references": [
    { "path": "./tsconfig.app.json" },
    { "path": "./tsconfig.node.json" }
  ],
  "compilerOptions": {
    "baseUrl": ".",
    "paths": {
      "@/*": ["./src/*"]
    }
  }
}
```

The `compilerOptions.paths` here is required for shadcn-vue CLI and IDE path resolution. It must mirror what is in `tsconfig.app.json`.

### tsconfig.app.json (browser/Vue code)

```json
{
  "extends": "@vue/tsconfig/tsconfig.dom.json",
  "include": ["env.d.ts", "src/**/*", "src/**/*.vue"],
  "exclude": ["src/**/__tests__/*"],
  "compilerOptions": {
    "composite": true,
    "tsBuildInfoFile": "./node_modules/.tmp/tsconfig.app.tsbuildinfo",
    "baseUrl": ".",
    "paths": {
      "@/*": ["./src/*"]
    },
    "verbatimModuleSyntax": true
  }
}
```

Notes:
- `extends "@vue/tsconfig/tsconfig.dom.json"` enables `strict: true`, `isolatedModules: true`, `jsx: "preserve"`, `jsxImportSource: "vue"` automatically.
- Do NOT add `"strict": true` manually — it is inherited from `@vue/tsconfig`.
- `verbatimModuleSyntax: true` is required for Vite's esbuild (replaces deprecated `isolatedModules`).

### tsconfig.node.json (Vite config file)

```json
{
  "extends": "@tsconfig/node22/tsconfig.json",
  "include": ["vite.config.*", "vitest.config.*", "cypress.config.*", "nightwatch.conf.*"],
  "compilerOptions": {
    "composite": true,
    "tsBuildInfoFile": "./node_modules/.tmp/tsconfig.node.tsbuildinfo",
    "noEmit": true
  }
}
```

### vite.config.ts (after migration from .js)

```typescript
import path from 'node:path'
import { defineConfig } from 'vite'
import vue from '@vitejs/plugin-vue'
import tailwindcss from '@tailwindcss/vite'
import { readFileSync } from 'fs'

const packageJson = JSON.parse(
  readFileSync(new URL('./package.json', import.meta.url), 'utf-8')
)

export default defineConfig({
  plugins: [
    vue(),
    tailwindcss(),   // Add here — no PostCSS config needed
  ],
  resolve: {
    alias: {
      '@': path.resolve(__dirname, './src'),
    },
  },
  define: {
    __APP_VERSION__: JSON.stringify(packageJson.version),
  },
  server: {
    port: 5173,
    proxy: {
      '/api': {
        target: 'http://localhost:8000',
        changeOrigin: true,
      },
    },
  },
})
```

Critical: `tailwindcss()` plugin must appear **after** `vue()` in the plugins array.

### src/assets/tailwind.css (Tailwind CSS entry file)

For Phase 0 (Tailwind + Vuetify coexistence), use a selective import to avoid preflight conflicts with Vuetify's CSS resets:

```css
/* Phase 0: No preflight — Vuetify handles CSS normalization */
@layer theme, base, components, utilities;
@import "tailwindcss/theme.css" layer(theme);
@import "tailwindcss/utilities.css" layer(utilities);

/* shadcn-vue theme variables: light mode */
:root {
  --background: hsl(0 0% 100%);
  --foreground: hsl(222.2 84% 4.9%);
  --card: hsl(0 0% 100%);
  --card-foreground: hsl(222.2 84% 4.9%);
  --popover: hsl(0 0% 100%);
  --popover-foreground: hsl(222.2 84% 4.9%);
  --primary: hsl(221.2 83.2% 53.3%);
  --primary-foreground: hsl(210 40% 98%);
  --secondary: hsl(210 40% 96.1%);
  --secondary-foreground: hsl(222.2 47.4% 11.2%);
  --muted: hsl(210 40% 96.1%);
  --muted-foreground: hsl(215.4 16.3% 46.9%);
  --accent: hsl(210 40% 96.1%);
  --accent-foreground: hsl(222.2 47.4% 11.2%);
  --destructive: hsl(0 84.2% 60.2%);
  --destructive-foreground: hsl(210 40% 98%);
  --border: hsl(214.3 31.8% 91.4%);
  --input: hsl(214.3 31.8% 91.4%);
  --ring: hsl(221.2 83.2% 53.3%);
  --radius: 0.5rem;
}

/* dark mode */
.dark {
  --background: hsl(222.2 84% 4.9%);
  --foreground: hsl(210 40% 98%);
  --card: hsl(222.2 84% 4.9%);
  --card-foreground: hsl(210 40% 98%);
  --popover: hsl(222.2 84% 4.9%);
  --popover-foreground: hsl(210 40% 98%);
  --primary: hsl(217.2 91.2% 59.8%);
  --primary-foreground: hsl(222.2 47.4% 11.2%);
  --secondary: hsl(217.2 32.6% 17.5%);
  --secondary-foreground: hsl(210 40% 98%);
  --muted: hsl(217.2 32.6% 17.5%);
  --muted-foreground: hsl(215 20.2% 65.1%);
  --accent: hsl(217.2 32.6% 17.5%);
  --accent-foreground: hsl(210 40% 98%);
  --destructive: hsl(0 62.8% 30.6%);
  --destructive-foreground: hsl(210 40% 98%);
  --border: hsl(217.2 32.6% 17.5%);
  --input: hsl(217.2 32.6% 17.5%);
  --ring: hsl(224.3 76.3% 48%);
}

/* Bridge CSS variables to Tailwind utility classes via @theme inline */
@theme inline {
  --color-background: var(--background);
  --color-foreground: var(--foreground);
  --color-card: var(--card);
  --color-card-foreground: var(--card-foreground);
  --color-primary: var(--primary);
  --color-primary-foreground: var(--primary-foreground);
  --color-secondary: var(--secondary);
  --color-secondary-foreground: var(--secondary-foreground);
  --color-muted: var(--muted);
  --color-muted-foreground: var(--muted-foreground);
  --color-accent: var(--accent);
  --color-accent-foreground: var(--accent-foreground);
  --color-destructive: var(--destructive);
  --color-destructive-foreground: var(--destructive-foreground);
  --color-border: var(--border);
  --color-input: var(--input);
  --color-ring: var(--ring);
  --radius: var(--radius);
}
```

For Phase 8 (Vuetify fully removed), replace the selective import with the full import:

```css
/* Phase 8: Full Tailwind (preflight re-enabled once Vuetify is removed) */
@import "tailwindcss";

/* ... same :root, .dark, @theme inline blocks ... */
```

Import order in `main.ts` — **critical during coexistence phase**:

```typescript
// main.ts
import { createApp } from 'vue'
import { createPinia } from 'pinia'
import router from './router'

// 1. Vuetify FIRST (its CSS resets take precedence intentionally during migration)
import 'vuetify/styles'
import { vuetify } from './plugins/vuetify'

// 2. Tailwind SECOND (after Vuetify, so our utility classes cascade over Vuetify's)
import './assets/tailwind.css'

import App from './App.vue'

const app = createApp(App)
app.use(createPinia())
app.use(router)
app.use(vuetify)
app.mount('#app')
```

### components.json (shadcn-vue — generated by init, for reference)

```json
{
  "$schema": "https://shadcn-vue.com/schema.json",
  "style": "new-york",
  "typescript": true,
  "tailwind": {
    "config": "",
    "css": "src/assets/tailwind.css",
    "baseColor": "neutral",
    "cssVariables": true
  },
  "aliases": {
    "components": "@/components",
    "utils": "@/lib/utils",
    "ui": "@/components/ui",
    "lib": "@/lib",
    "composables": "@/composables"
  }
}
```

Notes:
- `tailwind.config` is intentionally empty string — Tailwind v4 has no config file.
- `tailwind.css` must point to the file containing `@import "tailwindcss"`.
- `typescript: true` generates `.ts` components, not `.js`.
- `style: "new-york"` is the sharper variant (vs "default" which is more rounded). Immutable after init.

### src/lib/utils.ts (auto-generated by shadcn-vue init)

```typescript
import { type ClassValue, clsx } from 'clsx'
import { twMerge } from 'tailwind-merge'

export function cn(...inputs: ClassValue[]) {
  return twMerge(clsx(inputs))
}
```

This is the `cn()` helper used in every shadcn component for conditional class merging.

### package.json scripts additions

```json
{
  "scripts": {
    "dev": "vite",
    "build": "vue-tsc --noEmit && vite build",
    "type-check": "vue-tsc --noEmit",
    "preview": "vite preview",
    "lint": "eslint . --fix",
    "lint:check": "eslint .",
    "format": "prettier --write \"src/**/*.{ts,js,vue,css,md}\"",
    "format:check": "prettier --check \"src/**/*.{ts,js,vue,css,md}\"",
    "test:unit": "vitest run",
    "test:unit:watch": "vitest"
  }
}
```

---

## Alternatives Considered

| Recommended | Alternative | Why Not |
|-------------|-------------|---------|
| reka-ui (via shadcn-vue@latest) | radix-vue | radix-vue v1.9.17 is ~1 year old. shadcn-vue@latest switched to reka-ui in Feb 2025. radix-vue is still available via `shadcn-vue@radix` but is not the active development track. |
| Zod v3 + @vee-validate/zod v4 | Zod v4 + vee-validate v5 | vee-validate v5 is still in beta as of Feb 2026. `@vee-validate/zod` has explicit peer dep on `zod@^3.24.0` and does not support Zod v4 (issues #5027/#5024 open). Using Zod v4 now would require `--legacy-peer-deps` and break type inference. Use Zod v3 for stability. |
| vee-validate v4 | vee-validate v5 | v5 has no stable release yet (Feb 2026). v4.15.1 is production-stable with excellent shadcn-vue Form component integration. |
| @tailwindcss/vite plugin | PostCSS + tailwindcss | For Tailwind v4, the Vite plugin is the recommended integration. PostCSS works but is slower and adds extra config file. The Vite plugin provides tighter HMR integration. |
| tailwind-merge v3.x | tailwind-merge v2.x | v2.x only supports Tailwind v3. v3.x supports Tailwind v4. Must use v3.x. |
| @vueuse/core v14.x | Vuetify `useTheme()` | Vuetify's `useTheme()` will be removed. VueUse `useColorMode()` is the framework-agnostic replacement. @vueuse/core v14 is current (Feb 2026). |
| lucide-vue-next | @mdi/font + v-icon | @mdi/font is a font icon set (~7000 icons, but entire font loaded). lucide-vue-next is tree-shakable (only used icons bundled), typed, SVG-based. Use only icons actually needed. |
| vitest v4 | Jest | Vitest is Vite-native with zero config for this stack. Jest requires significant transformation config for Vue SFCs. Vitest v4.0.18 is current. |

---

## What NOT to Use

| Avoid | Why | Use Instead |
|-------|-----|-------------|
| `tailwind.config.js` | Tailwind v4 uses CSS-first config. A JS config file is v3 legacy. | `@theme` directive in the CSS file. |
| PostCSS for Tailwind | Not needed for Tailwind v4 with Vite. Adds unnecessary complexity. | `@tailwindcss/vite` plugin only. |
| `postcss.config.js` or `postcss.config.cjs` | Creates PostCSS pipeline that can conflict with the Vite plugin. | Delete if present. Vite plugin handles Tailwind processing natively. |
| radix-vue (direct install) | The active fork is now reka-ui. radix-vue v1.9.x is ~1 year old with no new releases. | Let shadcn-vue install reka-ui automatically. |
| `@headlessui/vue` | radix-vue/reka-ui covers the same territory with better shadcn-vue integration. | reka-ui (via shadcn-vue). |
| Zod v4 (`zod@^4.x`) | @vee-validate/zod peer dep conflict. No Zod v4 support in current vee-validate. | `zod@^3.24.0` explicitly. |
| `@vee-validate/zod` with `zod@^4.x` | Will produce peer dependency errors. Type inference breaks. | Install with `zod@^3.24.0` pinned. |
| vee-validate v5 (beta) | Not stable. API may change before release. | vee-validate@^4.15.0 stable. |
| `@mdi/font` (keep removing) | Loads entire 7000-icon font regardless of usage. Not tree-shakable. | lucide-vue-next (import individual icons). |
| Vue Options API in new files | Project is migrating to TypeScript. Options API has weaker type inference. | Composition API + `<script setup lang="ts">` in all new/migrated files. |
| Vuetify composables in migrated code | `useTheme()`, `useDisplay()` are Vuetify-specific. Using them in migrated components creates re-migration work later. | `useColorMode()` from @vueuse/core, Tailwind breakpoints. |
| Global CSS utility classes | Tailwind v4 scans files and generates only used classes. Global CSS anti-pattern. | Use Tailwind utilities inline in templates. |

---

## Version Compatibility Matrix

| Package A | Version | Compatible With | Constraint | Confidence |
|-----------|---------|----------------|------------|------------|
| tailwindcss | ^4.2.x | @tailwindcss/vite ^4.2.x | Must match major+minor. Install both from same release. | HIGH |
| tailwind-merge | ^3.5.x | tailwindcss ^4.x | v3.x required for Tailwind v4. v2.x is Tailwind v3 only. | HIGH |
| vee-validate | ^4.15.x | @vee-validate/zod ^4.15.x | Must match. Same version family. | HIGH |
| @vee-validate/zod | ^4.15.x | zod ^3.24.x | Peer dep `zod@^3.24.0`. DOES NOT support zod v4. | HIGH |
| zod | ^3.24.x | @vee-validate/zod ^4.15.x | Use v3 branch. Zod v4 (4.3.6) is available but incompatible here. | HIGH |
| vue-tsc | ^2.2.x | typescript ^5.x | Requires TypeScript >=5.0. vue-tsc v2.x requires Vue language-tools >=2.x. | HIGH |
| @vue/tsconfig | ^0.8.x | typescript ^5.x, vue ^3.4.x | Package requires TS >=5.0 and Vue >=3.4. | HIGH |
| reka-ui | ^2.x (auto) | shadcn-vue@latest | Auto-installed by shadcn-vue CLI. Do not install manually or pin separately. | HIGH |
| @vueuse/core | ^14.2.x | vue ^3.x | v14.x supports Vue 3. Peer dep: `vue@>=2.6` (broad). | HIGH |
| @tanstack/vue-table | ^8.21.x | vue ^3.x | Stable v8 series. v8.21.3 last published. Compatible with Vue 3 refs/reactive. | HIGH |
| vitest | ^4.0.x | vite ^7.x | Vitest 4.x aligns with Vite 7.x ecosystem. Uses Vite for transforms. | HIGH |
| lucide-vue-next | ^0.475.x | vue ^3.x | Peer dep: `vue@>=3.0`. All 0.x versions are production-stable. Use latest. | HIGH |

### Critical Constraint Summary

1. **Tailwind versions must match**: `tailwindcss` and `@tailwindcss/vite` should be at the same `4.x.y` release.
2. **Zod v3 is locked**: Cannot upgrade to Zod v4 until `@vee-validate/zod` releases support (track GitHub issue #5027).
3. **tailwind-merge must be v3.x**: v2.x breaks with Tailwind v4 class names.
4. **shadcn-vue uses reka-ui, not radix-vue**: Do not have both installed; they conflict in CSS variable naming (`data-radix-*` vs `data-reka-*`).
5. **vue-tsc v2.x required**: v1.x is obsolete and has bugs with Vue 3.4+ SFC typing.

---

## Vuetify + Tailwind Coexistence (Migration Window)

During Phases 0–7, both Vuetify 3 and Tailwind v4 coexist. Key risks and mitigations:

| Risk | Severity | Mitigation |
|------|----------|-----------|
| Tailwind preflight resets Vuetify styles | HIGH | Skip preflight during coexistence. Use selective imports: `@import "tailwindcss/theme.css"` + `@import "tailwindcss/utilities.css"` without `base.css`. |
| Vuetify's `!important` overrides Tailwind utilities | MEDIUM | Import Tailwind CSS **after** Vuetify styles in `main.ts`. For stubborn conflicts, use Tailwind's `@layer utilities` to increase specificity. |
| CSS variable name collision | LOW | Vuetify uses `--v-*` prefix. shadcn-vue uses `--background`, `--primary`, etc. No overlap. |
| Tailwind `container` class conflicts with Vuetify container | LOW | Tailwind v4 renames built-in container behavior. Use explicit `max-w-*` + `mx-auto` instead of `container` class during migration. |

**If conflicts become severe**: Use Tailwind's CSS prefix feature. In `tailwind.css`, replace `@import "tailwindcss/utilities.css"` with `@import "tailwindcss/utilities.css" prefix(tw)`. All utility classes become `tw:flex`, `tw:p-4`, etc. This adds migration cost but eliminates all conflicts.

---

## Sources

**Verified via official npm registry and official documentation:**

- [shadcn-vue changelog](https://www.shadcn-vue.com/docs/changelog) — confirms reka-ui switch in Feb 2025
- [shadcn-vue Vite installation (v3)](https://v3.shadcn-vue.com/docs/installation/vite) — tsconfig, vite.config, init steps
- [shadcn-vue components.json docs](https://www.shadcn-vue.com/docs/components-json) — confirmed Tailwind v4: `config` field left empty
- [Tailwind CSS v4 installation](https://tailwindcss.com/docs/installation) — @tailwindcss/vite plugin setup
- [Tailwind CSS @theme docs](https://tailwindcss.com/docs/theme) — @theme inline pattern
- [shadcn/ui Tailwind v4 docs](https://ui.shadcn.com/docs/tailwind-v4) — @theme inline + :root/.dark CSS variable pattern
- [reka-ui npm](https://www.npmjs.com/package/reka-ui) — v2.8.0 confirmed current
- [@tanstack/vue-table npm](https://www.npmjs.com/package/@tanstack/vue-table) — v8.21.3 confirmed
- [@vee-validate/zod npm](https://www.npmjs.com/package/@vee-validate/zod) — v4.15.1 + zod@^3.24.0 peer dep confirmed
- [vee-validate Zod v4 issue #5027](https://github.com/logaretm/vee-validate/issues/5027) — confirmed no Zod v4 support in v4.15.x
- [zod npm](https://www.npmjs.com/package/zod) — v4.3.6 on npm but v3 required for vee-validate
- [tailwind-merge npm](https://www.npmjs.com/package/tailwind-merge) — v3.5.0 for Tailwind v4 confirmed
- [@vueuse/core npm](https://www.npmjs.com/package/@vueuse/core) — v14.2.1 confirmed
- [vue-sonner npm](https://www.npmjs.com/package/vue-sonner) — v2.0.9 confirmed
- [lucide-vue-next npm](https://www.npmjs.com/package/lucide-vue-next) — v0.575.0 confirmed
- [vitest releases](https://vitest.dev/blog/vitest-4) — v4.0.18 confirmed
- [@vue/tsconfig npm](https://www.npmjs.com/package/@vue/tsconfig) — v0.8.1 confirmed
- [vue-tsc npm](https://www.npmjs.com/package/vue-tsc) — v2.2.10 confirmed
- [Tailwind v4 + Vuetify coexistence discussions](https://github.com/tailwindlabs/tailwindcss/discussions/15719) — preflight/prefix workarounds

---

*Stack research for: Frontend migration (Vuetify 3 → TypeScript + Tailwind CSS v4 + shadcn-vue)*
*Researched: 2026-02-28*
