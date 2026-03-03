# Design: Phase 3 Remaining Plans (03-03, 03-04, 03-05)

**Date:** 2026-02-28
**Status:** Approved
**Context:** Plans 03-01 (app shell + layout) and 03-02 (user menu + breadcrumbs + dark mode) are written. This design covers the remaining three plans needed to complete Phase 3.

## Decisions Made

| Decision | Choice | Rationale |
|----------|--------|-----------|
| Icon replacement scope | All 303 v-icon tags across 64 files | Complete ICON-03 in Phase 3; avoid carrying icon debt into later phases |
| Toast replacement scope | All 9 v-snackbar files + 2 window.snackbar files | Complete TFBK-02/03 in Phase 3; consistent with icon approach |
| Plan split | 3 plans (auth, toasts, icons) | Lower risk per plan than combining toasts+icons |
| Auth standalone pages | Same plan as modals (03-03) | Login.vue/ForgotPassword.vue share form logic with modals |
| Icon approach | Direct Lucide imports per file | Final state immediately; tree-shakeable; no throwaway bridge component |
| Vuetify icon props | Leave prepend-icon/append-icon for later phases | These are Vuetify API props tied to v-btn/v-text-field; replaced when parent component migrates |

## Plan 03-03: Auth Modals and Auth Pages

**Requirements:** AUTH-01, AUTH-02, AUTH-03, AUTH-04
**Wave:** 3 (depends on 03-01, 03-02)
**Estimated complexity:** MEDIUM

### Files Modified
- `frontend/src/components/auth/LoginModal.vue` — rewrite with Dialog + vee-validate + Zod
- `frontend/src/components/auth/ForgotPasswordModal.vue` — rewrite with Dialog + Form
- `frontend/src/components/auth/ChangePasswordModal.vue` — rewrite with Dialog + Form + password checklist
- `frontend/src/views/Login.vue` — rewrite standalone page with same form patterns
- `frontend/src/views/ForgotPassword.vue` — rewrite standalone page
- `frontend/src/layouts/AppHeader.vue` — wire LoginModal with v-model:open

### Key Design Decisions
1. **Controlled modal pattern**: LoginModal uses `v-model:open` from parent (AppHeader). No embedded `<template #activator>`. Parent controls open/close state.
2. **Static Zod schemas**: Defined as top-level `const`, NOT inside `computed()` (breaks TypeScript type inference per PITFALLS.md).
3. **Validation trigger**: `validateOnBlur: true` + `validateOnInput: true` on `defineField()` — shows errors after first blur, then continuously validates on input.
4. **Login success flow**: `authStore.login()` resolves → emit `login-success` → parent closes modal + shows toast. NO `router.go(0)` — auth state is reactive via Pinia.
5. **Password complexity**: ChangePasswordModal shows 5 requirements as a live checklist with checkmarks (Check/Circle icons from Lucide, green/muted colors).
6. **Standalone pages**: Login.vue and ForgotPassword.vue use the same Zod schemas and form logic but render in a centered card layout instead of a Dialog.

### Verification
- All 3 modals open/close correctly via v-model:open
- Login success shows toast and updates header (no page reload)
- Password change shows live complexity checklist
- Standalone auth pages render and function
- `npm run build` + `npm run lint` pass
- Zero v-dialog, v-form, v-text-field references in auth files

---

## Plan 03-04: Toast Replacement (All Files)

**Requirements:** TFBK-02, TFBK-03
**Wave:** 3 (depends on 03-01 for Toaster provider)
**Estimated complexity:** LOW

### Files Modified (11 total)
**v-snackbar removal (9 files):**
- `frontend/src/views/admin/AdminAnnotations.vue`
- `frontend/src/views/admin/AdminCacheManagement.vue`
- `frontend/src/views/admin/AdminGeneStaging.vue`
- `frontend/src/views/admin/AdminHybridSources.vue`
- `frontend/src/views/admin/AdminLogViewer.vue`
- `frontend/src/views/admin/AdminPipeline.vue`
- `frontend/src/views/admin/AdminReleases.vue`
- `frontend/src/views/admin/AdminUserManagement.vue`
- `frontend/src/views/NetworkAnalysis.vue`

