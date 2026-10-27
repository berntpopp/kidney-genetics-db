---
name: Kidney-Genetics Database
description: Evidence-scored kidney disease genes, every number traceable to its source.
colors:
  background: "oklch(0.985 0 0)"
  foreground: "oklch(0.141 0.005 285.823)"
  card: "oklch(1 0 0)"
  muted: "oklch(0.967 0.001 286.375)"
  muted-foreground: "oklch(0.5 0.016 285.938)"
  border: "oklch(0.943 0.003 286.32)"
  primary: "oklch(0.5 0.15 237.323)"
  primary-foreground: "oklch(0.984 0.003 247.858)"
  secondary: "oklch(0.967 0.001 286.375)"
  secondary-foreground: "oklch(0.21 0.006 285.885)"
  ring: "oklch(0.685 0.169 237.323)"
  strength-5: "oklch(0.32 0.14 275)"
  strength-4: "oklch(0.49 0.15 258)"
  strength-3: "oklch(0.62 0.08 215)"
  strength-2: "oklch(0.79 0.11 198)"
  strength-1: "oklch(0.87 0.09 88)"
  success: "oklch(0.52 0.13 152)"
  warning: "oklch(0.58 0.13 65)"
  info: "oklch(0.5 0.15 237.323)"
  danger: "oklch(0.53 0.2 27)"
  source-1: "#0072B2"
  source-2: "#E69F00"
  source-3: "#009E73"
  source-4: "#CC79A7"
  source-5: "#56B4E9"
  source-6: "#D55E00"
  source-7: "#F0E442"
  source-8: "#7F7F7F"
rounded:
  sm: "calc(0.625rem - 4px)"
  md: "calc(0.625rem - 2px)"
  lg: "0.625rem"
  xl: "calc(0.625rem + 4px)"
components:
  button-primary:
    backgroundColor: "{colors.primary}"
    textColor: "{colors.primary-foreground}"
    rounded: "{rounded.md}"
  button-secondary:
    backgroundColor: "{colors.secondary}"
    textColor: "{colors.secondary-foreground}"
    rounded: "{rounded.md}"
  card:
    backgroundColor: "{colors.card}"
    rounded: "{rounded.xl}"
  chip-strength:
    rounded: "{rounded.md}"
  chip-neutral:
    backgroundColor: "{colors.muted}"
    textColor: "{colors.foreground}"
    rounded: "{rounded.md}"
---

# Design System: Kidney-Genetics Database

## Overview

**Creative North Star: "The Evidence Ledger"**

The Kidney-Genetics Database is a ledger of evidence. Each gene is an entry, each source a column, each score a balance that can be audited back to its line items. The interface is quiet, precise and accountable: typography, alignment and tabular numbers carry the structure, and colour is spent on one thing only, how strong the evidence is. Nothing decorative competes with the data.

Density serves experts (clinical geneticists, researchers, curators) without becoming noise: rows align, numbers right-align with tabular figures, identifiers always carry their names, and every abbreviation explains itself on hover or focus. The same thing (a tier, a source, a classification, an identifier, a status) looks and behaves the same on every view, public or admin.

The incumbent shadcn-vue system (OKLCH tokens, light and dark themes, system font stack, KGDB logo) is kept and systematised, not replaced (confirmed 2026-10-27).

**Key Characteristics:**
- One colour meaning: evidence strength. Everything else is neutral or a semantic status.
- Identifiers are never bare: name + ID + link + tooltip.
- One evidence-card anatomy for all sources.
- Stable layout: no shifts between routes or while data loads.
- WCAG 2.2 AA in both themes.

## Colors

A neutral zinc canvas with one sky-blue action colour and one ordinal strength ramp; sources are neutral in the UI and categorical only in charts.

### Primary
- **Ledger Blue** (`--primary`, oklch(0.5 0.15 237.323); dark oklch(0.779 0.15 237.323)): actions, links, focus ring, selected navigation. Never used to express evidence strength.

