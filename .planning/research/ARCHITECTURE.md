# Architecture Research

**Domain:** Frontend migration architecture (Vuetify 3 + JavaScript → TypeScript + Tailwind CSS v4 + shadcn-vue)
**Researched:** 2026-02-28
**Confidence:** HIGH (TypeScript/Tailwind v4/shadcn-vue integration; MEDIUM for Vuetify+Tailwind coexistence specifics)

---

## Standard Architecture

### System Overview

```
┌─────────────────────────────────────────────────────────────────────┐
│                        Browser                                      │
│                                                                     │
│  ┌──────────────────────────────────────────────────────────────┐  │
│  │                        Vue 3 SPA                             │  │
│  │                                                              │  │
│  │  ┌─────────────┐  ┌─────────────────┐  ┌────────────────┐  │  │
│  │  │  App Shell  │  │  shadcn-vue UI  │  │  D3/Cytoscape  │  │  │
│  │  │  (Tailwind) │  │  (src/components│  │  (unchanged)   │  │  │
│  │  │             │  │   /ui/)         │  │                │  │  │
│  │  └──────┬──────┘  └────────┬────────┘  └───────┬────────┘  │  │
│  │         │                  │                    │           │  │
│  │  ┌──────▼──────────────────▼──────────────────-▼────────┐  │  │
│  │  │               Domain Components                       │  │  │
│  │  │  (src/components/{gene,evidence,network,admin,auth}/) │  │  │
│  │  └──────────────────────────┬────────────────────────────┘  │  │
│  │                             │                                │  │
│  │  ┌──────────────────────────▼────────────────────────────┐  │  │
│  │  │          Typed Application Layer                      │  │  │
│  │  │  src/stores/ (Pinia)  src/composables/  src/router/   │  │  │
│  │  └──────────────────────────┬────────────────────────────┘  │  │
│  │                             │                                │  │
│  │  ┌──────────────────────────▼────────────────────────────┐  │  │
│  │  │          Typed API Layer (src/api/)                   │  │  │
│  │  │     12 modules, Axios client, JSON:API transforms     │  │  │
│  │  └──────────────────────────┬────────────────────────────┘  │  │
│  └─────────────────────────────┼────────────────────────────────┘  │
│                                │ REST + WebSocket                   │
└────────────────────────────────┼───────────────────────────────────┘
                                 │
                    FastAPI backend (unchanged)
```

### Component Responsibilities

| Component Layer | Responsibility | Typical Implementation |
|-----------------|----------------|------------------------|
| `src/components/ui/` | shadcn-vue primitives: buttons, inputs, dialogs, tables | Copied source files from shadcn-vue CLI; owned by project |
| `src/components/{domain}/` | Business-logic components using ui/ primitives | TypeScript SFCs importing from `@/components/ui/` |
| `src/views/` | Page-level route components | TypeScript SFCs composing domain components |
| `src/layouts/` | App shell (header, footer, sidebar) | TypeScript SFCs using Tailwind layout classes |
| `src/lib/utils.ts` | `cn()` utility for class merging | clsx + tailwind-merge |
| `src/types/` | Shared TypeScript interfaces | Pure `.ts` type declaration files |
| `src/stores/` | Pinia state (auth, logs) | TypeScript Pinia composition stores |
| `src/api/` | REST API client modules | Typed Axios wrapper with JSON:API transforms |
| `src/composables/` | Reusable Vue composition functions | TypeScript composables |
| `src/utils/` | Pure utility functions | TypeScript modules |
| `src/services/` | WebSocket, logging | TypeScript service classes |

---

## Project Structure Evolution

### Current State

```
frontend/
├── src/
│   ├── api/
│   │   ├── admin/              # 6 admin API modules (.js)
│   │   ├── auth.js
│   │   ├── client.js           # Axios instance
│   │   ├── datasources.js
│   │   ├── genes.js
│   │   ├── network.js
│   │   └── statistics.js
│   ├── assets/
│   │   └── *.svg
│   ├── components/
│   │   ├── admin/              # Admin components
│   │   ├── auth/               # Auth modals
│   │   ├── branding/           # Logo
│   │   ├── evidence/           # Evidence display
│   │   ├── gene/               # Gene detail parts
│   │   ├── network/            # Network analysis
│   │   ├── visualizations/     # D3/Cytoscape wrappers
│   │   └── *.vue               # Shared components (top-level)
│   ├── composables/            # 6 composables (.js)
│   ├── config/                 # Config files (.js)
│   ├── plugins/
│   │   └── vuetify.js          # Vuetify configuration
│   ├── router/
│   │   └── index.js
│   ├── services/               # logService.js, websocket.js
│   ├── stores/                 # auth.js, logStore.js
│   ├── utils/                  # 11 utility files (.js)
│   ├── views/
│   │   ├── admin/              # 11 admin views
│   │   └── *.vue               # 11 public views
│   ├── App.vue                 # v-app root (Vuetify)
│   ├── config.js
│   └── main.js                 # JS entry point
├── eslint.config.js
├── package.json                # No TypeScript, no Tailwind
└── vite.config.js
```

