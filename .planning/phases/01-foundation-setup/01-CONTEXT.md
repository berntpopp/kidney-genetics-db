# Phase 1: Foundation Setup - Context

**Gathered:** 2026-02-28
**Status:** Ready for planning

<domain>
## Phase Boundary

Install and configure TypeScript, Tailwind CSS v4, shadcn-vue, Vitest, and audit all 193 MDI icons for Lucide equivalents. Zero visual changes to the running application. This phase produces the tooling foundation that every subsequent phase builds on.

</domain>

<decisions>
## Implementation Decisions

### Icon gap resolution
- Use the closest available Lucide icon for every MDI icon without a direct match — no custom SVGs
- No special treatment for domain-specific icons (gene, DNA, kidney); context comes from labels, not icons
- Produce a mapping table only (MDI name -> Lucide name -> status) — no visual comparison document
- Decorative-only icons with no reasonable Lucide match: drop entirely
- Functional icons (buttons, actions) with no match: use a generic Lucide replacement

### CSS coexistence approach
- Use the `@layer` wrapping strategy to slot Vuetify below Tailwind utilities — committed approach, no `tw:` prefix fallback
- Restructure `main.css` immediately into the full `@layer` import structure: `@layer theme, base, vuetify, components, utilities`
- Define all custom domain colors (evidence tier OKLCH values, source badge colors) in the `@theme` block now, so they're available from Phase 1 onward
- After setup, spot-check 3 pages (Home, GeneDetail, one Admin page) to verify both CSS systems coexist without visual breakage
- Overall philosophy: move fast, fix issues on the go, minimize the Vuetify coexistence window

### Branching & workflow
- Single long-lived milestone branch: `feat/v0.2.0-frontend-migration`
- All 9 phases land sequentially on this branch
- Branch created now (before Phase 1 execution begins)
- Both planning docs (.planning/) and code changes go on the milestone branch — main stays clean until final merge
- Merge to main only when all 9 phases are complete

### Vitest baseline
- Smoke test mounts a Vue component (e.g., a shadcn-vue Button) to prove the Vitest + Vue + Tailwind pipeline works end-to-end
- Use jsdom as DOM environment (more complete DOM implementation)
- Vitest config extends Vite config using `mergeConfig` pattern (shared path aliases and plugins)
- Update Makefile targets in Phase 1: add vitest to `make ci-frontend` pipeline

### Claude's Discretion
- Exact `tsconfig.json` settings (follow `@vue/tsconfig` base with `strict: true`, `allowJs: true`)
- shadcn-vue `components.json` init settings (follow CLI defaults + Reka UI)
- Which 3 pages to spot-check for CSS coexistence (recommended: Home, GeneDetail, AdminDashboard)
- Exact evidence tier OKLCH color values (derive from current Vuetify theme)

</decisions>

<specifics>
## Specific Ideas

- User wants aggressive migration pace — minimize time spent on coexistence hacks, fix forward
- Research already specifies exact package versions and installation steps (STACK.md) — follow them precisely
- The `@layer` CSS approach is the only path; if issues arise, fix per-component rather than switching strategies
- Makefile integration is expected from day one, not deferred

</specifics>

<deferred>
## Deferred Ideas

None — discussion stayed within phase scope

</deferred>

---

*Phase: 01-foundation-setup*
*Context gathered: 2026-02-28*