### Neutral
- **Canvas** (`--background`), **Sheet** (`--card`), **Rule** (`--border`), **Ink** (`--foreground`), **Pencil** (`--muted-foreground`): the shadcn zinc neutrals, unchanged.
- **Secondary** (`--secondary`) is neutral (same as `--muted`): secondary buttons, counts and plain labels. The former violet secondary is retired.

### Evidence strength (the only meaningful colour)
An ordinal, viridis-like ramp (pale gold → teal → blue → deep indigo). In light mode the strongest step is the darkest; in dark mode the ramp is reversed so the strongest step is the lightest (most prominent on the dark canvas). Text and icons on tinted chips are mixed toward `--foreground` so chips stay ≥ 4.5:1 in both themes; adjacent steps keep an OKLab distance > 0.15 under deuteranopia (enforced by `tierPalette.spec.ts`, which reads the values from `main.css`). Dark values: 1 `oklch(0.29 0.04 92)`, 2 `oklch(0.5 0.09 162)`, 3 `oklch(0.63 0.12 233)`, 4 `oklch(0.79 0.11 247)`, 5 `oklch(0.92 0.04 272)`.

| Token | Tier | ClinGen / GenCC classification | Score band |
|---|---|---|---|
| `--strength-5` | Comprehensive Support | Definitive | ≥ 50 |
| `--strength-4` | Multi-Source Support | Strong | ≥ 35 |
| `--strength-3` | Established Support | Moderate | ≥ 20 |
| `--strength-2` | Preliminary Evidence | Limited, Supportive | ≥ 10 |
| `--strength-1` | Minimal Evidence | No Known Disease Relationship, Animal Model Only | < 10 |

Disputed and Refuted are not strengths: they use `--warning` and `--danger` with an icon. "No Classification" uses neutral.

### Status (semantic, never strength)
- **Success** (`--success`): completed, healthy, published. **Warning** (`--warning`): needs attention, stale, disputed. **Danger** (`--danger`, replaces the low-contrast `--destructive`): failed, destructive actions, refuted. **Info** (`--info` = primary): running, informational. Neutral: idle, draft, unknown.
- Each status has `-foreground` and a tinted `-subtle` background; text on solid status colours is ≥ 4.5:1.

### Sources (charts only)
Okabe-Ito categorical palette `--source-1 … --source-8`, assigned to sources in one fixed order in `utils/sources.ts`. Used for chart series, legends and a small marker dot beside a source name. Never as card or header backgrounds, never as text colour.

### Named Rules
**The One Meaning Rule.** Colour means evidence strength. If a colour is not a strength step, a status token or a chart series, it is a neutral.
**The Token-Only Rule.** No raw Tailwind palette classes (`text-red-500`, `bg-green-100`) and no hex/rgb literals in components. Colours come from tokens in `assets/main.css` or from `utils/evidenceTiers.ts`, `utils/sources.ts`, `utils/status.ts`. Enforced by `designTokens.spec.ts`.
**The OKLCH Rule.** Tokens are OKLCH; reference them as `var(--token)` or Tailwind token classes, never wrapped in `hsl(...)`.

## Typography

**Font:** system UI stack (Tailwind `font-sans`); monospace (`font-mono`) for identifiers, code and versions.

### Hierarchy
- **Page title** (600, 1.875rem/2.25rem): one per view, in `PageHeader`.
- **Section title** (600, 1.25rem): card and section headings.
- **Card title** (600, 1rem): evidence and data cards.
- **Body** (400, 0.875–1rem, line-height 1.5; prose max 70ch).
- **Label** (500, 0.75rem): chips, table headers, metadata.
- **Numbers**: `tabular-nums`, right-aligned in tables; scores show one decimal place and a unit.

**The Full-Value Rule.** Truncate only with the full value available on hover/focus.

## Layout

