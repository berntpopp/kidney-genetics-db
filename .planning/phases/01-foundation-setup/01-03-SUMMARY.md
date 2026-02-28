---
phase: "01"
plan: "03"
name: "Vitest and Icon Audit"
subsystem: "frontend-testing"
tags: ["vitest", "vue-test-utils", "jsdom", "component-testing", "icon-audit", "lucide", "mdi", "ci"]

dependency-graph:
  requires:
    - "01-02: Tailwind and shadcn-vue (Button component must exist for smoke test)"
  provides:
    - "Working Vitest pipeline with jsdom environment and Vue component mounting"
    - "Smoke test proving shadcn-vue Button mounts and behaves correctly"
    - "Updated Makefile ci-frontend (4/4 steps including Vitest)"
    - "Updated GitHub Actions frontend-ci job with Vitest step"
    - "Complete MDI-to-Lucide icon mapping for all 198 unique icons"
  affects:
    - "Phase 3: Icon migration can now be planned (audit complete)"
    - "All future phases: component tests can be written with Vitest"

tech-stack:
  added:
    - "vitest@4.0.18 — component testing runner"
    - "@vue/test-utils@2.4.6 — Vue component mounting"
    - "jsdom@28.1.0 — browser DOM simulation"
  patterns:
    - "TDD with Vitest + @vue/test-utils for Vue 3 component testing"
    - "jsdom for browser API simulation (not happy-dom)"
    - "vitest.config.ts separate from vite.config.ts (test-specific config)"

key-files:
  created:
    - "frontend/vitest.config.ts"
    - "frontend/src/test/setup.ts"
    - "frontend/src/components/ui/__tests__/Button.spec.ts"
    - ".planning/phases/01-foundation-setup/01-icon-audit.md"
  modified:
    - "frontend/package.json (added test, test:run scripts)"
    - "frontend/package-lock.json (added vitest, @vue/test-utils, jsdom)"
    - "Makefile (ci-frontend updated 3→4 steps, test-frontend added)"
    - ".github/workflows/ci.yml (Vitest step added to frontend-ci job)"

decisions:
  - key: "jsdom over happy-dom"
    choice: "jsdom"
    reason: "Plan specifies jsdom; better DOM spec compliance for complex components"
  - key: "Separate vitest.config.ts"
    choice: "Separate config file"
    reason: "Avoids polluting vite.config.ts with test-only settings; cleaner separation"
  - key: "98 direct / 198 total icon mappings"
    choice: "No custom SVGs; use closest Lucide icon for all"
    reason: "Context comes from labels, not icons. Custom SVGs add maintenance burden"
  - key: "1 dropped icon: mdi-vuejs"
    choice: "Drop"
    reason: "Framework logo is purely decorative; no semantic meaning in data UI"

metrics:
  duration: "6m 1s"
  completed: "2026-02-28"
  tasks-completed: 2
  tests-added: 3
  icons-mapped: 198
---

# Phase 1 Plan 03: Vitest and Icon Audit Summary

**One-liner:** Vitest with jsdom smoke-tests shadcn-vue Button; all 198 MDI icons mapped to Lucide with direct/close/generic/drop categorization.

## What Was Built

### Task 1: Vitest + CI Integration
Installed and configured the complete frontend component testing pipeline:

- **Vitest 4.0.18** with **jsdom** environment (not happy-dom per plan spec)
- **@vue/test-utils 2.4.6** for mounting Vue 3 components
- **vitest.config.ts** with path aliases (@), Vue plugin, coverage config
- **Smoke test** (`Button.spec.ts`) proving end-to-end pipeline: 3 tests pass
  - Renders with default props (tagName = BUTTON, text = "Click me")
  - Applies variant classes (destructive variant)
  - Handles click events (emits click)
- **Makefile ci-frontend** updated from 3/3 → 4/4 steps; `test-frontend` target added
- **GitHub Actions** frontend-ci job updated with `npx vitest run` step after Build

