# Dashboard Visualizations Enhancement Plan

**GitHub Issue**: #21
**Status**: Planning
**Priority**: Medium
**Effort**: 2-3 days

## Problem Statement

Current dashboard visualizations have limited interactivity and insight capabilities:
- Single-group bar charts without meaningful insights
- Basic Vue progress bars instead of proper charting libraries
- Static visualizations without drill-down analysis
- No cross-filtering or linked visualizations

## Proposed Solution

Replace basic components with **Vue Data UI** (native Vue 3 library):
- 63+ native Vue 3 components with zero external dependencies
- Excellent Vuetify integration
- TypeScript support, MIT licensed

## Key Visualizations

### 1. Multi-series Evidence Distribution (VueUiXy)
**Component**: Line/Bar chart with multi-series support
- Compare genetic/functional/clinical evidence across sources
- Interactive legends, tooltips, zoom/pan
- Export capabilities

**Data Source**: `/api/statistics/evidence-distribution`

### 2. Gene Network Graph (VueUiMolecule)
**Component**: Force-directed graph
- Visualize gene-disease relationships
- Interactive nodes with metadata tooltips
- Filter by evidence strength

**Data Source**: `/api/genes?include_relationships=true`

### 3. Evidence Quality Heatmap (VueUiHeatmap)
**Component**: Color-coded matrix
- Evidence scores by gene and source
- Quality indicators (Definitive/Strong/Moderate/Limited)
- Click-through to gene details

**Data Source**: `/api/statistics/evidence-heatmap`

### 4. Source Statistics (VueUiDonut)
**Component**: Donut/pie chart
- Distribution of genes across data sources
- Interactive slice selection
- Percentage and count display

**Data Source**: `/api/statistics/source-distribution` (existing)

## Implementation Priority

### Phase 1: Quick Wins (1 day)
1. ✅ Install Vue Data UI: `npm install vue-data-ui`
2. ✅ Replace source distribution with VueUiDonut
3. ✅ Basic theming to match Vuetify

### Phase 2: High Impact (1 day)
1. ⏳ Evidence distribution multi-series chart
2. ⏳ Add backend endpoint for evidence-distribution data
3. ⏳ Interactive filters (date range, classification)

### Phase 3: Advanced (1 day)
1. 📋 Evidence quality heatmap
2. 📋 Backend endpoint for heatmap data
3. 📋 Click-through navigation

### Phase 4: Exploratory (Optional)
1. 📋 Gene network graph
2. 📋 Complex relationship queries
3. 📋 Network analysis features

## Technical Requirements

### Frontend Changes

```bash
# Install dependency
npm install vue-data-ui
```

**Files to modify**:
- `frontend/src/views/DashboardPage.vue` - Main dashboard layout
- `frontend/src/components/dashboard/EvidenceChart.vue` - New component
- `frontend/src/components/dashboard/SourceDonut.vue` - Replace existing
- `frontend/src/stores/statistics.js` - Add new data fetching

### Backend Changes

**New API Endpoints**:
```python
# backend/app/api/endpoints/statistics.py

@router.get("/evidence-distribution")
async def get_evidence_distribution():
    """Multi-series data for evidence across sources"""
    return {
        "series": [
            {"name": "Genetic", "data": [...]},
            {"name": "Functional", "data": [...]},
            {"name": "Clinical", "data": [...]}
        ],
        "labels": ["PanelApp", "ClinGen", "GenCC", ...]
    }

@router.get("/evidence-heatmap")
async def get_evidence_heatmap():
    """Matrix of genes vs evidence scores"""
    return {
        "rows": ["PKD1", "PKD2", ...],  # Gene symbols
        "columns": ["PanelApp", "ClinGen", ...],  # Sources
        "data": [[0.8, 0.9, ...], ...]  # Scores 0-1
    }
```

## Vue Data UI Configuration Examples

### Donut Chart
```vue
<VueUiDonut
  :config="{
    style: {
      chart: {
        backgroundColor: theme.current.value.colors.surface,
        color: theme.current.value.colors.onSurface
      }
    },
    userOptions: {
      show: true
    },
    table: {
      show: false
    }
  }"
  :dataset="sourceDistribution"
/>
```

### Multi-Series Chart
```vue
<VueUiXy
  :config="{
    chart: {
      backgroundColor: theme.current.value.colors.surface,
      fontFamily: 'Roboto'
    },
    userOptions: {
      show: true,
      buttons: {
        csv: true,
        fullscreen: true,
        pdf: true
      }
    }
  }"
  :dataset="evidenceDistribution"
/>
```

## Success Metrics

- [ ] Source distribution donut chart replaces existing component
- [ ] Evidence distribution chart shows multi-series data
- [ ] Charts responsive and match Vuetify theme
- [ ] Export functionality works (CSV, PDF)
- [ ] Interactive tooltips provide detailed information
- [ ] Click-through navigation to gene details (Phase 3)

## Benefits

### User Experience
- **Better insights**: Multi-dimensional data visualization
- **Interactivity**: Drill-down, filtering, export
- **Professional**: Modern chart library with smooth animations

### Developer Experience
- **Native Vue 3**: No external framework dependencies
- **TypeScript**: Better autocomplete and type safety
- **Lightweight**: Tree-shakeable, minimal bundle size

### Data Analysis
- **Cross-filtering**: Link visualizations together
- **Export capabilities**: Share insights with collaborators
- **Responsive**: Works on mobile and desktop

## References

- **Vue Data UI**: https://github.com/graphieros/vue-data-ui
- **Documentation**: https://vue-data-ui.graphieros.com/
- **Examples**: https://vue-data-ui.graphieros.com/examples
- **GitHub Issue**: #21

## Migration Notes

**Current Implementation**:
```vue
<!-- OLD: Basic Vue component -->
<v-progress-linear :value="percentage" />
```

**New Implementation**:
```vue
<!-- NEW: Vue Data UI component -->
<VueUiDonut :dataset="data" :config="config" />
```

**Backward Compatibility**: Can keep existing components during migration, replace one at a time.

## Estimated Timeline

- **Day 1**: Install library, replace source donut, test theming
- **Day 2**: Evidence distribution chart + backend endpoint
- **Day 3**: Evidence heatmap + advanced features

**Total**: 2-3 days for Phases 1-2 (high value items)

## Dependencies

- `vue-data-ui`: ^2.x (check for latest version)
- No breaking changes to existing code
- Fully compatible with Vuetify 3

## Next Steps

1. Install `vue-data-ui` package
2. Create proof-of-concept with source distribution donut
3. Test Vuetify theme integration
4. Implement evidence distribution chart
5. Add backend endpoints for new data
6. Optional: Implement heatmap and network graph
