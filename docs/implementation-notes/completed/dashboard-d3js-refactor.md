# Dashboard Visualizations - D3.js Refactor Plan

**Parent Issue**: #21
**Status**: 🟡 In Progress
**Priority**: High
**Estimated Effort**: 8-12 hours (1-1.5 days)
**Created**: 2025-10-06
**Reason**: vue-data-ui complexity and configuration issues

---

## Executive Summary

Refactor dashboard visualizations to use **pure D3.js** instead of vue-data-ui, eliminating dependency issues and providing full control over chart rendering.

**Problem Statement:**
- vue-data-ui has configuration issues (tables showing despite `show: false`)
- Complex data format requirements (`values: []` vs `series: []`)
- Large bundle size for simple charts
- Limited customization control

**Solution:**
- Leverage existing D3.js expertise (UpSetChart.vue already using D3)
- Create reusable D3 chart components following established patterns
- Remove vue-data-ui dependency entirely
- Maintain all current functionality with cleaner implementation

---

## Current State Analysis

### Charts Using vue-data-ui (TO REPLACE)

1. **VueUiDonut** - Classification distributions (ClinGen/GenCC)
   - Location: `SourceDistributionsChart.vue`
   - Issues: Table component, legend removal problems
   - Data: `{ name: string, values: [number], color: string }[]`

2. **VueUiStackbar** - Count distributions (PanelApp/PubTator/HPO)
   - Location: `SourceDistributionsChart.vue`
   - Issues: Complex series data format
   - Data: `{ name: string, series: [number] }[]`

3. **VueUiDonut** - Evidence tier distribution
   - Location: `EvidenceCompositionChart.vue`
   - Issues: Same as #1

### Charts Already Using D3.js (REFERENCE PATTERN)

✅ **UpSetChart.vue** - Gene source overlaps
- Clean Vue 3 Composition API setup
- Proper ResizeObserver for responsiveness
- Theme integration with `useTheme()`
- Cleanup with `onUnmounted()`
- Data validation before rendering

---

## D3.js Component Architecture

### Base Pattern (from UpSetChart.vue)

```javascript
// ✅ Standard structure for all D3 components
import { ref, onMounted, onUnmounted, watch, nextTick } from 'vue'
import { useTheme } from 'vuetify'
import * as d3 from 'd3'

const theme = useTheme()
const chartContainer = ref(null)
let resizeObserver = null

// Render function with:
// - Container dimension validation
// - Clear previous chart
// - Create SVG
// - Theme-aware colors
// - Smooth transitions

// Setup:
// - ResizeObserver for responsiveness
// - Watch data changes
// - Watch theme changes
// - Cleanup on unmount
```

---

## Implementation Phases

### Phase 1: D3 Donut Chart Component (2-3 hours)

**File**: `frontend/src/components/visualizations/D3DonutChart.vue`

**Props Interface:**
```typescript
interface Props {
  data: Array<{
    category: string
    gene_count: number
    color?: string  // Optional, can use default color scale
  }>
  total?: number    // For center text
  average?: number  // For center text
  centerLabel?: string  // Default: "Total"
  width?: number    // Container manages sizing
  height?: number   // Default: 400
}
```

**Features:**
- ✅ Clean donut with hole in center
- ✅ Center text group showing total/average
- ✅ Color-coded segments (from props or color scale)
- ✅ Hover tooltips with category and count
- ✅ Smooth arc transitions on data changes
- ✅ Responsive sizing with ResizeObserver
- ✅ Theme-aware colors (light/dark mode)
- ✅ No legend, no table, no extra UI

**D3 Implementation Details:**
```javascript
// Layout
const pie = d3.pie()
  .value(d => d.gene_count)
  .sort(null)

// Arc generator
const arc = d3.arc()
  .innerRadius(radius * 0.6)  // Donut hole
  .outerRadius(radius)

// Color scale (if colors not provided)
const colorScale = d3.scaleOrdinal(d3.schemeCategory10)

// Segments with transitions
const paths = g.selectAll('path')
  .data(pieData)
  .join('path')
  .attr('d', arc)
  .attr('fill', d => d.data.color || colorScale(d.data.category))
  .on('mouseover', showTooltip)
  .on('mouseout', hideTooltip)
  .transition()
  .duration(750)
  .attrTween('d', arcTween)

// Center text
const centerGroup = svg.append('g')
  .attr('transform', `translate(${width/2}, ${height/2})`)

centerGroup.append('text')
  .attr('text-anchor', 'middle')
  .attr('dy', '-0.5em')
  .style('font-size', '14px')
  .text(props.centerLabel || 'Total')

centerGroup.append('text')
  .attr('text-anchor', 'middle')
  .attr('dy', '1.5em')
  .style('font-size', '24px')
  .style('font-weight', 'bold')
  .text(props.total || d3.sum(props.data, d => d.gene_count))
```