### Target State (post-migration)

```
frontend/
├── src/
│   ├── api/
│   │   ├── admin/              # 6 admin API modules (.ts)
│   │   ├── auth.ts
│   │   ├── client.ts           # Typed Axios instance
│   │   ├── datasources.ts
│   │   ├── genes.ts
│   │   ├── network.ts
│   │   └── statistics.ts
│   ├── assets/
│   │   ├── *.svg
│   │   └── main.css            # NEW: Tailwind CSS v4 entry point
│   ├── components/
│   │   ├── admin/              # Admin domain components (.vue, TS)
│   │   ├── auth/               # Auth domain components (.vue, TS)
│   │   ├── branding/           # Logo component (.vue, TS)
│   │   ├── evidence/           # Evidence components (.vue, TS)
│   │   ├── gene/               # Gene detail components (.vue, TS)
│   │   ├── network/            # Network components (.vue, TS)
│   │   ├── ui/                 # NEW: shadcn-vue primitives
│   │   │   ├── button/
│   │   │   │   └── index.ts    # Button component
│   │   │   ├── card/
│   │   │   ├── dialog/
│   │   │   ├── input/
│   │   │   ├── table/
│   │   │   ├── data-table/     # TanStack Table wrapper
│   │   │   └── ...             # Other shadcn-vue components
│   │   └── visualizations/     # D3/Cytoscape wrappers (.vue, TS)
│   ├── composables/            # All composables (.ts)
│   ├── config/                 # Config files (.ts)
│   ├── lib/
│   │   └── utils.ts            # NEW: cn() utility (clsx + tailwind-merge)
│   ├── layouts/                # NEW: App shell layouts
│   │   ├── AppHeader.vue       # (was App.vue header block)
│   │   ├── AppFooter.vue       # (was AppFooter.vue)
│   │   └── AdminLayout.vue     # Admin pages layout wrapper
│   ├── router/
│   │   └── index.ts            # (.ts)
│   ├── services/               # logService.ts, websocket.ts
│   ├── stores/                 # auth.ts, logStore.ts
│   ├── types/                  # NEW: TypeScript type declarations
│   │   ├── api.ts              # PaginatedResponse, ApiError, FilterParams
│   │   ├── auth.ts             # User, AuthToken, LoginCredentials
│   │   ├── gene.ts             # Gene, GeneEvidence, GenePhenotype
│   │   └── pipeline.ts         # PipelineStatus, AnnotationSource
│   ├── utils/                  # All utilities (.ts)
│   ├── views/
│   │   ├── admin/              # 11 admin views (.vue, TS)
│   │   └── *.vue               # 11 public views (.vue, TS)
│   ├── App.vue                 # Tailwind layout root (no v-app)
│   ├── config.ts
│   └── main.ts                 # TS entry point
├── components.json             # NEW: shadcn-vue CLI config
├── eslint.config.ts            # Updated: TS rules, vue-typescript
├── package.json                # + TypeScript, Tailwind, shadcn deps
├── tsconfig.json               # NEW: root TS config
├── tsconfig.app.json           # NEW: app-specific TS config
├── tsconfig.node.json          # NEW: node/vite TS config
└── vite.config.ts              # Updated: @tailwindcss/vite plugin
```

### Structure Rationale

**`src/components/ui/` for shadcn-vue primitives:**
shadcn-vue CLI copies component source directly into this directory. Unlike npm packages, these files are project-owned and can be modified. The `ui/` subdirectory cleanly separates generic primitives from domain-specific components in sibling directories.

**`src/lib/utils.ts` for `cn()`:**
This is the shadcn-vue convention enforced by `components.json`. The `cn()` function (clsx + tailwind-merge) is the single utility that every UI component imports. Keeping it at `src/lib/utils.ts` matches the default alias `@/lib/utils` that all generated shadcn-vue components expect.

**`src/types/` for interfaces:**
Separating type declarations from implementation files allows both `.js` and `.ts` files to import types during the incremental migration. Type files contain only `interface`, `type`, and `enum` declarations — no runtime code.

**`src/layouts/` for app shell:**
Extracting the navigation header and footer out of `App.vue` into dedicated layout components follows the pattern of the target architecture where `<v-app>` is replaced by composable layout primitives.

---

## Architectural Patterns

### Pattern 1: shadcn-vue Component Integration

shadcn-vue components are added by CLI into `src/components/ui/` as owned source code.

**Installation flow:**
```bash
# Initialize: creates components.json, src/lib/utils.ts, updates CSS
npx shadcn-vue@latest init

# Add individual components as needed
npx shadcn-vue@latest add button
npx shadcn-vue@latest add card
npx shadcn-vue@latest add dialog
npx shadcn-vue@latest add table
```

**`components.json` configuration (project-specific):**
```json
{
  "$schema": "https://shadcn-vue.com/schema.json",
  "style": "new-york",
  "typescript": true,
  "tailwind": {
    "config": "",
    "css": "src/assets/main.css",
    "baseColor": "slate",
    "cssVariables": true,
    "prefix": ""
  },
  "aliases": {
    "components": "@/components",
    "composables": "@/composables",
    "utils": "@/lib/utils",
    "ui": "@/components/ui",
    "lib": "@/lib"
  }
}
```

