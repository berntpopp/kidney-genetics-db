# Network Analysis UX Improvement Plan

> Based on thorough Playwright CLI testing of http://localhost:5173/network-analysis
> Tested: Filter → Build → Cluster → Enrichment full workflow

---

## Current Bugs Found

### Bug 1: Network stats show "undefined" after clustering
- **Location**: `NetworkVisualization.vue` or parent component
- **Symptom**: After "Detect Clusters", the header changes from "395 genes, 2151 interactions, 15 components" to "undefined genes, undefined interactions, undefined component(s)"
- **Root cause**: Clustering response replaces the network data but doesn't preserve the original node/edge/component counts
- **Priority**: P1

### Bug 2: Cluster selector dropdown overflows viewport
- **Location**: Enrichment section cluster multi-select
- **Symptom**: The dropdown opens but items are outside the viewport, can't be clicked by mouse
- **Root cause**: Popover/dialog position doesn't account for page scroll position
- **Priority**: P2

### Bug 3: "Run Analysis" stays disabled after selecting cluster
- **Location**: Enrichment section
- **Symptom**: Even after checking a cluster, the button remains disabled
- **Root cause**: Likely the cluster selection state isn't reactive or the JS click doesn't trigger Vue's change detection
- **Priority**: P1

---

## UX Improvement Recommendations

### 1. Simplify the Workflow Into a Guided Stepper

**Current**: 4 separate cards (Gene Selection, Network Construction, Network Filtering, Functional Enrichment) are all visible at once, creating cognitive overload. Users don't know what order to use them.

**Proposed**: Convert to a **3-step guided workflow** with clear progression:

```
Step 1: Select Genes          →  Step 2: Build & Explore Network  →  Step 3: Analyze Clusters
[Tiers, Score, Max Genes]        [Network viz + clustering]           [Enrichment results]
```

- Each step has a clear CTA button
- Previous steps collapse into a summary bar
- Next step is disabled until prerequisites are met
- Progress indicator shows current step

### 2. Merge "Network Construction" and "Network Filtering"

**Current**: Two separate cards for building and filtering. The user has to understand the difference between "Build Network" filtering (pre-build) and "Network Filtering" (post-build).

**Proposed**:
- Move MIN STRING Score into the Gene Selection step (it's a data quality filter)
- Move filtering options (Remove Isolated, Largest Component, Min Degree, Min Cluster Size) into an **accordion panel** within the network visualization area
- The "Tip" alert becomes a contextual tooltip on the filter icon

### 3. Improve Network Visualization Area

**Current issues**:
- Stats header shows "undefined" after clustering
- Controls (Layout, Clustering, Node Color, Search) are separate from the visualization
- Cluster legend takes too much horizontal space with 38 clusters

**Proposed**:
- **Sticky stats bar** above visualization showing: Nodes | Edges | Components | Clusters | Modularity
- **Collapsible sidebar** for controls instead of above the canvas
- **Scrollable cluster legend** with max-height, color swatches only (expand on hover)
- **Minimap** for large networks
- **Node tooltip** on hover showing gene symbol, evidence score, source count

### 4. Redesign Cluster Legend

**Current**: 38 colored badges in a wrapping flex container — hard to scan, takes lots of space.

**Proposed**:
- **Compact list view** with color dot + name + gene count
- Max height with scroll (e.g., 200px)
- Click to highlight cluster in network
- Double-click to zoom to cluster
- Sort options: by size, by modularity contribution

### 5. Improve Functional Enrichment Analysis

**Current issues**:
- Located at the bottom of a very long page — users may not find it
- Cluster selector dropdown overflows viewport
- No results display area visible
- GO and HPO enrichment options not clearly explained

**Proposed**:
- Move enrichment into a **right sidebar or tabbed panel** alongside the network visualization
- After clicking a cluster in the legend or network, auto-populate the enrichment cluster selector
- Show enrichment results as a **sortable table** with:
  - Term name, p-value, FDR, fold enrichment, gene count
  - Expandable rows showing which genes are in each term
- Add **bar chart visualization** for top enriched terms
- Add **export to CSV** button for results

### 6. Improve Gene Selection Section

**Current**: Tier badges, score input, max genes input, Filter button — functional but basic.

**Proposed**:
- Show a **live gene count preview** as filters change (before clicking "Filter Genes")
- Add a **gene list preview** (collapsible) showing the selected genes
- Add **quick presets**: "Top 100 genes", "All Comprehensive Support", "Custom gene list"
- Make the Share button more prominent — it's a powerful feature

### 7. Responsive Layout for Network + Results

**Current**: Everything is stacked vertically — lots of scrolling.

**Proposed layout** (for desktop):
```
┌─────────────────────────────────────────────────────────┐
│ Gene Selection (collapsible summary after filtering)    │
├─────────────────────────────────┬───────────────────────┤
│                                 │ Controls & Filters    │
│     Network Visualization       │ Cluster Legend        │
│     (takes most space)          │ Enrichment Results    │
│                                 │                       │
├─────────────────────────────────┴───────────────────────┤
│ Status bar: 395 genes | 2151 edges | 38 clusters        │
└─────────────────────────────────────────────────────────┘
```

### 8. Better Loading States

**Current**: Buttons show spinners but no progress indication for long operations.

**Proposed**:
- Skeleton loading for network area during build
- Progress bar for clustering (especially with large networks)
- Toast notification when enrichment analysis completes (it can take time)
- Disable ALL controls during network build/cluster (prevent conflicting requests)

### 9. Error Handling

**Current**: CORS errors and 500s show as generic network errors or nothing at all.

**Proposed**:
- Show inline error alerts in the relevant section (not just console)
- Retry button on errors
- Specific error messages: "STRING PPI data not available for these genes", "Network too large, reduce gene count"
- Log errors to the application log viewer

### 10. Accessibility & Keyboard Navigation

- Add ARIA labels to the network canvas
- Keyboard navigation between clusters (Tab, Enter to select)
- Screen reader announcements for network stats changes
- High contrast mode for cluster colors

---

## Implementation Priority

| Priority | Item | Effort | Impact |
|----------|------|--------|--------|
| **P0** | Fix "undefined" stats bug | Small | High |
| **P0** | Fix cluster selector overflow | Small | High |
| **P0** | Fix enrichment "Run Analysis" disabled | Small | High |
| **P1** | Merge construction + filtering | Medium | High |
| **P1** | Redesign cluster legend (compact list) | Medium | High |
| **P1** | Move enrichment to sidebar/tab | Medium | High |
| **P2** | Guided stepper workflow | Large | High |
| **P2** | Responsive 2-column layout | Large | High |
| **P2** | Better loading states | Small | Medium |
| **P2** | Error handling improvements | Medium | Medium |
| **P3** | Live gene count preview | Small | Medium |
| **P3** | Enrichment bar chart visualization | Medium | Medium |
| **P3** | Minimap for large networks | Medium | Low |
| **P3** | Accessibility improvements | Medium | Medium |

---

## Design References

- **Cytoscape.js** best practices: https://js.cytoscape.org/
- **STRING-DB** network visualization: https://string-db.org/ (good reference for cluster coloring and interaction display)
- **Enrichr** results display: https://maayanlab.cloud/Enrichr/ (excellent enrichment results UX)
- **DAVID** enrichment: https://david.ncifcrf.gov/ (table-based results reference)
- **shadcn/ui** components: Use ResizablePanel for sidebar, Tabs for enrichment types, DataTable for results