**Tooltip Implementation:**
```javascript
// Create tooltip div
const tooltip = d3.select('body').append('div')
  .attr('class', 'chart-tooltip')
  .style('opacity', 0)

function showTooltip(event, d) {
  tooltip.transition().duration(200).style('opacity', .9)
  tooltip.html(`
    <strong>${d.data.category}</strong><br/>
    ${d.data.gene_count} genes
  `)
  .style('left', (event.pageX + 10) + 'px')
  .style('top', (event.pageY - 28) + 'px')
}

function hideTooltip() {
  tooltip.transition().duration(500).style('opacity', 0)
}
```

---

### Phase 2: D3 Bar Chart Component (2-3 hours)

**File**: `frontend/src/components/visualizations/D3BarChart.vue`

**Props Interface:**
```typescript
interface Props {
  data: Array<{
    category: string
    gene_count: number
  }>
  xAxisLabel?: string  // e.g., "Panel Count"
  yAxisLabel?: string  // e.g., "Gene Count"
  barColor?: string    // Default: theme primary color
  height?: number      // Default: 400
}
```

**Features:**
- ✅ Vertical bars with proper spacing
- ✅ X-axis with category labels (rotated if needed)
- ✅ Y-axis with gene count scale
- ✅ Hover effects (highlight bar + tooltip)
- ✅ Responsive scales that adjust to container
- ✅ Theme-aware colors and text
- ✅ Grid lines for readability
- ✅ Axis labels

**D3 Implementation Details:**
```javascript
// Margins for axes
const margin = { top: 20, right: 20, bottom: 60, left: 60 }
const innerWidth = width - margin.left - margin.right
const innerHeight = height - margin.top - margin.bottom

// Scales
const xScale = d3.scaleBand()
  .domain(props.data.map(d => d.category))
  .range([0, innerWidth])
  .padding(0.2)

const yScale = d3.scaleLinear()
  .domain([0, d3.max(props.data, d => d.gene_count)])
  .nice()
  .range([innerHeight, 0])

// Axes
const xAxis = d3.axisBottom(xScale)
const yAxis = d3.axisLeft(yScale)

// Grid lines
svg.append('g')
  .attr('class', 'grid')
  .attr('transform', `translate(0,${innerHeight})`)
  .call(d3.axisBottom(xScale).tickSize(-innerHeight).tickFormat(''))
  .style('stroke-opacity', 0.1)

// Bars
svg.selectAll('rect')
  .data(props.data)
  .join('rect')
  .attr('x', d => xScale(d.category))
  .attr('width', xScale.bandwidth())
  .attr('y', innerHeight)  // Start from bottom
  .attr('height', 0)       // Start with 0 height
  .attr('fill', props.barColor || theme.global.current.value.colors.primary)
  .on('mouseover', highlightBar)
  .on('mouseout', unhighlightBar)
  .transition()
  .duration(750)
  .attr('y', d => yScale(d.gene_count))
  .attr('height', d => innerHeight - yScale(d.gene_count))

// Axis labels
svg.append('text')
  .attr('transform', `translate(${innerWidth/2}, ${height - 10})`)
  .style('text-anchor', 'middle')
  .text(props.xAxisLabel || '')

svg.append('text')
  .attr('transform', 'rotate(-90)')
  .attr('y', -margin.left + 15)
  .attr('x', -innerHeight/2)
  .style('text-anchor', 'middle')
  .text(props.yAxisLabel || '')
```

---

### Phase 3: Component Integration (1-2 hours)

**Update**: `frontend/src/components/visualizations/SourceDistributionsChart.vue`

**Changes:**

1. **Remove vue-data-ui imports:**
```vue
<script setup>
// REMOVE:
// import { VueUiDonut, VueUiStackbar } from 'vue-data-ui'

// ADD:
import D3DonutChart from './D3DonutChart.vue'
import D3BarChart from './D3BarChart.vue'
</script>
```

2. **Update template:**
```vue
<template>
  <v-card class="source-distributions-container">
    <!-- ... existing card header ... -->

    <v-card-text>
      <!-- ... existing loading/error states ... -->

      <div v-else-if="data && selectedSource && sourceData">
        <!-- ... existing metadata card ... -->

        <!-- Dynamic chart based on visualization type -->
        <div v-if="hasDistributionData" class="chart-container">
          <!-- ClinGen/GenCC: D3 Donut for classifications -->
          <D3DonutChart
            v-if="visualizationType === 'classification_donut'"
            :data="classificationData"
            :total="sourceMetadata.total_genes"
            :average="sourceMetadata.average"
            center-label="Total"
          />

          <!-- All other sources: D3 Bar Chart -->
          <D3BarChart
            v-else
            :data="histogramData"
            :x-axis-label="getXAxisLabel(selectedSource)"
            :y-axis-label="'Gene Count'"
          />
        </div>
      </div>
    </v-card-text>
  </v-card>
</template>
```

