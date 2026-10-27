# UI/UX design audit 2026-10-27: schema

Every view is reviewed against the same checklist and reported in the same JSON shape, so findings from different reviewers can be merged, deduplicated and turned into shared fixes. Product context: `PRODUCT.md`. Scoring rubric (0–100 per dimension): `../README.md` §2.

## Capture (per view)

- Viewports: desktop 1440×900 and mobile 390×844.
- Themes: light and dark (stored preference `localStorage['theme']`; check the app's theme store for the exact key).
- Full-page screenshots at rest, plus close-ups of every distinct component type on the view.
- Hover and focus states of interactive elements (cursor, tooltip, focus ring).
- Loading, empty and error states where reachable (e.g. a search with no results, an unknown gene).
- Navigation into the view from another route (layout stability of header/nav).

## Checklist (every view, every item)

| ID | Check | Pass means |
|---|---|---|
| C1 | Pointer affordance | Every clickable element (buttons, links, clickable cards/rows, chips with actions, tabs, toggles) shows `cursor: pointer`; non-interactive elements do not. |
| C2 | Layout stability | Header, nav and page container do not move horizontally or vertically between routes or while data loads (scrollbar gutter, skeleton sizes, late-loading content). |
| C3 | Identifiers | Every identifier (HGNC, HPO, MONDO, OMIM, Orphanet, PubMed, Ensembl, ClinVar) shows its human-readable name next to the ID, links to its source, and is never a bare list of codes. |
| C4 | Chips and badges | One chip/badge language: the same kind of thing (tier, source, classification, count, ID) looks the same everywhere; every abbreviated or coded chip explains itself on hover/focus (tooltip). |
| C5 | Evidence presentation | All evidence sources share one card anatomy (source name, score, summary line, count, detail expansion) with consistent typography, spacing and alignment. |
| C6 | Color semantics | Colors come from tokens; tier colors, evidence-source colors and status colors mean the same thing on every view; no raw palette classes (`text-red-500`, hex) outside the token layer; no colour-only meaning. |
| C7 | States | Loading, empty and error states exist, are styled consistently and do not shift layout. |
| C8 | Dark mode | Parity with light: contrast, borders, charts, chips and focus rings all readable. |
| C9 | Accessibility | WCAG 2.2 AA: contrast ≥ 4.5:1 text / 3:1 UI, named controls, logical heading order, keyboard reachable with visible focus, no keyboard traps. |
| C10 | Mobile | 390 px without horizontal scroll; touch targets ≥ 24 px (44 px preferred); readable tables (scroll container or stacked). |
| C11 | Typography | One type scale; numbers tabular in tables and scores; truncation only with a tooltip/full value available. |
| C12 | Copy and labels | No duplicated or garbled strings (e.g. "Definitive, Strong - Definitive, Strong"), labels match geneticists' vocabulary, units and denominators explicit. |
| C13 | Performance feel | No visible jank, long blank states or layout shift; heavy components (charts, network, tables) lazy or skeleton-backed. |

## Finding format (JSON)

Write one file per reviewer: `findings-<group>.json`, an array of:

```json
{
  "id": "genes-detail-hpo-bare-ids",
  "view": "/genes/:symbol",
  "check": "C3",
  "severity": "P1",
  "theme": "both",
  "viewport": "both",
  "title": "HPO evidence lists bare HP IDs without term names",
  "evidence": "screenshot path(s) + what is seen",
  "location": "frontend/src/components/.../File.vue:123",
  "impact": "why it hurts the user",
  "fix": "specific recommendation",
  "shared": "name of the shared primitive/token this belongs to, or null"
}
```

Severity: P0 blocks the task · P1 major difficulty or WCAG AA failure · P2 annoyance · P3 polish.
`shared` names the system-level fix (e.g. `token:tier-colors`, `component:EvidenceCard`, `component:OntologyTerm`, `base:cursor-pointer`, `base:scrollbar-gutter`) so one fix can close many findings.

Also write `scores-<group>.json`: `{ "<view>": { "<dimension>": 0-100, ... } }` with the README §2 dimensions, scored after reviewing.

## Known findings to confirm (reported 2026-10-27)

- Navigating `/` → `/genes` moves the top bar to the right (C2).
- Buttons (share, export) and Evidence Detail cards show the default cursor (C1).
- Evidence Detail cards on `/genes/:symbol` look different per source; chips have no hover info (C4, C5).
- HPO evidence card lists bare HP IDs without term names (C3).
- MONDO Diseases section on `/genes/:symbol` looks poor (C3, C11, C12).
