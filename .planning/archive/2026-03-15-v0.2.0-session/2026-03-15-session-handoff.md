# Session Handoff — 2026-03-15

## Resume Command

```
Read .planning/2026-03-15-session-handoff.md and .planning/2026-03-15-network-analysis-ux-plan.md and .planning/2026-03-15-pipeline-stability-audit.md to get full context. Then continue fixing the remaining issues listed below. The backend and frontend should already be running (make hybrid-up, make backend, make frontend). If not, start them. Use Playwright CLI to test all changes.
```

## Branch: `refactor/migration-squash` — 44 commits today

## Remaining Bugs (Priority Order)

### 1. Cluster selector doesn't toggle checkboxes on row click
- **File**: `frontend/src/views/NetworkAnalysis.vue` ~line 374
- **Issue**: The row `@click` handler calls `toggleCluster()` but the checkbox state doesn't visually update. The reka-ui Checkbox needs `v-model:checked` binding or the `@click` on the row conflicts with the checkbox's internal state management.
- **Fix approach**: Use `v-model:checked` with a computed getter/setter per cluster, OR remove the Checkbox component and use a simple div with a checkmark icon that's fully controlled by the reactive state.

### 2. Cytoscape "Cannot read properties of null (reading 'style')"
- **File**: `frontend/src/components/visualizations/NetworkVisualization.vue`
- **Issue**: Cytoscape tries to render before the container DOM element is mounted.
- **Fix approach**: Add `await nextTick()` before Cytoscape initialization, or use a `v-if` guard on the container ref.

### 3. Gene structure page broken (`/genes/PKHD1/structure`)
- **File**: Unknown — needs investigation
- **Issue**: User reported it broken, not yet investigated.

### 4. Network Analysis UI improvements (from `.planning/2026-03-15-network-analysis-ux-plan.md`)
- Merge "Network Construction" and "Network Filtering" into one section
- Compact scrollable cluster legend (replace wrapping badges)
- Better error display (show errors inline, not just console)
- Move enrichment closer to network visualization

## What's Working

| Page | Status |
|------|--------|
| `/` (Home) | 1,947+ genes, 7 sources |
| `/genes` | Filters, zero-score toggle, count slider |
| `/genes/PKHD1` | Gene detail page works |
| `/dashboard` | UpSet chart rendering |
| `/network-analysis` | Build + cluster works (UI bugs above) |
| `/data-sources` | 7 sources displayed |
| `/admin/pipeline` | Live progress, stable tiles, upload section |
| `/admin/annotations` | 10/10 sources, all annotated |
| Auth | Persists on refresh |

## Pipeline State
- **Evidence**: 7 sources (ClinGen, GenCC, HPO, PanelApp, PubTator, DiagnosticPanels, Literature)
- **Annotations**: 10 sources (hgnc, ensembl, gnomad, clinvar, hpo, mpo_mgi, string_ppi, uniprot, gtex, descartes)
- **PubTator**: May still be running keyword search (~5,734 pages)
- **Orchestrator**: Survives restarts by loading state from DB

## Key Architecture Decisions Made Today
- Gene-centric PubTator mode removed — keyword search only
- Annotation pipeline concurrency reduced to 1 (prevents DB pool starvation)
- Orchestrator loads completed/failed state from DB on restart
- DiagnosticPanels/Literature seeded after evidence sources create genes
- Frontend datasources API falls back to gene_evidence count when gene_scores view is stale