**window.snackbar replacement (2 files):**
- `frontend/src/composables/useNetworkUrlState.ts`
- `frontend/src/views/NetworkAnalysis.vue` (also has window.snackbar)

### Pattern Per File
1. Remove `snackbar` ref / reactive state and `showSnackbar()` helper function
2. Remove `<v-snackbar>` template block entirely
3. Add `import { toast } from 'vue-sonner'`
4. Replace success calls: `toast.success('message', { duration: 5000 })`
5. Replace error calls: `toast.error('message', { duration: Infinity })`
6. Use `toast.promise()` for async operations where applicable (TFBK-03)
7. Replace `window.snackbar.success/error()` with direct `toast()` imports

### Verification
- `grep -rn 'v-snackbar' frontend/src/` returns zero results
- `grep -rn 'showSnackbar' frontend/src/` returns zero results
- Toast notifications appear at bottom-right on success/error actions in admin views
- Error toasts persist until dismissed; success toasts auto-dismiss after ~5s
- `npm run build` + `npm run lint` pass

---

## Plan 03-05: Icon Replacement (All Files)

**Requirements:** ICON-01, ICON-02, ICON-03, ICON-04, TEST-02
**Wave:** 3 (depends on 03-01)
**Estimated complexity:** HIGH (volume, not difficulty)

### Scope
- **Replace:** All 303 `<v-icon>` tags across 64 files with direct Lucide component imports
- **Create:** `src/utils/icons.ts` — full MDI-to-Lucide mapping module (198 entries from Phase 1 audit)
- **Update:** `adminIcons.ts` to export Lucide component references instead of mdi-* strings
- **Update:** `evidenceTiers.ts` icon references
- **Leave:** `prepend-icon="mdi-*"` / `append-icon="mdi-*"` / `:icon="mdi-*"` Vuetify component props — these migrate with their parent components in Phases 4-8
- **Test:** Component tests for icon utilities (TEST-02)

### Sizing Mapping
| v-icon | Lucide Tailwind class |
|--------|----------------------|
| Default (no size) | `size-5` (20px) |
| `size="small"` | `size-4` (16px) |
| `size="x-small"` | `size-3` (12px) |
| `size="large"` | `size-6` (24px) |
| `size="x-large"` | `size-8` (32px) |
| Explicit px (e.g. `size="16"`) | Matching Tailwind class |

Color inheritance works automatically — Lucide uses `currentColor`.

### adminIcons.ts Migration
Current: exports `Record<string, string>` with mdi-* strings used by admin sidebar.
New: exports `Record<string, Component>` with Lucide component references. Admin views that consume this (AdminHeader, admin sidebar) import the component and render with `<component :is="icon" />`.

### Verification
- `grep -rn '<v-icon' frontend/src/` returns zero results
- `grep -c 'lucide-vue-next' frontend/src/**/*.vue` shows imports in all 64 previously-icon-using files
- `adminIcons.ts` exports Lucide components (not mdi-* strings)
- `npm run build` + `npm run lint` pass
- Vitest tests for icon utilities pass

---

## Execution Order

```
03-01 (written) ──┐
                   ├──→ 03-03 (auth modals)
03-02 (written) ──┤
                   ├──→ 03-04 (toast replacement)
                   │
                   └──→ 03-05 (icon replacement)
```

Plans 03-03, 03-04, and 03-05 are independent of each other. They all depend on 03-01/03-02 (app shell must exist first). They can execute in parallel via worktrees.

## Requirements Coverage

| Requirement | Plan | Status |
|-------------|------|--------|
| LNAV-01 through LNAV-04 | 03-01 | Plan written |
| TFBK-01 | 03-01 | Plan written (Toaster provider) |
| LNAV-05, LNAV-06, LNAV-07 | 03-02 | Plan written |
| AUTH-01, AUTH-02, AUTH-03, AUTH-04 | 03-03 | This design |
| TFBK-02, TFBK-03 | 03-04 | This design |
| ICON-01, ICON-02, ICON-03, ICON-04 | 03-05 | This design |
| TEST-02 | 03-05 | This design |

All 19 Phase 3 requirements are covered across 5 plans.