**Key:** `tailwind.config` is empty string for Tailwind v4 (no `tailwind.config.js` exists).

**Domain component importing from `ui/`:**
```vue
<!-- src/components/gene/GeneBasicInfo.vue -->
<script setup lang="ts">
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { Badge } from '@/components/ui/badge'
import type { Gene } from '@/types/gene'

defineProps<{ gene: Gene }>()
</script>

<template>
  <Card>
    <CardHeader>
      <CardTitle>{{ gene.symbol }}</CardTitle>
    </CardHeader>
    <CardContent>
      <Badge variant="secondary">{{ gene.evidence_tier }}</Badge>
    </CardContent>
  </Card>
</template>
```

**Rule:** Domain components (gene/, evidence/, etc.) import from `@/components/ui/`. They never import directly from `radix-vue` or Tailwind utilities bypassing ui/.

### Pattern 2: TypeScript SFC Pattern

All migrated components use `<script setup lang="ts">` with `defineProps<T>()` generic syntax.

**Type-first prop definition:**
```typescript
// src/types/gene.ts
export interface Gene {
  id: number
  symbol: string
  hgnc_id: string | null
  evidence_score: number | null
  evidence_tier: 'comprehensive_support' | 'multi_source_support' |
                 'established_support' | 'preliminary_evidence' | 'minimal_evidence' | null
  source_count: number
}

export interface PaginatedGenes {
  items: Gene[]
  total: number
  page: number
  perPage: number
  pageCount: number
}
```

```vue
<!-- src/components/gene/GeneBasicInfo.vue -->
<script setup lang="ts">
import type { Gene } from '@/types/gene'

// Generic defineProps - no defineProps({}) object form
const props = defineProps<{
  gene: Gene
  showScore?: boolean
}>()

// Optional props use withDefaults
const { gene, showScore = true } = defineProps<{
  gene: Gene
  showScore?: boolean
}>()
</script>
```

**TypeScript Pinia store pattern (composition API):**
```typescript
// src/stores/auth.ts
import { defineStore } from 'pinia'
import { ref, computed } from 'vue'
import type { User } from '@/types/auth'

export const useAuthStore = defineStore('auth', () => {
  const user = ref<User | null>(null)
  const accessToken = ref<string | null>(localStorage.getItem('access_token'))

  const isAuthenticated = computed(() => !!accessToken.value && !!user.value)
  const isAdmin = computed(() => user.value?.role === 'admin')

  // Actions remain the same, just typed
  return { user, accessToken, isAuthenticated, isAdmin }
})
```

**Typed API module pattern:**
```typescript
// src/api/genes.ts
import apiClient from './client'
import type { PaginatedGenes, Gene } from '@/types/gene'

interface GeneListParams {
  page?: number
  perPage?: number
  search?: string
  tiers?: string[]
  sortBy?: string
  sortDesc?: boolean
}

export const geneApi = {
  async getGenes(params: GeneListParams = {}): Promise<PaginatedGenes> {
    // Implementation same as current .js file, now with types
    const response = await apiClient.get('/api/genes/', { params: queryParams })
    return { items: ..., total: ..., page: ..., perPage: ..., pageCount: ... }
  }
}
```

### Pattern 3: CSS Coexistence During Migration

During the coexistence period (phases 0-7), both Vuetify and Tailwind CSS v4 are active. CSS cascade layers are used to establish explicit precedence.

