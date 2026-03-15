# Homepage Content Redesign — Design Spec

> **Goal:** Transform the KGDB homepage from a minimal 3-section layout (~30 words) into a content-rich, SEO-optimized 6-section page (~250-300 words) inspired by GeneFoundry's lean modern style — without becoming a wall of text.

> **Constraints:**
> - Single file change: `frontend/src/views/Home.vue`
> - Use existing shadcn-vue primitives (Card, Button, Input, Separator) — no new component files
> - Must pass `npm run lint` and `npx vitest run`
> - Branch: `feat/seo-optimization`
> - Priority keywords: nephrology gene panel, renal genetics database, kidney disease gene database, kidney gene curation, nephropathy gene list, kidney genomics resource

---

## Current State

The homepage has 3 sections:
1. **Hero** — Animated logo + sr-only H1 + tagline paragraph + 3 stats cards (Genes with Evidence, Active Sources, Last Update)
2. **Key Benefits** — 3 icon cards (Evidence-Based, Multi-Source, Research-Grade)
3. (nothing else — page ends with large empty space before the footer)

**Problems:**
- ~30 words of visible indexable text (SEO minimum is 300+)
- H1 is `sr-only` — Google may discount hidden headings
- No search CTA — visitors must navigate to Gene Browser to search
- No explanation of what KGDB is or who it's for
- No citation information for academic users
- No data source credibility signals
- No methodology explanation

## Target State: 6 Sections

### Section 1: Hero (modify existing)

**Keep:** Animated KGDBLogo component, 3 stats cards with gradients, responsive sizing.

**Change:**
- Make H1 **visible** — style it as a compact subtitle below the logo, not a giant heading. Use `text-lg md:text-xl font-semibold text-foreground` — visually secondary to the logo but semantically the H1.
- Text: `Kidney Genetics Database` (the logo already shows "Kidney-Genetics Database" so this is reinforcement, not duplication)

**Add: Inline search input** below the tagline, above the stats cards:
```
[🔍 Search by gene symbol, HGNC ID, or keyword...    ] [Search]
```
- Uses shadcn-vue `Input` + `Button` components
- On submit: `router.push('/genes?search=' + encodeURIComponent(query))`
- Placeholder: `"Search PKD1, HGNC:9008, polycystin..."`
- Max width ~500px, centered
- Search icon (lucide `Search`) inside the button

**Tagline stays:** "Evidence-based renal & nephrology gene curation with multi-source integration"

### Section 2: Data Sources Strip (new)

A subtle horizontal strip showing the 7 integrated data sources.

**Layout:** Full-width muted background (`bg-muted/50`), horizontal flex/grid with source items centered. Each item: small icon (lucide icon matching the source) + source name in `text-sm font-medium`.

**Sources (7):**
1. PanelApp
2. ClinGen
3. GenCC
4. HPO
5. PubTator
6. Literature
7. Diagnostic Panels

**Header text:** `"Integrated from 7 authoritative genomic sources"` — centered, `text-sm text-muted-foreground` above the icons.

**Link:** Entire strip is clickable, links to `/data-sources`.

**SEO value:** Mentions source names as indexable text; signals comprehensiveness.

### Section 3: Key Benefits (expand existing)

**Change:** Expand from 3 cards to 6 in a responsive `grid-cols-1 sm:grid-cols-2 md:grid-cols-3` grid.

**Cards:**

| # | Title | Icon | Description |
|---|-------|------|-------------|
| 1 | Evidence-Based | ShieldCheck | Weighted multi-source scoring from 0-100 with tier classification |
| 2 | Multi-Source | RefreshCw | Aggregated from 7 clinical and research databases |
| 3 | Research-Grade | Microscope | Professional-quality curation workflow with complete audit trails |
| 4 | Regularly Updated | AlarmClockCheck | Automated pipeline with continuous synchronization |
| 5 | Open Access | Unlock | Free under CC BY 4.0 — no registration required for browsing |
| 6 | API Available | Code | JSON:API compliant REST API for programmatic access |

