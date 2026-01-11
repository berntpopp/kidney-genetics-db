# Gene Visualization UI/UX Integration Analysis

**Related Issue**: [#29 - Add gene structure and protein domain annotations](https://github.com/berntpopp/kidney-genetics-db/issues/29)
**Related Plan**: [gene-protein-visualization.md](./gene-protein-visualization.md)
**Date**: 2026-01-11
**Status**: Design Recommendation (Revised)
**Last Review**: 2026-01-11 (Added route guards, D3 cleanup, error boundaries)

---

## Executive Summary

This document provides an expert UI/UX analysis of the current gene detail page and recommends the optimal placement for gene structure and protein domain visualizations.

### Core Principle: Evidence First

**The Kidney Genetics Database's primary value is gene-disease association evidence.** The Gene Information card and Evidence Score must remain the most prominent elements on the gene detail page.

**Recommendation**: Create a **dedicated Gene Structure subpage** (`/genes/:symbol/structure`) that is:
1. Linked from the ClinVar section (to see variants in structural context)
2. Accessible via a subtle "View Structure" link in the header
3. NOT on the main gene page to avoid cluttering the evidence-focused layout

---

## Current Page Analysis

### Page Structure (GeneDetail.vue)

```
┌─────────────────────────────────────────────────────────────────┐
│ Breadcrumb: Home > Genes > PKD1                                 │
├─────────────────────────────────────────────────────────────────┤
│ Gene Header: PKD1                    [Save] [Share] [Export] ⋮  │
│ Gene information                                                │
├───────────────────────────────────────┬─────────────────────────┤
│                                       │                         │
│  Gene Information Card (8 cols)       │  Evidence Score (4 cols)│
│  ┌─────────────────────────────────┐  │  ┌───────────────────┐  │
│  │ PKD1 • HGNC:9008 • NM_...       │  │  │    ┌────┐        │  │
│  │                                 │  │  │    │95.4│        │  │
│  │ [Constraint] [ClinVar]          │  │  │    └────┘        │  │
│  │ [Expression] [Phenotypes]       │  │  │  Score Breakdown  │  │
│  │ [Mouse] [Interactions]          │  │  │  CG:100 GC:100... │  │
│  └─────────────────────────────────┘  │  └───────────────────┘  │
│                                       │                         │
├───────────────────────────────────────┴─────────────────────────┤
│ Evidence Details                              [Refresh] [Filter] │
│ ┌───────────────────────────────────────────────────────────┐   │
│ │ ▶ ClinGen: Definitive for autosomal...      Score: 100.0  │   │
│ │ ▶ PanelApp: 10 panels                        Score: 93.8  │   │
│ │ ▶ GenCC: 6 submissions...                   Score: 100.0  │   │
│ │ ▶ PubTator: 1187 publications               Score: 100.0  │   │
│ │ ▶ HPO: 19 phenotypes                         Score: 90.1  │   │
│ │ ▶ DiagnosticPanels: 8 providers             Score: 95.3  │   │
│ │ ▶ Literature: 10 publications                Score: 88.7  │   │
│ └───────────────────────────────────────────────────────────┘   │
└─────────────────────────────────────────────────────────────────┘
```

### Design Observations

| Aspect | Current State | Notes |
|--------|---------------|-------|
| **Layout** | 2-column grid (8:4 ratio) | Vuetify `v-row`/`v-col` |
| **Cards** | Consistent styling with elevation | `v-card` components |
| **Data Display** | Chips for metrics, badges for counts | Color-coded semantically |
| **Theme** | Light/dark mode support | Uses Vuetify theme system |
| **Spacing** | 6-unit margins (`mb-6`) | Consistent throughout |
| **Typography** | H3 for gene name, H4 for sections | Material Design hierarchy |
| **Interactions** | Tooltips on hover, expandable panels | Progressive disclosure |

### Strengths
- Clean, professional appearance
- Good information density without overwhelming
- Consistent design language
- Works well in both light and dark modes
- Responsive column layout

### Areas for Improvement
- No visual representation of gene structure
- MANE transcript ID shown but no structural context
- ClinVar variants shown as counts, not mapped to gene
- Missing protein domain information entirely

---

## Why NOT on the Main Gene Page?

### The Database's Core Mission

The Kidney Genetics Database exists to help clinicians and researchers:
1. **Identify** kidney disease-related genes
2. **Evaluate** gene-disease association strength
3. **Review** curated evidence from multiple sources

The current page perfectly serves this mission:

```
┌─────────────────────────────────────────────────────────────────┐
│ PKD1                                                            │
├───────────────────────────────────────┬─────────────────────────┤
│ Gene Information Card (8 cols)        │ Evidence Score (4 cols) │
│ - Constraint scores ← IMPORTANT       │     ┌────┐              │
│ - ClinVar counts ← IMPORTANT          │     │95.4│ ← MOST       │
│ - Expression ← IMPORTANT              │     └────┘   IMPORTANT  │
│ - Phenotypes ← IMPORTANT              │  Score Breakdown        │
├───────────────────────────────────────┴─────────────────────────┤
│ Evidence Details (expandable)         ← IMPORTANT               │
│ - ClinGen, PanelApp, GenCC, HPO, PubTator, etc.                │
└─────────────────────────────────────────────────────────────────┘
```

**Adding visualizations here would:**
- Push critical evidence information below the fold
- Distract from the gene-disease association focus
- Add loading time for data most users don't need immediately
- Clutter an already information-rich page

### When IS Structure Data Useful?

Structure visualization becomes relevant when:
1. **Interpreting variants** - "Is this variant in a functional domain?"
2. **Understanding pathogenic mechanisms** - "Which exons are affected?"
3. **Research context** - "What are the protein domains?"

These are **secondary tasks** that follow the primary question: "Is this gene associated with kidney disease?"

---

## Recommended Approach: Dedicated Subpage

### Route: `/genes/:symbol/structure`

```
┌─────────────────────────────────────────────────────────────────┐
│ Home > Genes > PKD1 > Structure                                 │
├─────────────────────────────────────────────────────────────────┤
│ ← Back to PKD1                                                  │
│                                                                 │
│ PKD1 Gene Structure & Protein Domains                           │
│ NM_001009944.3 (MANE Select) • chr16:2,088,708-2,135,898       │
├─────────────────────────────────────────────────────────────────┤
│                                                                 │
│ Gene Structure (46 exons)                                       │
│ ┌───────────────────────────────────────────────────────────┐   │
│ │ 5'─┬─┬─┬┬─┬─┬─┬─┬─┬─┬─┬─┬─┬─┬─┬─┬─┬─┬─┬─┬─┬─┬─┬─┬─┬─3'    │   │
│ │    Full interactive exon visualization                    │   │
│ └───────────────────────────────────────────────────────────┘   │
│                                                                 │
│ Protein Domains (4303 aa)                                       │
│ ┌───────────────────────────────────────────────────────────┐   │
│ │ [LRR][PKD repeats][REJ][GPS][PLAT][TM domains]            │   │
│ │ Full interactive domain visualization                     │   │
│ └───────────────────────────────────────────────────────────┘   │
│                                                                 │
│ Variant Overlay (optional future feature)                       │
│ ┌───────────────────────────────────────────────────────────┐   │
│ │ ClinVar pathogenic variants mapped to structure           │   │
│ └───────────────────────────────────────────────────────────┘   │
│                                                                 │
│ [Open in Ensembl] [Open in UniProt] [Download SVG]             │
└─────────────────────────────────────────────────────────────────┘
```

### Entry Points (How Users Get There)

#### 1. ClinVar Section Link (Primary)

```
┌─────────────────────────────────────────────────────────────────┐
│ Clinical Variants (ClinVar):                                    │
│ ┌─────┐ ┌──────┐ ┌───────┐ ┌───────┐                           │
│ │5724 │ │2050  │ │2721   │ │942    │  [View Structure →]       │
│ │total│ │P/LP  │ │VUS    │ │B/LB   │                           │
│ └─────┘ └──────┘ └───────┘ └───────┘                           │
│ [Consequences]                                                  │
└─────────────────────────────────────────────────────────────────┘
```

**Why here?** Users looking at ClinVar counts are likely interested in WHERE variants occur.

#### 2. Gene Header Subtle Link (Secondary)

```
┌─────────────────────────────────────────────────────────────────┐
│ ← PKD1                                      [Save] [Share] [⋮]  │
│   Gene information • NM_001009944.3 [Structure →]              │
└─────────────────────────────────────────────────────────────────┘
```

**Why here?** The MANE transcript ID is already shown - users who know what it means may want more detail.

#### 3. Gene Header Menu (Tertiary)

```
┌─────────────────────────────────────────────────────────────────┐
│                                                      ┌────────┐ │
│                                                      │Copy ID │ │
│                                                      │View in │ │
│                                                      │  HGNC  │ │
│                                                      │────────│ │
│                                                      │View    │ │
│                                                      │Structure│ │
│                                                      └────────┘ │
└─────────────────────────────────────────────────────────────────┘
```

---

## Alternative: Minimal Inline Preview

If some structural context is desired on the main page without disrupting the layout, consider a **minimal preview chip**:

```
┌─────────────────────────────────────────────────────────────────┐
│ Gene Information   PKD1 • HGNC:9008 • NM_001009944.3           │
│                    46 exons • 4303 aa • 12 domains [View →]    │
├─────────────────────────────────────────────────────────────────┤
│ Constraint Scores (gnomAD):                                     │
│ ...                                                             │
└─────────────────────────────────────────────────────────────────┘
```

This adds only one line but provides:
- Quick summary (exon count, protein length, domain count)
- Clear link to full visualization
- No visual disruption

---

## Integration Options Comparison

| Option | Rating | Disruption | Discoverability | Notes |
|--------|--------|------------|-----------------|-------|
| **Subpage (Recommended)** | 9/10 | None | Medium | Best for evidence-first design |
| Subpage + inline preview | 9/10 | Minimal | High | Best of both worlds |
| Full section on main page | 5/10 | High | High | Competes with evidence |
| Collapsible on main page | 6/10 | Medium | Low | Hidden = forgotten |
| Tabs in Gene Info card | 5/10 | Medium | Low | Hides critical data |
| Side drawer | 4/10 | High | Medium | Awkward UX |

---

## Subpage Design Specification

### Route Configuration

```javascript
// router/index.js
{
  path: '/genes/:symbol/structure',
  name: 'gene-structure',
  component: () => import('@/views/GeneStructure.vue'),
  meta: {
    title: 'Gene Structure',
    requiresAuth: false
  },
  // REQUIRED: Route guard to validate gene symbol before loading heavy visualization
  beforeEnter: async (to, from, next) => {
    const symbol = to.params.symbol

    // Basic format validation (gene symbols are alphanumeric with optional hyphens)
    if (!/^[A-Z0-9][A-Z0-9-]*$/i.test(symbol)) {
      next({ name: 'NotFound' })
      return
    }

    // Optional: Verify gene exists in database (prevents loading for invalid genes)
    try {
      const { geneApi } = await import('@/api/genes')
      const response = await geneApi.getBySymbol(symbol)
      if (!response.data) {
        next({ name: 'NotFound' })
        return
      }
      // Store gene data in route meta for component use
      to.meta.gene = response.data
      next()
    } catch (error) {
      // If API fails, proceed anyway (component will handle error)
      next()
    }
  }
}
```

### Component Hierarchy

```
views/
├── GeneDetail.vue (existing - NO CHANGES to layout)
│   └── Add link to structure page in ClinVar section
│
└── GeneStructure.vue (NEW - dedicated subpage)
    ├── Breadcrumbs (Home > Genes > PKD1 > Structure)
    ├── BackLink (← Back to PKD1)
    ├── PageHeader (gene name, transcript, coordinates)
    ├── GeneStructureVisualization.vue (full-width exon track)
    ├── ProteinDomainVisualization.vue (full-width domain track)
    └── ExternalLinks (Ensembl, UniProt, Download)
```

### GeneStructure.vue (New Page)

```vue
<template>
  <div>
    <!-- Use unified breadcrumb system (commit 77ffc7b) -->
    <AppBreadcrumbs />

    <v-container>
      <!-- Back Link & Header -->
      <div class="d-flex align-center mb-4">
        <v-btn
          icon="mdi-arrow-left"
          variant="text"
          size="small"
          :to="`/genes/${route.params.symbol}`"
          class="mr-3"
        />
        <div>
          <h1 class="text-h4 font-weight-bold">
            {{ gene?.approved_symbol }} Structure
          </h1>
          <p class="text-body-2 text-medium-emphasis">
            {{ ensemblData?.canonical_transcript?.refseq_transcript_id }}
            (MANE Select) •
            chr{{ ensemblData?.chromosome }}:{{ formatNumber(ensemblData?.start) }}-{{ formatNumber(ensemblData?.end) }}
            ({{ formatSize(ensemblData?.gene_length) }})
          </p>
        </div>
      </div>

      <!-- REQUIRED: Error boundary for visualization failures -->
      <v-alert
        v-if="visualizationError"
        type="warning"
        variant="tonal"
        class="mb-6"
        closable
        @click:close="visualizationError = null"
      >
        <template #title>Visualization Error</template>
        {{ visualizationError }}
        <template #append>
          <v-btn variant="text" size="small" @click="retryFetch">
            Retry
          </v-btn>
        </template>
      </v-alert>

      <!-- Gene Structure Visualization with error handling -->
      <v-card class="mb-6">
        <v-card-item>
          <template #prepend>
            <v-avatar color="primary" size="40">
              <v-icon icon="mdi-dna" color="white" />
            </v-avatar>
          </template>
          <v-card-title>Gene Structure</v-card-title>
          <v-card-subtitle>
            {{ ensemblData?.exon_count }} exons •
            {{ ensemblData?.strand === '+' ? 'Forward' : 'Reverse' }} strand
          </v-card-subtitle>
        </v-card-item>

        <v-card-text>
          <!-- Loading skeleton -->
          <v-skeleton-loader
            v-if="loading && !ensemblData"
            type="image"
            height="150"
          />

          <!-- Error state for this specific visualization -->
          <v-alert
            v-else-if="ensemblError"
            type="info"
            variant="tonal"
            density="compact"
          >
            Gene structure data unavailable
          </v-alert>

          <!-- Visualization with ref for cleanup -->
          <GeneStructureVisualization
            v-else-if="ensemblData"
            ref="geneStructureRef"
            :gene-data="ensemblData"
            :highlighted-position="hoveredPosition"
            @position-hover="handlePositionHover"
            @error="handleVisualizationError"
          />
        </v-card-text>
      </v-card>

      <!-- Protein Domain Visualization with error handling -->
      <v-card class="mb-6">
        <v-card-item>
          <template #prepend>
            <v-avatar color="secondary" size="40">
              <v-icon icon="mdi-protein" color="white" />
            </v-avatar>
          </template>
          <v-card-title>Protein Domains</v-card-title>
          <v-card-subtitle>
            {{ uniprotData?.length }} amino acids •
            {{ uniprotData?.domains?.length || 0 }} domains
          </v-card-subtitle>
        </v-card-item>

        <v-card-text>
          <!-- Loading skeleton -->
          <v-skeleton-loader
            v-if="loading && !uniprotData"
            type="image"
            height="150"
          />

          <!-- Error state -->
          <v-alert
            v-else-if="uniprotError"
            type="info"
            variant="tonal"
            density="compact"
          >
            Protein domain data unavailable
          </v-alert>

          <!-- Visualization with ref for cleanup -->
          <ProteinDomainVisualization
            v-else-if="uniprotData"
            ref="proteinDomainRef"
            :protein-data="uniprotData"
            :highlighted-domain="hoveredDomain"
            @domain-hover="handleDomainHover"
            @error="handleVisualizationError"
          />
        </v-card-text>
      </v-card>

      <!-- External Links -->
      <v-card>
        <v-card-text class="d-flex justify-center ga-4">
          <v-btn
            variant="outlined"
            prepend-icon="mdi-open-in-new"
            :href="`https://ensembl.org/Homo_sapiens/Gene/Summary?g=${ensemblData?.gene_id}`"
            target="_blank"
            :disabled="!ensemblData?.gene_id"
          >
            View in Ensembl
          </v-btn>
          <v-btn
            variant="outlined"
            prepend-icon="mdi-open-in-new"
            :href="`https://www.uniprot.org/uniprotkb/${uniprotData?.accession}`"
            target="_blank"
            :disabled="!uniprotData?.accession"
          >
            View in UniProt
          </v-btn>
          <v-btn
            variant="outlined"
            prepend-icon="mdi-download"
            @click="downloadSVG"
            :disabled="!ensemblData && !uniprotData"
          >
            Download SVG
          </v-btn>
        </v-card-text>
      </v-card>
    </v-container>
  </div>
</template>

<script setup>
import { ref, computed, onMounted, onUnmounted } from 'vue'
import { useRoute } from 'vue-router'
import * as d3 from 'd3'
import { geneApi } from '@/api/genes'
import { useBreadcrumbs } from '@/composables/useBreadcrumbs'
import AppBreadcrumbs from '@/components/layout/AppBreadcrumbs.vue'
import GeneStructureVisualization from '@/components/visualizations/GeneStructureVisualization.vue'
import ProteinDomainVisualization from '@/components/visualizations/ProteinDomainVisualization.vue'

const route = useRoute()

// Data refs
const gene = ref(null)
const ensemblData = ref(null)
const uniprotData = ref(null)
const loading = ref(true)

// Error state refs
const visualizationError = ref(null)
const ensemblError = ref(false)
const uniprotError = ref(false)

// Interaction refs
const hoveredPosition = ref(null)
const hoveredDomain = ref(null)

// Component refs for D3 cleanup
const geneStructureRef = ref(null)
const proteinDomainRef = ref(null)

// ResizeObserver ref for cleanup
let resizeObserver = null

// REQUIRED: Use unified breadcrumb system (commit 77ffc7b)
useBreadcrumbs([
  { title: 'Home', to: '/' },
  { title: 'Genes', to: '/genes' },
  { title: computed(() => gene.value?.approved_symbol || 'Loading...'),
    to: computed(() => `/genes/${route.params.symbol}`) },
  { title: 'Structure', disabled: true }
])

// Error handling
function handleVisualizationError(error) {
  console.error('Visualization error:', error)
  visualizationError.value = error.message || 'Failed to render visualization'
}

async function retryFetch() {
  visualizationError.value = null
  ensemblError.value = false
  uniprotError.value = false
  await fetchData()
}

// Fetch data on mount
onMounted(async () => {
  await fetchData()
})

// CRITICAL: Clean up D3 selections and observers on unmount to prevent memory leaks
onUnmounted(() => {
  // Clean up D3 selections from visualization components
  if (geneStructureRef.value?.$el) {
    d3.select(geneStructureRef.value.$el).selectAll('svg *').remove()
  }
  if (proteinDomainRef.value?.$el) {
    d3.select(proteinDomainRef.value.$el).selectAll('svg *').remove()
  }

  // Clean up ResizeObserver
  if (resizeObserver) {
    resizeObserver.disconnect()
    resizeObserver = null
  }

  // Clear any D3 tooltips that may have been appended to body
  d3.selectAll('.gene-structure-tooltip').remove()
  d3.selectAll('.protein-domain-tooltip').remove()
})

// ... fetch methods and helpers
</script>
```

#### REQUIRED: D3 Cleanup in Visualization Components

Each D3 visualization component MUST implement cleanup in `onUnmounted`:

```javascript
// In GeneStructureVisualization.vue or ProteinDomainVisualization.vue
import { onUnmounted, ref } from 'vue'
import * as d3 from 'd3'

const containerRef = ref(null)
let resizeObserver = null

onUnmounted(() => {
  // Clean up D3 selections to prevent memory leaks
  if (containerRef.value) {
    d3.select(containerRef.value).selectAll('*').remove()
  }

  // Clean up ResizeObserver
  if (resizeObserver) {
    resizeObserver.disconnect()
    resizeObserver = null
  }

  // Remove any tooltips appended to body
  d3.selectAll('.visualization-tooltip').remove()
})
```

### Changes to GeneDetail.vue (Minimal)

Only add a link to the structure page in the ClinVar section:

```vue
<!-- In ClinVarVariants.vue or GeneInformationCard.vue -->
<template>
  <div>
    <div class="d-flex align-center justify-space-between">
      <div class="text-body-2 font-weight-medium">Clinical Variants (ClinVar):</div>
      <v-btn
        v-if="hasStructureData"
        variant="text"
        size="x-small"
        density="compact"
        append-icon="mdi-chevron-right"
        :to="`/genes/${geneSymbol}/structure`"
      >
        View Structure
      </v-btn>
    </div>
    <!-- existing ClinVar chips -->
  </div>
</template>
```

---

## Interaction Design

### Hover Interactions

```
┌──────────────────────────────────────────────────────────────┐
│ User hovers over Exon 15 in Gene Structure                   │
│                                                              │
│ 1. Exon 15 highlights (brighter fill, border)               │
│ 2. Tooltip appears with exon details                         │
│ 3. Corresponding protein region highlights (if mappable)     │
│ 4. Connected by visual line/bracket                          │
└──────────────────────────────────────────────────────────────┘
```

### Tooltip Content - Gene Structure

```
┌─────────────────────────────────┐
│ Exon 15 of 46                   │
│ ─────────────────────────────── │
│ Size: 234 bp                    │
│ Position: 2,098,456-2,098,690   │
│ Phase: 0                        │
│ Codes for: aa 1,245-1,323       │
└─────────────────────────────────┘
```

### Tooltip Content - Protein Domain

```
┌─────────────────────────────────┐
│ PKD Domain                      │
│ ─────────────────────────────── │
│ Position: 1,245-1,323 (78 aa)   │
│ Source: Pfam PF00801            │
│ Description: Polycystin-1,      │
│ lipoxygenase, alpha-toxin       │
│ domain                          │
│                                 │
│ [View in Pfam ↗]                │
└─────────────────────────────────┘
```

### Click Actions

| Element | Click Action |
|---------|--------------|
| Exon | Zoom to exon, show detailed view |
| Domain | Open domain info panel or external link |
| Transcript ID | Copy to clipboard |
| Ensembl button | Open gene in Ensembl browser |
| UniProt button | Open protein in UniProt |

---

## Responsive Design

### Breakpoints

| Breakpoint | Behavior |
|------------|----------|
| **Desktop (≥1264px)** | Full visualization with all details |
| **Laptop (960-1263px)** | Slightly compressed, fewer labels |
| **Tablet (600-959px)** | Stacked tracks, simplified domains |
| **Mobile (<600px)** | Collapsed by default, expandable |

### Mobile Adaptation

```
┌─────────────────────────────────┐
│ Gene Structure & Domains    [▼] │
├─────────────────────────────────┤
│ (Collapsed by default)          │
│                                 │
│ Tap to expand visualization     │
│                                 │
│ 46 exons • 4303 aa • 12 domains │
└─────────────────────────────────┘
```

---

## Color Scheme

### Light Theme

| Element | Color | Hex |
|---------|-------|-----|
| Exon fill | Primary blue | `rgb(var(--v-theme-primary))` |
| Intron line | Grey | `#E0E0E0` |
| UTR | Light blue | `rgba(var(--v-theme-primary), 0.3)` |
| Pfam domain | Teal | `#009688` |
| InterPro domain | Purple | `#673AB7` |
| Transmembrane | Orange | `#FF9800` |
| Disordered | Grey dashed | `#9E9E9E` |

### Dark Theme

| Element | Color | Hex |
|---------|-------|-----|
| Exon fill | Primary blue (lighter) | `rgb(var(--v-theme-primary))` |
| Intron line | Dark grey | `#424242` |
| UTR | Translucent blue | `rgba(var(--v-theme-primary), 0.4)` |
| Pfam domain | Teal (lighter) | `#4DB6AC` |
| InterPro domain | Purple (lighter) | `#9575CD` |
| Transmembrane | Orange (lighter) | `#FFB74D` |
| Disordered | Light grey dashed | `#757575` |

### Theme Integration (Vuetify)

```javascript
// Use Vuetify's useTheme() composable
import { useTheme } from 'vuetify'

const theme = useTheme()
const isDark = computed(() => theme.global.current.value.dark)

// Dynamic color based on theme
const exonColor = computed(() =>
  isDark.value ? '#90CAF9' : '#1976D2'
)
```

---

## Accessibility Considerations

### WCAG 2.1 AA Compliance

| Requirement | Implementation |
|-------------|----------------|
| **Color contrast** | Minimum 4.5:1 for text, 3:1 for graphics |
| **Keyboard navigation** | Tab through exons/domains, Enter to select |
| **Screen readers** | ARIA labels for all interactive elements |
| **Focus indicators** | Visible focus ring on keyboard navigation |
| **Text alternatives** | Summary text below visualizations |

### ARIA Implementation

```html
<svg role="img" aria-label="Gene structure visualization showing 46 exons">
  <title>PKD1 Gene Structure</title>
  <desc>Exon-intron structure of PKD1 gene spanning 47.2 kilobases on chromosome 16</desc>

  <g role="list" aria-label="Exons">
    <rect role="listitem" aria-label="Exon 1, 234 base pairs" tabindex="0" />
    <!-- ... -->
  </g>
</svg>
```

---

## Performance Considerations

### Rendering Optimization

| Technique | Purpose |
|-----------|---------|
| **Canvas fallback** | For genes with >100 exons, use canvas instead of SVG |
| **Virtualization** | Only render visible domains in viewport |
| **Debounced resize** | Limit redraws on window resize |
| **Memoization** | Cache computed scale functions |

### Loading States

```vue
<template>
  <!-- Skeleton loader while fetching -->
  <v-skeleton-loader
    v-if="loading"
    type="image"
    height="200"
  />

  <!-- Error state -->
  <v-alert v-else-if="error" type="warning" variant="tonal">
    Gene structure data unavailable
  </v-alert>

  <!-- Visualization -->
  <GeneStructureVisualization v-else :data="geneData" />
</template>
```

---

## Implementation Checklist

### Phase 1: Subpage Infrastructure
- [ ] Create route `/genes/:symbol/structure` in `router/index.js`
- [ ] **Add route guard** with gene symbol validation (regex + API check)
- [ ] Create `GeneStructure.vue` page component in `views/`
- [ ] Add API endpoint for structure data (or use existing annotation endpoints)
- [ ] **Use unified breadcrumb system** (`useBreadcrumbs` composable from commit 77ffc7b)
- [ ] Add back link to parent gene page

### Phase 2: Entry Points (Minimal Changes to Main Page)
- [ ] Add "View Structure" link to ClinVar section in `GeneInformationCard.vue`
- [ ] Add subtle "Structure →" link near transcript ID in gene header
- [ ] (Optional) Add "View Structure" menu item in gene header dropdown
- [ ] **DO NOT** add any visualization components to `GeneDetail.vue`

### Phase 3: Basic Visualizations
- [ ] Implement `GeneStructureVisualization.vue` component (D3.js)
- [ ] Implement `ProteinDomainVisualization.vue` component (D3.js)
- [ ] **Add `@error` event emit** for visualization failures
- [ ] Create skeleton loaders for loading states
- [ ] **Add error alert component** with retry functionality
- [ ] Add external links (Ensembl, UniProt, Download SVG)
- [ ] Handle error states gracefully

### Phase 4: Interactivity
- [ ] Add hover tooltips to exons with details
- [ ] Add hover tooltips to domains with Pfam/InterPro links
- [ ] Implement exon-domain positional linking on hover
- [ ] Add keyboard navigation support (tab through elements)
- [ ] Add click-to-zoom functionality for large genes

### Phase 5: Memory Management & Cleanup (CRITICAL)
- [ ] **Implement `onUnmounted` cleanup** in all D3 visualization components
- [ ] **Clean up D3 selections** (`d3.select(el).selectAll('*').remove()`)
- [ ] **Disconnect ResizeObserver** instances
- [ ] **Remove D3 tooltips** appended to document body
- [ ] Add component refs for cleanup access from parent

### Phase 6: Polish & Accessibility
- [ ] Implement responsive breakpoints (desktop/tablet/mobile)
- [ ] Add WCAG 2.1 AA compliance (ARIA labels, contrast, focus)
- [ ] Performance optimization for genes with >100 exons
- [ ] Canvas fallback for very large visualizations
- [ ] Ensure proper dark/light theme support

### Phase 7: Advanced Features (Future)
- [ ] Variant overlay on gene structure (ClinVar pathogenic variants)
- [ ] Interactive variant filtering by exon/domain
- [ ] Export visualization as PNG/SVG
- [ ] Transcript comparison mode (canonical vs. other isoforms)

---

## References

### Frontend Libraries
- [Vuetify Grid System](https://vuetifyjs.com/en/components/grids/)
- [Vuetify Skeleton Loader](https://vuetifyjs.com/en/components/skeleton-loaders/)
- [D3.js Documentation](https://d3js.org/)
- [Vue 3 Composition API - onUnmounted](https://vuejs.org/api/composition-api-lifecycle.html#onunmounted)

### Accessibility
- [WCAG 2.1 Guidelines](https://www.w3.org/WAI/WCAG21/quickref/)
- [SVG Accessibility](https://developer.mozilla.org/en-US/docs/Web/Accessibility/ARIA/Roles/img_role)

### API Documentation
- [Ensembl REST API](https://rest.ensembl.org/) - Verified 2026-01-11
- [UniProt REST API](https://www.uniprot.org/help/api) - Verified 2026-01-11

### Related Plans
- [gene-protein-visualization.md](./gene-protein-visualization.md) - Main implementation plan
- [ensembl-uniprot-system-integration.md](./ensembl-uniprot-system-integration.md) - Backend integration

### Codebase References
- Unified breadcrumb system: commit 77ffc7b
- `useBreadcrumbs` composable: `frontend/src/composables/useBreadcrumbs.js`
- `AppBreadcrumbs` component: `frontend/src/components/layout/AppBreadcrumbs.vue`

---

**Document Status**: Ready for Review
**Author**: Expert UI/UX Analysis
**Last Updated**: 2026-01-11
**Review Status**: ✅ Added route guards, D3 cleanup, error boundaries, breadcrumb integration