**`src/assets/main.css` — the CSS entry point:**
```css
/* 1. Declare layer order explicitly.
   Layers listed first have LOWER precedence.
   Utilities (Tailwind's highest layer) wins over vuetify. */
@layer theme, base, vuetify, components, utilities;

/* 2. Import Vuetify styles into the vuetify layer.
   This is the key: Vuetify's unlayered CSS is now explicit,
   so Tailwind utilities in the 'utilities' layer override it. */
@import 'vuetify/styles' layer(vuetify);
@import '@mdi/font/css/materialdesignicons.css' layer(vuetify);

/* 3. Import Tailwind v4.
   This emits into theme, base, components, utilities layers. */
@import "tailwindcss";

/* 4. Define shadcn-vue CSS variables (light and dark mode).
   These live outside any layer so they are always accessible. */
:root {
  --radius: 0.625rem;
  --background: oklch(1 0 0);
  --foreground: oklch(0.145 0 0);
  --primary: oklch(0.205 0 0);
  --primary-foreground: oklch(0.985 0 0);
  --secondary: oklch(0.97 0 0);
  --secondary-foreground: oklch(0.205 0 0);
  --muted: oklch(0.97 0 0);
  --muted-foreground: oklch(0.556 0 0);
  --accent: oklch(0.97 0 0);
  --accent-foreground: oklch(0.205 0 0);
  --destructive: oklch(0.577 0.245 27.325);
  --border: oklch(0.922 0 0);
  --input: oklch(0.922 0 0);
  --ring: oklch(0.708 0 0);

  /* Medical/scientific domain tokens - preserved from Vuetify */
  --kidney-primary: oklch(0.69 0.1 194);
  --kidney-secondary: oklch(0.62 0.12 192);
  --dna-primary: oklch(0.69 0.18 220);
  --dna-secondary: oklch(0.59 0.17 294);
}

.dark {
  --background: oklch(0.09 0 0);
  --foreground: oklch(0.97 0 0);
  --primary: oklch(0.97 0 0);
  --primary-foreground: oklch(0.205 0 0);
  --secondary: oklch(0.17 0 0);
  --secondary-foreground: oklch(0.97 0 0);
  --muted: oklch(0.17 0 0);
  --muted-foreground: oklch(0.64 0 0);
  --accent: oklch(0.17 0 0);
  --accent-foreground: oklch(0.97 0 0);
  --destructive: oklch(0.65 0.22 25);
  --border: oklch(0.17 0 0);
  --input: oklch(0.17 0 0);
  --ring: oklch(0.45 0 0);

  /* Medical tokens - dark mode variants */
  --kidney-primary: oklch(0.78 0.1 194);
  --kidney-secondary: oklch(0.72 0.12 192);
  --dna-primary: oklch(0.72 0.13 220);
  --dna-secondary: oklch(0.71 0.14 294);
}

/* 5. Register shadcn-vue color variables in Tailwind @theme.
   @theme inline makes these available as bg-background, text-foreground, etc. */
@theme inline {
  --color-background: var(--background);
  --color-foreground: var(--foreground);
  --color-primary: var(--primary);
  --color-primary-foreground: var(--primary-foreground);
  --color-secondary: var(--secondary);
  --color-secondary-foreground: var(--secondary-foreground);
  --color-muted: var(--muted);
  --color-muted-foreground: var(--muted-foreground);
  --color-accent: var(--accent);
  --color-accent-foreground: var(--accent-foreground);
  --color-destructive: var(--destructive);
  --color-border: var(--border);
  --color-input: var(--input);
  --color-ring: var(--ring);
  --color-kidney-primary: var(--kidney-primary);
  --color-kidney-secondary: var(--kidney-secondary);
  --color-dna-primary: var(--dna-primary);
  --color-dna-secondary: var(--dna-secondary);
  --radius-sm: calc(var(--radius) - 4px);
  --radius-md: calc(var(--radius) - 2px);
  --radius-lg: var(--radius);
  --radius-xl: calc(var(--radius) + 4px);
}
```

**`vite.config.ts` — Vite plugin setup:**
```typescript
import { defineConfig } from 'vite'
import vue from '@vitejs/plugin-vue'
import tailwindcss from '@tailwindcss/vite'
import { fileURLToPath, URL } from 'node:url'
import { readFileSync } from 'fs'

const packageJson = JSON.parse(
  readFileSync(new URL('./package.json', import.meta.url), 'utf-8')
)

export default defineConfig({
  plugins: [
    vue(),
    tailwindcss(),  // @tailwindcss/vite plugin (no postcss.config.js needed)
  ],
  resolve: {
    alias: {
      '@': fileURLToPath(new URL('./src', import.meta.url))
    }
  },
  define: {
    __APP_VERSION__: JSON.stringify(packageJson.version)
  },
  server: {
    port: 5173,
    proxy: {
      '/api': {
        target: 'http://localhost:8000',
        changeOrigin: true
      }
    }
  }
})
```

**`main.ts` — import order matters:**
```typescript
import { createApp } from 'vue'
import { createPinia } from 'pinia'
import App from './App.vue'
import router from './router'

// Import CSS: Tailwind (which includes Vuetify via @layer wrapping)
import './assets/main.css'

// Vuetify plugin import (plugin still registered for Vuetify components)
import vuetify from './plugins/vuetify'
// ... etc
```