**Style:** Keep current icon-in-circle + title + description pattern. Same sizing, same spacing.

### Section 4: How It Works (new)

A 3-step horizontal pipeline visualization.

**Layout:** `grid-cols-1 md:grid-cols-3` with connecting arrow/chevron icons between steps on desktop.

**Steps:**

1. **Collect** (icon: `Download`)
   - "Gene-disease associations gathered from PanelApp, ClinGen, GenCC, HPO, PubTator, literature, and diagnostic panels"

2. **Score** (icon: `BarChart3`)
   - "Evidence aggregated into a weighted confidence score (0-100) with tier classification from Definitive to Minimal"

3. **Curate** (icon: `CheckCircle`)
   - "Validated genes with annotations including expression, variants, interactions, and phenotypes"

**Header:** `"How It Works"` as H2.

**Style:** Each step is a card with a number badge (1, 2, 3), icon, title, and description. On desktop, `ChevronRight` icons sit between cards.

### Section 5: Who Is This For? (new)

Three audience cards.

**Layout:** `grid-cols-1 md:grid-cols-3`, same card style as benefits but with a colored top border and CTA link.

**Cards:**

| Audience | Icon | Description | CTA |
|----------|------|-------------|-----|
| Nephrologists | Stethoscope | Explore evidence-scored gene panels for kidney disease diagnostics and precision medicine | Browse Genes → `/genes` |
| Geneticists | Dna | Access curated gene-disease associations with cross-referenced variant and phenotype data | View Data Sources → `/data-sources` |
| Bioinformaticians | Terminal | Query via REST API, download gene lists, and integrate with analysis pipelines | API Documentation → `/about` (links to API section) |

**Header:** `"Who Is This For?"` as H2.

### Section 6: How to Cite + Affiliation (new)

Full-width section with muted background, split into two columns on desktop.

**Left column — Citation:**
- H2: "How to Cite"
- Primary citation in a `<blockquote>`-style card with a copy button:
  ```
  Popp B, Rank N, Wolff A, Halbritter J. Kidney-Genetics: An evidence-based
  database for kidney disease associated genes. Nephrol Dial Transplant. 2024;
  39(Supplement_1):gfae069-0787-2170.
  ```
- Secondary citation below:
  ```
  Kidney Genetics Database. https://kidney-genetics.org. Accessed [auto-date].
  ```
- Copy button copies the primary citation to clipboard.

**Right column — Affiliation:**
- "Developed by" + Halbritter Lab link
- University of Leipzig Medical Center (or Charite, depending on current affiliation)
- GitHub icon + link to repo
- License badge: CC BY 4.0

---

## Technical Implementation Notes

### File changes
- **Modify:** `frontend/src/views/Home.vue` — all 6 sections in this single file
- **No new files** — keep it simple, all content is in the view

### New imports needed
- Additional lucide icons: `Search`, `Unlock`, `Code`, `Download`, `BarChart3`, `CheckCircle`, `ChevronRight`, `Stethoscope`, `Terminal`, `Copy`
- `useRouter` already imported
- shadcn-vue `Input` and `Button` (already available as global components)

### SEO considerations
- H1 visible (not sr-only) — even if styled small
- ~250-300 words of indexable text across all 6 sections
- Target keywords appear naturally in section descriptions
- Existing `useSeoMeta` and `useJsonLd` calls remain unchanged
- Data Sources strip adds source names as indexable text

### Responsive behavior
- All grids collapse to single column on mobile
- Search input goes full-width on mobile
- Data sources strip wraps on small screens
- "How It Works" steps stack vertically with downward arrows on mobile
- Citation section stacks (citation above, affiliation below)

### Accessibility
- Search input has `aria-label="Search genes"`
- All icon-only buttons have aria-labels
- Copy button announces "Citation copied" via aria-live region
- All sections have proper heading hierarchy (H1 → H2 → H3)

---

## Not in scope
- FAQ page (separate follow-up: new `/faq` route + footer icon)
- New Vue components (everything inline in Home.vue)
- Changes to other pages
- Changes to structured data schemas (already handled in prior SEO work)