### Task 2: MDI-to-Lucide Icon Audit
Complete audit of all 198 unique MDI icons used in frontend/src/:

| Category | Count | Description |
|----------|-------|-------------|
| direct | 92 | Exact semantic match in Lucide |
| close | 68 | Similar, slightly different name/style |
| generic | 29 | No close match, contextually reasonable |
| drop | 9 | Decorative-only or framework-specific |

Key gap resolutions:
- `mdi-molecule` → `Atom` (closest science icon)
- `mdi-protein` → `Dna` (biology molecule)
- `mdi-virus` / `mdi-virus-outline` → `Bug` (no Lucide Virus icon)
- `mdi-pipeline` → `Workflow` (sequential processing)
- `mdi-vuejs` → dropped (Vue.js logo, purely decorative)

## Decisions Made

### jsdom over happy-dom
Plan explicitly specifies jsdom. jsdom has better DOM spec compliance for complex component trees and is the de-facto standard for Vue Test Utils.

### Separate vitest.config.ts from vite.config.ts
Test-specific config (jsdom environment, setupFiles, coverage) is isolated. The Vite production config remains clean.

### No custom SVGs for icon migration
All 198 icons have Lucide equivalents or contextually reasonable replacements. Custom SVGs would require ongoing maintenance and add bundle size. Context comes from labels, not icons.

### 1 icon dropped: mdi-vuejs
The Vue.js logo appears in exactly one decorative location. It has no semantic meaning in a data/clinical UI. Removing is the correct choice.

## Verification Results

- `cd frontend && npx vitest run` — exits 0, 3 tests passing
- `grep "vitest" Makefile` — confirms ci-frontend step 4/4 and test-frontend target
- `grep "vitest" .github/workflows/ci.yml` — confirms CI step at line 186
- `wc -l 01-icon-audit.md` — 313 lines (requirement: 200+)
- `comm -23 source_icons.txt audit_icons.txt` — no missing icons (all 198 covered)
- Prettier/ESLint on new files — all pass (vitest.config.ts formatted; Button.spec.ts warnings resolved)

## Deviations from Plan

### Auto-fixed Issues

**[Rule 1 - Bug] Prettier trailing comma warnings in Button.spec.ts**

- **Found during:** Task 1 verification (npm run lint:check)
- **Issue:** Slot objects `{ default: 'Click me' },` had trailing commas that eslint-plugin-vue/prettier flagged as warnings
- **Fix:** Removed trailing commas from slot object literals in the 3 test cases
- **Files modified:** `frontend/src/components/ui/__tests__/Button.spec.ts`

**[Rule 1 - Bug] Prettier formatting issue in vitest.config.ts**

- **Found during:** Task 1 verification (npm run format:check)
- **Issue:** Initial write of vitest.config.ts had trailing commas that Prettier reformatted
- **Fix:** Ran `npx prettier --write vitest.config.ts` to normalize formatting
- **Files modified:** `frontend/vitest.config.ts`

## Commits

| Task | Commit | Description |
|------|--------|-------------|
| Task 1 | 7da490c | feat(01-03): install Vitest and configure component testing pipeline |
| Task 2 | 86ed970 | docs(01-03): complete MDI-to-Lucide icon audit for all 198 unique icons |

## Next Phase Readiness

**Phase 1 is now complete (all 3 plans done).**

- Phase 2 (Component Library): shadcn-vue components ready, Vitest available for testing
- Phase 3 (Icon Migration): Icon audit complete, all 198 MDI icons mapped
  - 1 icon to drop, 197 icons have Lucide equivalents
  - Recommended: search-replace by category (direct → bulk replace, close/generic → case-by-case)
- Phase 5 prerequisite (Evidence tier colors): Still needs design sign-off on OKLCH values
- Phase 6 research flag (multi-select chips): Still needs isolated prototype