3. **Update data transformations:**
```javascript
// Simplified data format for D3 components
const classificationData = computed(() => {
  if (!sourceData.value?.distribution) return []

  return sourceData.value.distribution.map(d => ({
    category: d.category,
    gene_count: d.gene_count,
    color: getCategoryColor(d.category)  // Optional color mapping
  }))
})

const histogramData = computed(() => {
  if (!sourceData.value?.distribution) return []

  return sourceData.value.distribution.map(d => ({
    category: String(d.category),
    gene_count: d.gene_count
  }))
})

function getXAxisLabel(source) {
  const labels = {
    'PanelApp': 'Panel Count',
    'PubTator': 'Publication Count',
    'HPO': 'Phenotype Count Range',
    'DiagnosticPanels': 'Provider'
  }
  return labels[source] || 'Category'
}
```

---

### Phase 4: Evidence Composition Update (1 hour)

**Update**: `frontend/src/components/visualizations/EvidenceCompositionChart.vue`

**Changes:**
```vue
<script setup>
// REMOVE: import { VueUiDonut } from 'vue-data-ui'
// ADD:
import D3DonutChart from './D3DonutChart.vue'
</script>

<template>
  <v-card>
    <v-card-title>Evidence Tier Distribution</v-card-title>

    <v-row>
      <v-col cols="12" md="6">
        <D3DonutChart
          :data="tierDonutData"
          :total="totalGenes"
          center-label="Total Genes"
        />
      </v-col>

      <v-col cols="12" md="6">
        <!-- Existing table -->
      </v-col>
    </v-row>
  </v-card>
</template>

<script setup>
const tierDonutData = computed(() => {
  if (!tierDistribution.value) return []

  return tierDistribution.value.map(tier => ({
    category: tier.tier_label,
    gene_count: tier.gene_count,
    color: tier.color  // From backend config
  }))
})

const totalGenes = computed(() =>
  tierDistribution.value?.reduce((sum, t) => sum + t.gene_count, 0) || 0
)
</script>
```

---

### Phase 5: Dependency Cleanup & Testing (30 min)

**Tasks:**

1. **Remove vue-data-ui dependency:**
```bash
cd frontend
npm uninstall vue-data-ui
```

2. **Update package.json** (verify removal):
```json
{
  "dependencies": {
    // vue-data-ui should be removed
  }
}
```

3. **Verify no import errors:**
```bash
npm run lint
```

4. **Test all charts:**
- ClinGen donut chart (classification distribution)
- GenCC donut chart (classification distribution)
- PanelApp bar chart (panel count)
- PubTator bar chart (publication count)
- HPO bar chart (phenotype ranges)
- Evidence composition donut chart

5. **Test responsiveness:**
- Resize browser window
- Switch between tabs
- Toggle theme (light/dark)

---

## Shared Chart Utilities

**File**: `frontend/src/components/visualizations/d3-chart-utils.js`

```javascript
/**
 * Shared utilities for D3 chart components
 */

/**
 * Get theme-aware colors
 */
export function getThemeColors(theme) {
  return {
    text: theme.global.current.value.colors['on-surface'],
    background: theme.global.current.value.colors.surface,
    grid: theme.global.current.value.colors.outline,
    primary: theme.global.current.value.colors.primary
  }
}

/**
 * Create responsive tooltip
 */
export function createTooltip() {
  return d3.select('body').append('div')
    .attr('class', 'chart-tooltip')
    .style('position', 'absolute')
    .style('pointer-events', 'none')
    .style('opacity', 0)
}

/**
 * Validate container dimensions
 */
export function validateDimensions(container, minWidth = 100, minHeight = 100) {
  const width = container.clientWidth
  const height = container.clientHeight || 400

  if (width < minWidth || height < minHeight) {
    console.warn('Container too small for chart', { width, height, minWidth, minHeight })
    return null
  }

  return { width, height }
}

/**
 * Setup resize observer
 */
export function setupResizeObserver(element, callback) {
  const observer = new ResizeObserver(() => callback())
  observer.observe(element)
  return observer
}
```

---

## Shared Tooltip Styles

**File**: `frontend/src/components/visualizations/chart-tooltip.css`

