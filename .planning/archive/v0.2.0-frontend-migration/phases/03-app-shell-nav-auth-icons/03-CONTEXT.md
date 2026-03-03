# Phase 3: App Shell, Navigation, Auth, Feedback, Icons - Context

**Gathered:** 2026-02-28
**Status:** Ready for planning

<domain>
## Phase Boundary

Migrate the application skeleton (header, footer, navigation, mobile drawer, dark mode, auth modals, toast notifications, and all icons) from Vuetify to shadcn-vue + Lucide. Every page that loads after this phase renders inside the new layout system. Pages themselves (content area) are NOT migrated here — only the shell they sit inside.

</domain>

<decisions>
## Implementation Decisions

### Navigation & mobile drawer
- Desktop nav: clean horizontal text links (no icons next to labels) with active state indicator
- Header: sticky, always visible when scrolling
- Footer: keep all current content — version info, environment badge, log viewer button, GitHub link
- Mobile drawer side: Claude's Discretion (pick based on shadcn-vue Sheet defaults and convention)

### Toast notification system
- Position: bottom-right
- Auto-dismiss: success/info toasts disappear after ~5 seconds; error toasts stay until user dismisses
- Action buttons: yes, when relevant (e.g., "Undo" on delete, "View" after creation)
- Stacking behavior: Claude's Discretion (follow Sonner defaults)

### Auth modal UX
- Keep both login entry points: modal (triggered from header) AND standalone /login page
- Form validation: inline per-field errors in real-time (red text below field on blur/type)
- Login success feedback: success toast ("Logged in as X") + modal closes + header updates
- Password change: show all 5 complexity requirements upfront below the password field with checkmarks as each is met

### Dark mode toggle & persistence
- System default + manual override: start with OS `prefers-color-scheme`, user can override, override persisted to localStorage
- Toggle placement: in the header, next to user menu (always visible)
- Toggle transition: Claude's Discretion (pick what avoids visual glitches during dual-system sync)

### Claude's Discretion
- Mobile drawer side (left vs right)
- Toast stacking behavior (Sonner defaults likely fine)
- Dark mode toggle transition (instant vs fade — depends on dual-system sync reliability)
- Color palette OKLCH conversion (stay close to current sky blue #0EA5E9 primary + violet #8B5CF6 secondary, optimize for contrast)
- Loading skeleton designs
- Exact spacing, typography, and component sizing
- Error state handling patterns
- Page transition animation (currently fade — keep or adjust)

</decisions>

<specifics>
## Specific Ideas

- Desktop nav should be text-only links — cleaner than current icon+text buttons
- Footer preserves all current functionality including the LogViewer toggle (Ctrl+Shift+L shortcut)
- Auth success feedback uses the new toast system (not inline alerts) — this establishes toast as the standard feedback pattern
- Password requirements displayed as a checklist that updates live — visual progress as user types

</specifics>

<deferred>
## Deferred Ideas

None — discussion stayed within phase scope

</deferred>

---

*Phase: 03-app-shell-nav-auth-icons*
*Context gathered: 2026-02-28*
