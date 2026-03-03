---
phase: "01-foundation-setup"
plan: "02"
name: "Tailwind and shadcn-vue Configuration"
subsystem: "frontend-tooling"
tags: ["tailwindcss", "shadcn-vue", "reka-ui", "css-layers", "oklch", "coexistence"]

dependency-graph:
  requires:
    - "01-01"  # TypeScript and Build Configuration (vite.config.ts)
  provides:
    - "tailwind-v4-installed"
    - "css-coexistence-layer"
    - "shadcn-vue-initialized"
    - "cn-utility"
    - "oklch-theme-variables"
    - "domain-color-tokens"
  affects:
    - "01-03"  # Vitest and Testing Infrastructure (ESLint now has TypeScript support)
    - "02"     # All subsequent phases using Tailwind utilities + shadcn-vue components

tech-stack:
  added:
    - "tailwindcss@4.2.x"
    - "@tailwindcss/vite@4.2.x"
    - "clsx@2.1.x"
    - "tailwind-merge@3.5.0"
    - "class-variance-authority@0.7.x"
    - "reka-ui@2.x"
    - "lucide-vue-next@0.475.x"
    - "@vueuse/core@14.2.x"
    - "@typescript-eslint/parser@8.x"
  patterns:
    - "CSS @layer coexistence: Tailwind utilities > Vuetify (via @layer(vuetify))"
    - "OKLCH color tokens mapped to Tailwind via @theme inline block"
    - "shadcn-vue components in src/components/ui/"
    - "cn() utility: clsx + tailwind-merge for class merging"
    - "TypeScript ESLint parser for .ts and .vue files"

key-files:
  created:
    - "frontend/src/assets/main.css"
    - "frontend/components.json"
    - "frontend/src/lib/utils.ts"
    - "frontend/src/components/ui/button/Button.vue"
    - "frontend/src/components/ui/button/index.ts"
  modified:
    - "frontend/vite.config.ts"
    - "frontend/src/main.js"
    - "frontend/src/plugins/vuetify.js"
    - "frontend/eslint.config.js"
    - "frontend/package.json"
    - "frontend/package-lock.json"

decisions:
  - id: "tailwindcss-vite-plugin"
    description: "Use @tailwindcss/vite plugin instead of tailwind.config.js"
    rationale: "Tailwind v4 native Vite integration — no config file needed"
  - id: "css-layer-order"
    description: "@layer theme, base, vuetify, components, utilities"
    rationale: "Ensures Tailwind utilities always win over Vuetify specificity"
  - id: "vuetify-styles-in-layer"
    description: "@import 'vuetify/styles' layer(vuetify) in main.css, removed from vuetify.js"
    rationale: "Moves Vuetify into named layer so Tailwind utilities take precedence"
  - id: "oklch-tokens"
    description: "All CSS custom properties use OKLCH color space"
    rationale: "Better perceptual uniformity, maps cleanly to shadcn-vue conventions"
  - id: "typescript-eslint-parser"
    description: "Added @typescript-eslint/parser to eslint.config.js for .ts and .vue files"
    rationale: "ESLint was failing to parse TypeScript syntax (pre-existing gap from 01-01)"
  - id: "components-json-no-config"
    description: "components.json has 'config': '' (empty string, no tailwind.config.js)"
    rationale: "Correct for Tailwind v4 — shadcn-vue CLI works without config file"

metrics:
  duration: "3m 35s"
  completed: "2026-02-28"
  tasks-completed: 2
  tasks-total: 2
  commits: 2
---

# Phase 1 Plan 02: Tailwind and shadcn-vue Configuration Summary

**One-liner:** Tailwind v4 + Vuetify CSS coexistence via @layer(vuetify) strategy with OKLCH tokens, shadcn-vue Button via CLI, and cn() utility (clsx + tailwind-merge v3).

## Objective

Install Tailwind CSS v4, shadcn-vue, and supporting libraries. Create a CSS coexistence layer that wraps Vuetify styles in `@layer(vuetify)` so Tailwind utilities win in specificity without breaking existing Vuetify components.

## What Was Built

### CSS Coexistence Layer (`frontend/src/assets/main.css`)

The central artifact of this plan — a CSS file that:

1. Declares the layer order: `@layer theme, base, vuetify, components, utilities`
2. Imports Vuetify styles inside `@layer(vuetify)` — any Tailwind utility class now beats Vuetify specificity
3. Imports `@mdi/font` inside `@layer(vuetify)` — moved from vuetify.js
4. Imports Tailwind v4 via `@import "tailwindcss"`
5. Defines 40+ OKLCH CSS custom properties for light and dark modes (background, foreground, primary, secondary, muted, accent, destructive, border, sidebar, chart tokens)
6. Defines domain colors: `--kidney-primary`, `--kidney-secondary`, `--dna-primary`, `--dna-secondary` in both light and dark variants
7. Uses `@theme inline` block to map CSS vars to Tailwind color tokens (`--color-primary`, `--color-background`, etc.) enabling `bg-primary`, `text-foreground`, `bg-kidney-primary` etc. as Tailwind utility classes

### shadcn-vue Setup

- **`frontend/components.json`**: shadcn-vue config with `"config": ""` (no tailwind.config.js for v4), pointing to `src/assets/main.css`
- **`frontend/src/lib/utils.ts`**: `cn()` utility combining clsx + tailwind-merge v3 for conflict-free class merging
- **`frontend/src/components/ui/button/`**: Button component added via `npx shadcn-vue@latest add button --yes` — proves the CLI pipeline works

### Vite Plugin

Added `tailwindcss()` plugin to `vite.config.ts` for Tailwind v4 native Vite integration.

### ESLint TypeScript Support

Updated `eslint.config.js` to add `@typescript-eslint/parser` for `.ts` and `.vue` files. This was a pre-existing gap — ESLint was failing to parse TypeScript syntax introduced in 01-01.

## Tasks Completed

| Task | Name | Commit | Key Files |
|------|------|--------|-----------|
| 1 | Install Tailwind v4 and create CSS coexistence layer | 0bbae3d | main.css, vite.config.ts, main.js, vuetify.js |
| 2 | Initialize shadcn-vue, cn() utility, install Button | 78fa87d | components.json, utils.ts, Button.vue, index.ts, eslint.config.js |

## Verification Results

All 7 plan checks passed:

1. `npm run build` — exits 0 (1356 modules transformed)
2. `head -3 src/assets/main.css` — shows layer declaration comment
3. `cat components.json` — shows valid shadcn-vue config with schema
4. `ls src/components/ui/button/` — shows Button.vue and index.ts
5. `ls src/lib/utils.ts` — exists with cn() export
6. `npm ls tailwind-merge` — shows v3.5.0 (not v2.x)
7. `grep "vuetify/styles" src/plugins/vuetify.js` — returns nothing (removed)

## Success Criteria Met

- FNDN-04: Tailwind CSS v4 installed with @tailwindcss/vite plugin
- FNDN-05: Tailwind v4 coexists with Vuetify (CSS @layer strategy)
- FNDN-06: shadcn-vue initialized with Reka UI primitives
- FNDN-07: cn() utility at src/lib/utils.ts (clsx + tailwind-merge v3)
- FNDN-08: Theme CSS variables with OKLCH light/dark mode + domain colors
- npm run build succeeds

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 3 - Blocking] Fixed missing TypeScript ESLint parser**

- **Found during:** Task 2, running `npm run lint:check` after adding shadcn-vue files
- **Issue:** ESLint config had no TypeScript parser — all `.ts` files (including pre-existing types from 01-01) produced "Unexpected token" parse errors. New files `utils.ts`, `Button.vue`, `index.ts` also failed
- **Fix:** Installed `@typescript-eslint/parser@^8.0.0` and updated `eslint.config.js` to use it for `.ts` and `.vue` files; added `env.d.ts` exception for ambient declaration false positives
- **Files modified:** `frontend/eslint.config.js`, `frontend/package.json`
- **Commit:** 78fa87d

## Next Phase Readiness

Phase 01-03 (Vitest and Testing Infrastructure) can proceed. ESLint now has TypeScript support, which was a prerequisite for TypeScript test files.

Potential blocker: `make lint-frontend` from CLAUDE.md runs `eslint .` — should now pass cleanly with the TypeScript parser in place.