```css
/* Theme-aware tooltip styles */
.chart-tooltip {
  position: absolute;
  pointer-events: none;
  background: var(--v-theme-surface);
  color: var(--v-theme-on-surface);
  border: 1px solid var(--v-theme-outline);
  padding: 8px 12px;
  border-radius: 4px;
  font-size: 12px;
  line-height: 1.4;
  z-index: 1000;
  box-shadow: 0 2px 8px rgba(0,0,0,0.15);
  transition: opacity 0.2s;
}

.chart-tooltip strong {
  color: var(--v-theme-primary);
  display: block;
  margin-bottom: 4px;
}
```

---

## Key Advantages of D3.js Approach

### 1. **Full Control**
- No hidden tables, legends, or unwanted UI elements
- Complete customization of every visual element
- Direct access to SVG DOM

### 2. **Smaller Bundle**
- D3 already used for UpSet chart (no new dependency)
- Remove vue-data-ui (~200KB minified)
- Only include D3 modules we need

### 3. **Better Performance**
- Optimized rendering with D3 selections
- Efficient data binding and transitions
- No framework overhead

### 4. **Theme Integration**
- Direct access to Vuetify theme colors via `useTheme()`
- Automatic dark/light mode support
- Consistent with app design system

### 5. **Maintainability**
- Consistent patterns across all D3 charts
- Follows proven UpSetChart.vue patterns
- Easy to debug and modify

### 6. **Responsiveness**
- ResizeObserver for automatic resize
- Scales adapt to container dimensions
- Mobile-friendly

---

## Testing Checklist

### Unit Tests (Optional - Complex)
- [ ] D3DonutChart renders with valid data
- [ ] D3BarChart renders with valid data
- [ ] Charts handle empty data gracefully
- [ ] Charts handle theme changes
- [ ] Tooltips show correct information

### Integration Tests
- [ ] SourceDistributionsChart switches between donut/bar correctly
- [ ] EvidenceCompositionChart shows tier donut
- [ ] All charts respond to window resize
- [ ] Theme toggle updates chart colors
- [ ] Data updates trigger chart re-render

### Manual Testing
- [ ] ClinGen: Donut with classifications (Definitive, Strong, etc.)
- [ ] GenCC: Donut with classifications
- [ ] PanelApp: Bar chart with panel counts
- [ ] PubTator: Bar chart with publication counts
- [ ] HPO: Bar chart with phenotype ranges
- [ ] DiagnosticPanels: Bar chart with providers
- [ ] Evidence tiers: Donut with confidence levels
- [ ] All charts show tooltips on hover
- [ ] All charts resize smoothly
- [ ] Dark/light theme works correctly

---

## Success Criteria

- [ ] All vue-data-ui charts replaced with D3.js equivalents
- [ ] No unwanted UI elements (tables, legends) in charts
- [ ] vue-data-ui dependency removed from package.json
- [ ] All charts render correctly with real data
- [ ] Charts are responsive and theme-aware
- [ ] No console errors or warnings
- [ ] Performance is equal or better than vue-data-ui
- [ ] Code follows UpSetChart.vue pattern

---

## Timeline Estimate

| Phase | Task | Time |
|-------|------|------|
| 1 | D3 Donut Chart Component | 2-3 hours |
| 2 | D3 Bar Chart Component | 2-3 hours |
| 3 | Component Integration | 1-2 hours |
| 4 | Evidence Composition Update | 1 hour |
| 5 | Cleanup & Testing | 30 min - 1 hour |
| | **Total** | **8-12 hours** |

**Estimated completion**: 1-1.5 days

---

## Files to Create/Modify

### New Files
- `frontend/src/components/visualizations/D3DonutChart.vue`
- `frontend/src/components/visualizations/D3BarChart.vue`
- `frontend/src/components/visualizations/d3-chart-utils.js` (optional)
- `frontend/src/components/visualizations/chart-tooltip.css` (optional)

### Modified Files
- `frontend/src/components/visualizations/SourceDistributionsChart.vue`
- `frontend/src/components/visualizations/EvidenceCompositionChart.vue`
- `frontend/package.json` (remove vue-data-ui)
- `frontend/package-lock.json` (auto-updated)

### Reference Files (No changes)
- `frontend/src/components/visualizations/UpSetChart.vue` (pattern reference)

---

## Next Steps

1. ✅ Create implementation plan (this document)
2. ⏳ Create D3DonutChart.vue component
3. ⏳ Create D3BarChart.vue component
4. ⏳ Update SourceDistributionsChart.vue
5. ⏳ Update EvidenceCompositionChart.vue
6. ⏳ Remove vue-data-ui dependency
7. ⏳ Test all visualizations
8. ⏳ Mark task complete and move to completed notes

**Status**: 🟡 Ready to implement Phase 1