**Why this CSS approach works:**
- Tailwind v4 uses native CSS cascade layers. Without `@layer`, Vuetify's styles are unlayered and sit at the highest specificity. With `@import 'vuetify/styles' layer(vuetify)`, Vuetify is assigned to a named layer.
- Layer precedence order is set by the `@layer theme, base, vuetify, components, utilities` declaration: later-listed layers win. Tailwind utilities (in `utilities` layer) now override Vuetify styles when they conflict.
- This means you can use Tailwind utility classes on Vuetify elements during migration to style them, which is helpful for gradual replacement.
- Confirmed approach via [Vuetify GitHub discussion #21241](https://github.com/vuetifyjs/vuetify/discussions/21241).

**What to avoid during coexistence:**
- Do NOT use Tailwind's `preflight` (CSS reset) alongside Vuetify's reset. Tailwind v4's base layer handles this, but Vuetify's layer wrapping ensures Tailwind base doesn't override Vuetify component internal styles.
- Do NOT write `@apply` directives inside `<style>` blocks in components. Tailwind v4 does not recommend scoped `@apply` — use utility classes in the template directly. Exception: if you must, add the style block without `scoped` and use explicit selectors.

### Pattern 4: Theme System Migration (Vuetify CSS vars → shadcn-vue/Tailwind)

**Current Vuetify system:**
```javascript
// Vuetify generates CSS custom properties like:
// --v-theme-primary: 14, 165, 233   (RGB values, no oklch)
// --v-theme-on-primary: 255, 255, 255
// Used as: rgb(var(--v-theme-primary))
```

**Migration target — shadcn-vue convention:**
```css
/* CSS variables hold full oklch() values (not components) */
:root {
  --primary: oklch(0.60 0.19 213);   /* maps to Vuetify primary #0EA5E9 sky-500 */
}

/* Used as: var(--primary) or bg-primary (via @theme inline) */
```

**Vuetify color → oklch mapping for this project:**

| Vuetify Token | Hex | shadcn-vue CSS Var | oklch |
|---------------|-----|--------------------|-------|
| `primary` (#0EA5E9) | Sky 500 | `--primary` (light: sky-ish; dark: lighter) | `oklch(0.69 0.18 220)` |
| `secondary` (#8B5CF6) | Violet 500 | `--secondary` extended | Custom `--color-secondary-brand` |
| `success` (#10B981) | Emerald 500 | `--color-emerald-500` via @theme | Native Tailwind |
| `warning` (#F59E0B) | Amber 500 | `--color-amber-500` | Native Tailwind |
| `error` (#EF4444) | Red 500 | `--destructive` | `oklch(0.638 0.245 27)` |
| `kidney-primary` (#14B8A6) | Teal 500 | `--kidney-primary` | Custom domain var |

**Dark mode toggle — replace `useTheme()` from Vuetify with `useColorMode()` from VueUse:**
```typescript
// src/composables/useTheme.ts (new file, replaces Vuetify usage)
import { useColorMode } from '@vueuse/core'

export function useTheme() {
  const colorMode = useColorMode({
    attribute: 'class',       // adds 'dark' class to <html>
    modes: {
      light: 'light',
      dark: 'dark',
    },
    storageKey: 'kgdb-color-mode',
  })

  const isDark = computed(() => colorMode.value === 'dark')

  const toggleTheme = () => {
    colorMode.value = isDark.value ? 'light' : 'dark'
  }

  return { isDark, toggleTheme, colorMode }
}
```

```html
<!-- App.vue (post-migration, no v-app) -->
<template>
  <div class="min-h-screen bg-background text-foreground">
    <AppHeader />
    <main>
      <router-view v-slot="{ Component }">
        <transition name="fade" mode="out-in">
          <component :is="Component" />
        </transition>
      </router-view>
    </main>
    <AppFooter />
    <LogViewer />
    <Toaster />  <!-- vue-sonner -->
  </div>
</template>
```

**`class="dark"` on `<html>` activates shadcn-vue dark mode via CSS:**
```css
/* Already defined in main.css */
.dark {
  --background: oklch(0.09 0 0);
  /* ... all dark tokens */
}
```

---

## Data Flow

```
User action (click, search, filter)
         │
         ▼
TypeScript SFC (defineProps<T> + defineEmits<T>)
         │  typed props/emits
         ▼
Pinia Store (useAuthStore / useLogStore) [TypeScript]
         │  or
         ▼
Typed Composable (useNetworkSearch, useBackupApi, etc.)
         │
         ▼
Typed API Module (src/api/*.ts)
         │  returns Promise<TypedResponse>
         ▼
Axios client (src/api/client.ts)
         │  JSON:API → transformed flat object
         ▼
FastAPI backend (unchanged contract)
```

**Type propagation:** Types flow from `src/types/*.ts` outward:
- `src/types/gene.ts` → `src/api/genes.ts` → `src/stores/*.ts` → components

**Visualization data flow (unchanged):**
D3 and Cytoscape components receive typed data via props but render entirely in SVG/canvas, independent of the CSS system. No migration needed for D3 internals; only the Vue wrapper's layout classes change.

---

## TypeScript Configuration

### File structure (three tsconfig files — standard Vue 3 pattern)

```
tsconfig.json         # Root config: references to app + node configs
tsconfig.app.json     # App code: src/ directory
tsconfig.node.json    # Build tooling: vite.config.ts, etc.
```

**`tsconfig.json` (root):**
```json
{
  "files": [],
  "references": [
    { "path": "./tsconfig.node.json" },
    { "path": "./tsconfig.app.json" }
  ]
}
```

**`tsconfig.app.json`:**
```json
{
  "extends": "@vue/tsconfig/tsconfig.dom.json",
  "compilerOptions": {
    "target": "ESNext",
    "module": "ESNext",
    "moduleResolution": "bundler",
    "strict": true,
    "verbatimModuleSyntax": true,
    "isolatedModules": true,
    "jsx": "preserve",
    "jsxImportSource": "vue",
    "lib": ["ESNext", "DOM"],
    "baseUrl": ".",
    "paths": {
      "@/*": ["./src/*"]
    },
    "allowJs": true,          // CRITICAL for incremental migration
    "checkJs": false,         // Don't type-check .js files (only .ts)
    "skipLibCheck": true,
    "noEmit": true,           // Vite handles emit, not tsc
    "types": ["vitest/globals"]  // If using Vitest globally
  },
  "include": ["src/**/*.ts", "src/**/*.tsx", "src/**/*.vue"],
  "exclude": ["src/**/*.spec.ts", "src/**/*.test.ts"]
}
```

**`tsconfig.node.json`:**
```json
{
  "extends": "@tsconfig/node22/tsconfig.json",
  "compilerOptions": {
    "module": "ESNext",
    "moduleResolution": "bundler",
    "strict": true
  },
  "include": ["vite.config.ts", "vitest.config.ts", "eslint.config.ts"]
}
```

**Critical settings explained:**

| Setting | Value | Reason |
|---------|-------|--------|
| `allowJs` | `true` | Enables mixed `.js`/`.ts` during migration; TypeScript can import from `.js` |
| `checkJs` | `false` | Avoids flooding errors from untyped `.js` files; enable only after full migration |
| `verbatimModuleSyntax` | `true` | Required by `@vue/tsconfig`; superset of `isolatedModules` |
| `moduleResolution` | `"bundler"` | Correct resolution for Vite; supports `package.exports` |
| `strict` | `true` | Enable from the start for `.ts` files; prevents accumulating tech debt |
| `noEmit` | `true` | Vite/esbuild does transpilation; `vue-tsc` is only for type checking |

**Build script additions:**
```json
{
  "scripts": {
    "build": "vue-tsc --build && vite build",
    "type-check": "vue-tsc --build --force",
    "lint": "eslint . --fix",
    "test": "vitest run",
    "test:ui": "vitest --ui",
    "test:coverage": "vitest run --coverage"
  }
}
```

---

## CSS Architecture

### Coexistence Period (Phases 0–7)

**CSS load order (enforced by `src/assets/main.css`):**
```
@layer declaration           → defines explicit precedence
@import vuetify layer(vuetify)  → Vuetify in its layer
@import tailwindcss           → Tailwind layers (theme > base > components > utilities)
:root / .dark variables       → shadcn-vue design tokens
@theme inline                 → Tailwind utility registration
```

**Specificity resolution:**
- Tailwind `utilities` layer > `components` layer > `vuetify` layer > `base` layer > `theme` layer
- This means `class="bg-primary"` always wins over Vuetify's background CSS
- Vuetify component internal layout (flex, positioning) is not in conflict because Tailwind doesn't emit structural equivalents for v-card's internal layout

**Rule for mixed components (partially migrated):**
Components in migration can use both Vuetify component tags AND Tailwind utility classes on those tags. This works because Tailwind utilities in the `utilities` layer override Vuetify's component styles where they conflict:
```vue
<!-- Valid during coexistence: Tailwind utilities on a Vuetify component -->
<v-card class="rounded-lg shadow-md p-4 bg-background">
  <v-card-title class="text-lg font-semibold text-foreground">
    {{ title }}
  </v-card-title>
</v-card>
```

### Final State (Phase 8: Vuetify removed)

Once Vuetify is removed, `main.css` simplifies to:
```css
@import "tailwindcss";

:root {
  /* all shadcn-vue variables */
}

.dark {
  /* dark mode variables */
}

@theme inline {
  /* all Tailwind utility registrations */
}
```

The `@layer` declaration for `vuetify` is removed. The `@import 'vuetify/styles' layer(vuetify)` import is removed. No other CSS changes are needed because domain components already use Tailwind utilities.

---

## Vitest Architecture

### Configuration

```typescript
// vitest.config.ts (separate from vite.config.ts for clarity)
import { defineConfig } from 'vitest/config'
import vue from '@vitejs/plugin-vue'
import { fileURLToPath, URL } from 'node:url'

export default defineConfig({
  plugins: [vue()],
  test: {
    globals: true,             // describe, it, expect without imports
    environment: 'happy-dom',  // Lighter than jsdom, good for Vue components
    setupFiles: ['./src/test/setup.ts'],
    include: ['src/**/*.{test,spec}.ts'],
    coverage: {
      provider: 'v8',
      reporter: ['text', 'html'],
      include: ['src/**/*.ts', 'src/**/*.vue'],
      exclude: ['src/components/ui/**', 'src/types/**'],
    }
  },
  resolve: {
    alias: {
      '@': fileURLToPath(new URL('./src', import.meta.url))
    }
  }
})
```

**Note on `src/components/ui/**` coverage exclusion:** shadcn-vue components are copied from a maintained library. They come with their own testing. Testing them in this project is redundant — exclude from coverage, but include if custom modifications are made.

**Test setup file:**
```typescript
// src/test/setup.ts
import { config } from '@vue/test-utils'

// Set up any global test configuration
// (plugins, stubs for router, etc.)
```

**What to test:**
- `src/stores/` — Pinia stores (logic-heavy, no DOM)
- `src/composables/` — Reusable logic
- `src/api/` — API transformations (mock Axios)
- `src/utils/` — Pure utility functions
- `src/components/{domain}/` — Domain components with @vue/test-utils

**What NOT to test with Vitest:**
- `src/components/ui/` — shadcn-vue primitives (library code, not project code)
- D3/Cytoscape visualizations (canvas/SVG, use Playwright for these)

---

## Build Order Recommendation

Build order is driven by two constraints: (1) type dependency graph, (2) visual risk (admin pages have lower user impact if temporarily broken).

### Phase 0: Foundation (Non-breaking)
**Build TypeScript infrastructure first — zero visual changes.**
- TypeScript configuration files
- `src/assets/main.css` with CSS layering (Vuetify + Tailwind coexistence)
- `components.json` + `src/lib/utils.ts` initialization
- `src/types/*.ts` type declarations
- Vitest configuration

Rationale: Types must exist before the API layer can be typed. The CSS must be coexistence-safe before any component touches Tailwind classes. This phase is invisible to users.

### Phase 1: Core Infrastructure (Non-visual)
**Migrate the non-component TypeScript layer.**
- `main.ts`, `router/index.ts`
- `src/stores/*.ts` (Pinia stores — highest type safety value)
- `src/api/*.ts` (12 modules using `src/types/`)
- `src/composables/*.ts`, `src/services/*.ts`, `src/utils/*.ts`

Rationale: Stores and API modules are consumed by all components. Migrating them first means every subsequent component migration automatically gets typed data. These files have no UI rendering — migration cannot cause visual regressions.

### Phase 2: App Shell + Layout
**Highest visual impact, but bounded scope.**
- `App.vue` restructure (remove `<v-app>`)
- `AppHeader`, `AppFooter` (layout/nav)
- `UserMenu`, auth modals (Login, ChangePassword, ForgotPassword)
- Theme toggle (`useTheme()` → `useColorMode()`)

Rationale: The app shell is the skeleton everything else hangs on. Migrating it before individual pages means the navigation scaffold is correct before pages are migrated. It's also a good test of the CSS coexistence strategy.

**Risk note:** This phase requires the most careful CSS attention because the header uses MDI icons and Vuetify layout extensively. Plan for a visual testing session after this phase.

### Phase 3: Simple Public Pages
**Low risk, establishes migration patterns.**
- Home, About, DataSources, Login, ForgotPassword, Profile
- Dashboard (statistics cards — no data tables)

Rationale: These pages use basic Vuetify components (v-card, v-btn, v-chip, v-alert) that map 1:1 to shadcn-vue equivalents. They establish the migration pattern for more complex pages and have minimal risk.

### Phase 4: Evidence & Gene Detail
**Medium complexity, domain-specific components.**
- GeneDetail (tabs + evidence layout)
- All 8 gene/ components
- All 8 evidence/ components
- EvidenceTierBadge, ScoreBreakdown, TierHelpDialog

Rationale: Gene detail is the primary public page. Evidence tier badges require careful color mapping from Vuetify semantic colors (success, warning, info) to shadcn-vue equivalents. Migrate after simple pages to have established patterns.

### Phase 5: Data Tables
**Highest technical complexity — standalone phase.**
- TanStack Table infrastructure (`src/components/ui/data-table/`)
- `GeneTable.vue` (primary gene list — server-side pagination)
- `Genes.vue` (gene list page)
- All admin data table views

Rationale: Data tables are the highest-risk migration item. `v-data-table` with server-side pagination/sorting requires careful TanStack Table configuration. Isolating this as its own phase allows focused effort and testing. Admin tables are included here because they share the same infrastructure.

### Phase 6: Admin Panel
**Lowest user-facing risk (admin-only).**
- AdminDashboard, AdminPipeline, AdminLogViewer
- Backup dialogs (5 components)
- Settings dialogs (2 components)
- AdminHeader component

Rationale: Admin-only pages have limited users. Forms with vee-validate + Zod are concentrated here (backup/settings dialogs). Migrate after data tables because admin pages heavily use them.

### Phase 7: Network Analysis & Visualizations
**Complex but bounded scope.**
- `NetworkAnalysis.vue`, `NetworkGraph.vue`, `NetworkSearchOverlay.vue`
- `ClusterDetailsDialog.vue`, `EnrichmentTable.vue`
- D3 chart Vue wrappers (7 components — CSS only, no D3 internals)
- `GeneStructure.vue`

Rationale: D3 and Cytoscape components only need their wrapper layouts migrated. Network analysis page is complex but the core rendering (Cytoscape) is unaffected. Leave for late phases when patterns are fully established.

### Phase 8: Vuetify Removal
**Final cleanup.**
- Grep and verify zero remaining `v-` tags
- Remove `vuetify`, `@mdi/font` from `package.json`
- Delete `src/plugins/vuetify.js`
- Simplify `src/assets/main.css` (remove layer wrapping)
- Update build scripts, ESLint config, documentation

---

## Anti-Patterns

### Anti-Pattern 1: Importing Radix Vue Directly

**What:** Importing from `radix-vue` directly in domain components instead of through `@/components/ui/`.

```vue
<!-- WRONG -->
<script setup lang="ts">
import { DialogRoot, DialogTrigger } from 'radix-vue'
</script>
```

**Why bad:** shadcn-vue's `@/components/ui/dialog/` wraps Radix with correct styles and accessibility composition. Direct use bypasses styling and may diverge from the rest of the project's component API.

**Instead:** Always use `import { Dialog } from '@/components/ui/dialog'`.

### Anti-Pattern 2: Mixing Vuetify and Tailwind Class Systems

**What:** Using both `pa-4` (Vuetify spacing) and `p-4` (Tailwind) on the same component.

```vue
<!-- WRONG: confusing double-system -->
<v-card class="pa-4 rounded p-4 rounded-lg">
```

**Why bad:** During coexistence, both apply. Post-migration, `pa-4` becomes dead code. Keeps the Vuetify dependency alive in subtle ways.

**Instead:** For any file you touch, convert all Vuetify utilities to Tailwind equivalents in the same commit. Don't half-migrate layout utilities.

### Anti-Pattern 3: Skipping `allowJs` and Starting Strict TypeScript

**What:** Enabling full TypeScript strictness before the codebase is migrated, causing 500+ type errors.

**Why bad:** Makes incremental migration impossible. `tsconfig.app.json` with `strict: true` and `checkJs: true` on all files at once will halt development.

**Instead:** Use `allowJs: true, checkJs: false` during migration. Only `.ts` files are type-checked strictly. Add `checkJs: true` in Phase 8 as a final step.

### Anti-Pattern 4: Building a Custom CSS Theme Instead of Mapping to shadcn-vue Variables

**What:** Recreating the Vuetify `--v-theme-primary` CSS variable system instead of mapping to `--primary`.

```css
/* WRONG: preserving Vuetify's naming convention */
:root {
  --v-theme-primary: 14, 165, 233;
}
```

**Why bad:** Every shadcn-vue component uses `bg-primary`, `text-primary-foreground` — the Tailwind utilities registered via `@theme inline`. Creating a parallel naming system means shadcn-vue components don't pick up the project's brand colors.

**Instead:** Map Vuetify colors → oklch values → shadcn-vue CSS variables. The `--primary` variable is what `bg-primary` resolves to.

### Anti-Pattern 5: Migrating in Place Without Phase Gates

**What:** Partially migrating `App.vue` while also changing `GeneTable.vue` in the same PR.

**Why bad:** When a visual regression occurs, it is unclear which change caused it. Phase gates with verification steps create clear rollback points.

**Instead:** One logical unit per PR. Phase boundary = dedicated PR with visual verification checklist.

### Anti-Pattern 6: Using `@apply` Heavily in Scoped Styles

**What:** Rewriting component logic with `@apply` in `<style scoped>`:

```vue
<!-- AVOID during migration -->
<style scoped>
.card { @apply rounded-lg shadow-md p-4 bg-background; }
</style>
```

**Why bad:** Tailwind v4 documentation explicitly discourages `<style>` block usage in Vue SFCs when using Tailwind — each scoped block is a separate CSS processing context. The style block is processed without access to Tailwind's layer system, which can produce unexpected specificity. Also, it undoes the purpose of utility classes.

**Instead:** Use utility classes directly in the template. Reserve `<style>` for complex pseudo-selector patterns or third-party library overrides that genuinely cannot be expressed as utilities.

---

## Sources

- [shadcn-vue Installation (Vite)](https://radix.shadcn-vue.com/docs/installation/vite) — MEDIUM confidence (documentation site)
- [shadcn-vue components.json Reference](https://www.shadcn-vue.com/docs/components-json) — HIGH confidence (official docs)
- [Tailwind CSS v4.0 Release](https://tailwindcss.com/blog/tailwindcss-v4) — HIGH confidence (official Tailwind blog)
- [Tailwind CSS v4 + shadcn](https://ui.shadcn.com/docs/tailwind-v4) — HIGH confidence (official shadcn docs)
- [Vue 3 TypeScript Overview](https://vuejs.org/guide/typescript/overview.html) — HIGH confidence (official Vue docs)
- [vuejs/tsconfig base config](https://github.com/vuejs/tsconfig) — HIGH confidence (official Vue tooling)
- [Vuetify + Tailwind CSS Coexistence Discussion](https://github.com/vuetifyjs/vuetify/discussions/21241) — MEDIUM confidence (community discussion with solution)
- [Vitest Getting Started](https://vitest.dev/guide/) — HIGH confidence (official Vitest docs)
- [shadcn-vue Theming](https://www.shadcn-vue.com/docs/theming) — HIGH confidence (official docs)
- [VueUse useColorMode](https://vueuse.org/core/useColorMode/) — HIGH confidence (official VueUse docs)
- [Incremental JS→TS Migration (Mixmax)](https://www.mixmax.com/engineering/incremental-migration-from-javascript-to-typescript-in-our-largest-service) — LOW confidence (engineering blog post)

---
*Architecture research for: Frontend migration (Vuetify → TypeScript + Tailwind CSS v4 + shadcn-vue)*
*Researched: 2026-02-28*