- Container `max-w-7xl` with `px-4 sm:px-6 lg:px-8` on every view (public and admin); `PageHeader` with breadcrumb, title, one-line description and actions.
- 4px base spacing rhythm (Tailwind scale); cards separated by `gap-4`/`gap-6`.
- `html { scrollbar-gutter: stable }`: the header never moves between routes.
- Loading states reserve their final size (skeletons in the final layout); no full-page spinners for partial data.
- Mobile 390 px: no horizontal page scroll; tables scroll inside their container; touch targets ≥ 24 px (44 px for primary actions).

## Elevation & Depth

Flat by default: depth comes from the `--card` sheet on the `--background` canvas and a 1px `--border` rule. Shadows appear only on overlays (popover, dialog, dropdown) via the shadcn defaults.

## Shapes

Radius scale from `--radius` 0.625rem (`rounded-sm` … `rounded-xl`); cards `rounded-xl`, controls and chips `rounded-md`. 1px borders in `--border`.

## Components

### Interaction baseline
Every interactive element has `cursor: pointer` (base rule for `button`, `[role=button]`, `a`, `summary`, `label[for]`, `select`, clickable rows/cards); disabled elements `cursor: not-allowed`. Visible `focus-visible` ring (2px `--ring`). Clickable cards and rows are real `button`/`a` elements or `role="button"` with keyboard handling.

### Buttons
shadcn `Button`: primary (Ledger Blue), secondary (neutral), outline, ghost, destructive (`--danger`). Icon-only buttons always have an accessible name and a tooltip. Async actions (share, copy, export) give visible feedback (toast or inline "Copied").

### Chips
One `Chip` primitive, three kinds:
- **Strength chip**: tier or classification, tinted with its strength step, with the tier icon (non-colour cue) and a tooltip explaining the tier/classification and its threshold.
- **Neutral chip**: counts, sources, metadata; muted background, foreground text; tooltip when the label is abbreviated or coded.
- **Status chip** (`StatusBadge`): one status → one token everywhere (`utils/status.ts`).

### Identifiers (`OntologyTerm`)
Every identifier (HGNC, HPO, MONDO, OMIM, Orphanet, PubMed, Ensembl, ClinVar) renders as **name first, ID second** (`font-mono`, muted), linked to its source (`target="_blank"`, `rel="noopener"`), with a tooltip showing the full name, ID and source. Lists of identifiers are sorted by name and deduplicated; bare ID lists are not allowed.

### Evidence card (`EvidenceCard`)
One anatomy for all sources: header (source name with source marker dot, strength chip or score, one-line summary), stat row (count + unit), body (source-specific detail using the shared primitives), footer (last updated, link to the record at the source). Same paddings, typography and "show more" wording for every source. Expandable cards are buttons with `aria-expanded`.

### Data state (`DataState`)
One loading / empty / error pattern: skeleton in final layout while loading; empty state with a reason; error state inline with message and Retry. A failed load never renders as an empty list.

### Navigation
Top bar with logo, primary links, search, theme toggle; active link marked with weight + underline in Ledger Blue; mobile sheet menu.

## Do's and Don'ts

### Do:
- **Do** take colours only from tokens and the three config modules (`evidenceTiers.ts`, `sources.ts`, `status.ts`).
- **Do** show the strength ramp for tiers, classifications and score bars, always with an icon or label as non-colour cue.
- **Do** render every identifier through `OntologyTerm` with name, ID, link and tooltip.
- **Do** give every abbreviated or coded chip a tooltip.
- **Do** use `DataState` for loading, empty and error.
- **Do** use display names for sources ("Diagnostic panels", not "DiagnosticPanels").

### Don't:
- **Don't** use raw Tailwind palette classes or hex/rgb literals in components.
- **Don't** colour sources in the UI beyond the chart palette and the small marker dot.
- **Don't** use green for anything but success, or use colour as the only signal.
- **Don't** wrap OKLCH tokens in `hsl(...)`.
- **Don't** show bare identifier lists or garbled concatenations (e.g. "Definitive, Strong - Definitive, Strong").
- **Don't** let a failed load look like "no data".
