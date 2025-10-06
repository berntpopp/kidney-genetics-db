<template>
  <v-card class="upset-chart-container">
    <v-card-title class="d-flex align-center">
      <v-icon class="me-2">mdi-chart-scatter-plot</v-icon>
      Gene Source Overlaps
      <v-tooltip location="bottom">
        <template #activator="{ props }">
          <v-icon v-bind="props" class="me-2 text-medium-emphasis" size="small">
            mdi-help-circle-outline
          </v-icon>
        </template>
        <span
          >UpSet plot showing intersections between gene data sources. Click bars or dots to see
          genes in each intersection.</span
        >
      </v-tooltip>
      <v-spacer />
      <v-tooltip v-if="data" location="bottom" max-width="300">
        <template #activator="{ props }">
          <v-chip v-bind="props" variant="outlined" size="small" class="me-2">
            {{ data.total_unique_genes.toLocaleString() }} genes
          </v-chip>
        </template>
        <div class="pa-2">
          <strong>Genes with evidence:</strong> {{ data.total_unique_genes.toLocaleString() }} genes
          with evidence score > 0 <br />These genes have kidney disease associations from at least
          one data source
        </div>
      </v-tooltip>
      <v-btn
        icon="mdi-refresh"
        variant="text"
        size="small"
        :loading="loading"
        @click="refreshData"
      />
    </v-card-title>

    <v-card-text>
      <!-- Loading state -->
      <div v-if="loading" class="d-flex justify-center align-center" style="height: 400px">
        <v-progress-circular indeterminate size="64" />
      </div>

      <!-- Error state -->
      <v-alert v-else-if="error" type="error" variant="outlined" class="mb-4">
        {{ error }}
      </v-alert>

      <!-- UpSet visualization -->
      <div v-else-if="data">
        <!-- Summary stats -->
        <div class="mb-4">
          <v-row class="text-center">
            <v-col cols="12" sm="3">
              <div class="text-h6 text-primary">{{ data.sets.length }}</div>
              <div class="text-caption">Data Sources</div>
            </v-col>
            <v-col cols="12" sm="3">
              <div class="text-h6 text-primary">{{ data.intersections.length }}</div>
              <div class="text-caption">Intersections</div>
            </v-col>
            <v-col cols="12" sm="3">
              <div class="text-h6 text-primary">
                {{ data.overlap_statistics.genes_in_all_sources }}
              </div>
              <div class="text-caption">In All Sources</div>
            </v-col>
            <v-col cols="12" sm="3">
              <div class="text-h6 text-primary">
                {{ data.overlap_statistics.single_source_combinations }}
              </div>
              <div class="text-caption">Single Source Only</div>
            </v-col>
          </v-row>
        </div>

        <v-divider class="mb-4" />

        <!-- Source Selection Interface -->
        <div class="source-selection-container mb-4">
          <div class="d-flex align-center flex-wrap gap-2">
            <div class="d-flex align-center">
              <v-icon class="me-2" size="small">mdi-filter-outline</v-icon>
              <span class="text-subtitle-2">Selected Sources ({{ selectedSources.length }}):</span>
            </div>

            <!-- Source chips inline -->
            <v-chip
              v-for="source in selectedSources"
              :key="source"
              class="ma-1"
              closable
              color="primary"
              variant="flat"
              size="small"
              @click:close="removeSource(source)"
            >
              {{ source }}
            </v-chip>

            <!-- Select All chip (appears when not all sources are selected) -->
            <v-chip
              v-if="selectedSources.length < availableSources.length"
              class="ma-1"
              variant="outlined"
              color="success"
              prepend-icon="mdi-select-all"
              size="small"
              @click="selectAllSources"
            >
              Select All
            </v-chip>

            <!-- Add source menu -->
            <v-menu v-if="availableToAdd.length > 0">
              <template #activator="{ props }">
                <v-chip
                  v-bind="props"
                  class="ma-1"
                  variant="outlined"
                  color="primary"
                  prepend-icon="mdi-plus"
                  size="small"
                >
                  Add Source
                </v-chip>
              </template>
              <v-list>
                <v-list-item
                  v-for="source in availableToAdd"
                  :key="source"
                  @click="addSource(source)"
                >
                  <v-list-item-title>{{ source }}</v-list-item-title>
                </v-list-item>
              </v-list>
            </v-menu>
          </div>
        </div>

        <!-- UpSet Plot -->
        <div
          v-if="selectedSources.length > 0"
          ref="upsetContainer"
          class="upset-plot"
          style="min-height: 500px; width: 100%"
        ></div>

        <!-- Empty state when no sources selected -->
        <div v-else class="empty-state">
          <v-icon size="64" color="grey-lighten-1">mdi-chart-scatter-plot-hexbin</v-icon>
          <h3 class="text-h6 mt-4 mb-2 text-grey-lighten-1">No Sources Selected</h3>
          <p class="text-body-2 text-grey">
            Select one or more data sources above to view the UpSet plot visualization.
          </p>
        </div>

        <!-- Selected intersection details -->
        <v-card v-if="selectedIntersection" variant="outlined" class="mt-4">
          <v-card-title class="text-h6">
            Selected Intersection: {{ selectedIntersection.sets.join(' ∩ ') }}
          </v-card-title>
          <v-card-text>
            <div class="mb-2">
              <strong>{{ selectedIntersection.size }}</strong> genes in this intersection
            </div>
            <v-chip-group v-if="selectedIntersection.genes.length <= 20">
              <v-chip
                v-for="gene in selectedIntersection.genes"
                :key="gene"
                size="small"
                variant="outlined"
              >
                {{ gene }}
              </v-chip>
            </v-chip-group>
            <div v-else>
              <div class="mb-2">First 20 genes:</div>
              <v-chip-group>
                <v-chip
                  v-for="gene in selectedIntersection.genes.slice(0, 20)"
                  :key="gene"
                  size="small"
                  variant="outlined"
                >
                  {{ gene }}
                </v-chip>
              </v-chip-group>
              <div class="text-caption mt-2">
                ... and {{ selectedIntersection.genes.length - 20 }} more genes
              </div>
            </div>
          </v-card-text>
        </v-card>
      </div>
    </v-card-text>
  </v-card>
</template>

<script setup>
import { ref, computed, onMounted, onUnmounted, nextTick, watch } from 'vue'
import { statisticsApi } from '@/api/statistics'
import * as d3 from 'd3'

// Props
const props = defineProps({
  minTier: {
    type: String,
    default: null
  }
})

// Reactive data
const loading = ref(false)
const error = ref(null)
const data = ref(null)
const selectedIntersection = ref(null)
const upsetContainer = ref(null)

// Source selection state
const selectedSources = ref([])
const availableSources = ref([])

// Computed properties
const availableToAdd = computed(() =>
  availableSources.value.filter(source => !selectedSources.value.includes(source))
)

// Initial load to get available sources
const loadAvailableSources = async () => {
  try {
    const response = await statisticsApi.getSourceOverlaps(null, props.minTier) // Get all sources with tier filter
    if (response.data?.sets) {
      const sources = response.data.sets.map(set => set.name).sort()
      availableSources.value = sources
      // Select all sources by default on first load
      if (selectedSources.value.length === 0) {
        selectedSources.value = [...sources]
      }
    }
  } catch (err) {
    window.logService.error('Error loading available sources:', err)
  }
}

// Load data
const loadData = async () => {
  loading.value = true
  error.value = null

  try {
    // If no sources selected, show empty state
    if (selectedSources.value.length === 0) {
      data.value = null
      loading.value = false
      return
    }

    // Call API with selected sources and tier filter
    window.logService.info(
      'Calling API with sources:',
      selectedSources.value,
      'and minTier:',
      props.minTier
    )
    const response = await statisticsApi.getSourceOverlaps(selectedSources.value, props.minTier)
    window.logService.info('API response:', response.data)
    data.value = response.data

    // Render UpSet plot after data is loaded
    await nextTick()
    // Add a small delay to ensure DOM is fully rendered
    setTimeout(() => {
      renderUpSetPlot()
    }, 100)
  } catch (err) {
    error.value = err.message || 'Failed to load source overlap data'
    window.logService.error('Error loading source overlaps:', err)
  } finally {
    loading.value = false
  }
}

const refreshData = () => {
  loadData()
}

// Source selection methods
const addSource = source => {
  if (!selectedSources.value.includes(source)) {
    window.logService.info('Adding source:', source)
    // Create new array to ensure reactivity
    selectedSources.value = [...selectedSources.value, source]
    window.logService.info('New selected sources:', selectedSources.value)
  }
}

const removeSource = async source => {
  const index = selectedSources.value.indexOf(source)
  if (index > -1) {
    window.logService.info('Removing source:', source)
    // Create new array to ensure reactivity
    selectedSources.value = selectedSources.value.filter(s => s !== source)
    window.logService.info('New selected sources:', selectedSources.value)
  }
}

const selectAllSources = () => {
  window.logService.info('Selecting all sources')
  selectedSources.value = [...availableSources.value]
  window.logService.info('New selected sources:', selectedSources.value)
}

// Watch for changes in selectedSources and reload data
watch(
  selectedSources,
  async (newSources, oldSources) => {
    // Only reload if sources actually changed and we're not in the initial load
    if (oldSources && newSources.length !== oldSources.length) {
      window.logService.info(
        'Source count changed from',
        oldSources.length,
        'to',
        newSources.length
      )
      window.logService.info('Previous sources:', oldSources)
      window.logService.info('New sources:', newSources)
      await loadData()
    }
  },
  { deep: true, immediate: false }
)

// Watch for minTier changes and reload data
watch(
  () => props.minTier,
  async (newTier, oldTier) => {
    if (newTier !== oldTier) {
      window.logService.info('Tier filter changed from', oldTier, 'to', newTier)
      await loadAvailableSources()
      await loadData()
    }
  }
)

// Render UpSet plot using D3
const renderUpSetPlot = () => {
  if (!data.value || !upsetContainer.value) {
    return
  }

  // Clear any existing plot
  d3.select(upsetContainer.value).selectAll('*').remove()

  const margin = { top: 40, right: 40, bottom: 120, left: 120 }
  const containerWidth = upsetContainer.value.clientWidth
  const containerHeight = 500
  const width = containerWidth - margin.left - margin.right
  const height = containerHeight - margin.top - margin.bottom

  // Validate dimensions - don't render if container is too small
  const minWidth = 400
  const minHeight = 300
  if (width < minWidth || height < minHeight) {
    window.logService.warn('Container too small for UpSet plot', {
      containerWidth,
      width,
      height,
      minWidth,
      minHeight
    })

    // Show message in container
    d3
      .select(upsetContainer.value)
      .append('div')
      .style('display', 'flex')
      .style('align-items', 'center')
      .style('justify-content', 'center')
      .style('height', '100%')
      .style('color', 'var(--v-theme-on-surface-variant)')
      .style('text-align', 'center')
      .style('padding', '20px').html(`
        <div>
          <p>Container too small to display chart</p>
          <p style="font-size: 0.875rem; margin-top: 8px;">
            Minimum width: ${minWidth}px (current: ${Math.round(containerWidth)}px)
          </p>
        </div>
      `)
    return
  }

  // Create SVG
  const svg = d3
    .select(upsetContainer.value)
    .append('svg')
    .attr('width', containerWidth)
    .attr('height', containerHeight)

  const g = svg.append('g').attr('transform', `translate(${margin.left},${margin.top})`)

  // Prepare data
  const sets = data.value.sets
  const intersections = data.value.intersections.sort((a, b) => b.size - a.size)

  // Set up scales
  const maxSetSize = Math.max(...sets.map(d => d.size), 1) // Ensure at least 1
  const maxIntersectionSize = Math.max(...intersections.map(d => d.size), 1) // Ensure at least 1

  // Horizontal scale for set sizes (left bars)
  const setScale = d3
    .scaleLinear()
    .domain([0, maxSetSize])
    .range([0, Math.max(width * 0.25, 0)]) // Ensure non-negative

  // Vertical scale for intersection sizes (top bars)
  const intersectionScale = d3
    .scaleLinear()
    .domain([0, maxIntersectionSize])
    .range([height * 0.6, 0])

  // Position scales
  const setsY = d3
    .scaleBand()
    .domain(sets.map(d => d.name))
    .range([height * 0.6, height])
    .padding(0.1)

  const intersectionsX = d3
    .scaleBand()
    .domain(intersections.map((d, i) => i))
    .range([Math.max(width * 0.3, 0), width]) // Ensure start is non-negative
    .padding(0.1)

  // 1. Draw set size bars (horizontal bars on the left)
  g.selectAll('.set-bar')
    .data(sets)
    .enter()
    .append('rect')
    .attr('class', 'set-bar')
    .attr('x', Math.max(width * 0.25 - setScale.range()[1], 0))
    .attr('y', d => setsY(d.name))
    .attr('width', d => Math.max(setScale(d.size), 0)) // Ensure non-negative width
    .attr('height', setsY.bandwidth())
    .attr('fill', '#0EA5E9')
    .attr('opacity', 0.8)
    .style('cursor', 'pointer')
    .on('mouseover', function () {
      d3.select(this)
        .attr('opacity', 1)
        .attr('stroke', 'rgb(var(--v-theme-on-surface))')
        .attr('stroke-width', 1)
    })
    .on('mouseout', function () {
      d3.select(this).attr('opacity', 0.8).attr('stroke', 'none')
    })

  // Set labels
  g.selectAll('.set-label')
    .data(sets)
    .enter()
    .append('text')
    .attr('class', 'set-label')
    .attr('x', width * 0.25 - setScale.range()[1] - 10)
    .attr('y', d => setsY(d.name) + setsY.bandwidth() / 2)
    .attr('text-anchor', 'end')
    .attr('dominant-baseline', 'middle')
    .attr('font-size', '12px')
    .attr('font-weight', '500')
    .attr('fill', 'currentColor')
    .text(d => d.name)

  // Set size labels
  g.selectAll('.set-size')
    .data(sets)
    .enter()
    .append('text')
    .attr('class', 'set-size')
    .attr('x', width * 0.25 + 5)
    .attr('y', d => setsY(d.name) + setsY.bandwidth() / 2)
    .attr('dominant-baseline', 'middle')
    .attr('font-size', '10px')
    .attr('fill', 'rgb(var(--v-theme-on-surface-variant))')
    .text(d => d.size)

  // 2. Draw intersection size bars (vertical bars on top)
  g.selectAll('.intersection-bar')
    .data(intersections)
    .enter()
    .append('rect')
    .attr('class', 'intersection-bar')
    .attr('x', (d, i) => intersectionsX(i))
    .attr('y', d => intersectionScale(d.size))
    .attr('width', Math.max(intersectionsX.bandwidth(), 0)) // Ensure non-negative width
    .attr('height', d => Math.max(height * 0.6 - intersectionScale(d.size), 0)) // Ensure non-negative height
    .attr('fill', '#10B981')
    .attr('opacity', 0.8)
    .style('cursor', 'pointer')
    .on('click', (event, d) => {
      selectedIntersection.value = d
      window.logService.info('Selected intersection:', d)
    })
    .on('mouseover', function () {
      // Highlight this bar
      d3.select(this).attr('opacity', 1)

      // Show tooltip or highlight effect
      d3.select(this).attr('stroke', 'rgb(var(--v-theme-on-surface))').attr('stroke-width', 2)
    })
    .on('mouseout', function () {
      // Reset bar appearance
      d3.select(this).attr('opacity', 0.8).attr('stroke', 'none')
    })

  // Intersection size labels
  g.selectAll('.intersection-size')
    .data(intersections)
    .enter()
    .append('text')
    .attr('class', 'intersection-size')
    .attr('x', (d, i) => intersectionsX(i) + intersectionsX.bandwidth() / 2)
    .attr('y', d => intersectionScale(d.size) - 5)
    .attr('text-anchor', 'middle')
    .attr('font-size', '10px')
    .attr('fill', 'rgb(var(--v-theme-on-surface))')
    .text(d => d.size)

  // 3. Draw intersection matrix (dots and lines)
  intersections.forEach((intersection, i) => {
    const x = intersectionsX(i) + intersectionsX.bandwidth() / 2

    // Draw vertical line connecting all dots for this intersection
    const connectedSets = intersection.sets
    if (connectedSets.length > 1) {
      const minY = Math.min(...connectedSets.map(setName => setsY(setName) + setsY.bandwidth() / 2))
      const maxY = Math.max(...connectedSets.map(setName => setsY(setName) + setsY.bandwidth() / 2))

      g.append('line')
        .attr('x1', x)
        .attr('y1', minY)
        .attr('x2', x)
        .attr('y2', maxY)
        .attr('stroke', 'rgb(var(--v-theme-on-surface))')
        .attr('stroke-width', 2)
    }

    // Draw dots for each set
    sets.forEach(set => {
      const y = setsY(set.name) + setsY.bandwidth() / 2
      const isInIntersection = intersection.sets.includes(set.name)

      g.append('circle')
        .attr('cx', x)
        .attr('cy', y)
        .attr('r', 4)
        .attr(
          'fill',
          isInIntersection
            ? 'rgb(var(--v-theme-on-surface))'
            : 'rgb(var(--v-theme-surface-variant))'
        )
        .attr('stroke', 'rgb(var(--v-theme-on-surface))')
        .attr('stroke-width', 1)
        .style('cursor', 'pointer')
        .on('mouseover', function () {
          d3.select(this).attr('r', 6)
        })
        .on('mouseout', function () {
          d3.select(this).attr('r', 4)
        })
        .on('click', function () {
          selectedIntersection.value = intersection
          window.logService.info('Selected intersection via dot:', intersection)
        })
    })
  })
}

// Resize observer to handle container size changes
let resizeObserver = null

// Initialize
onMounted(async () => {
  await loadAvailableSources()
  // Trigger initial load after sources are set
  if (selectedSources.value.length > 0) {
    loadData()
  }

  // Add resize observer to re-render when container size changes
  if (upsetContainer.value) {
    resizeObserver = new window.ResizeObserver(() => {
      if (data.value && upsetContainer.value) {
        // Debounce the render to avoid too many re-renders
        setTimeout(() => {
          renderUpSetPlot()
        }, 150)
      }
    })
    resizeObserver.observe(upsetContainer.value)
  }
})

// Cleanup on unmount
onUnmounted(() => {
  if (resizeObserver && upsetContainer.value) {
    resizeObserver.unobserve(upsetContainer.value)
    resizeObserver.disconnect()
  }
})
</script>

<style scoped>
.upset-chart-container {
  width: 100%;
}

.upset-plot {
  border: 1px solid rgb(var(--v-theme-outline-variant));
  border-radius: 4px;
  background: rgb(var(--v-theme-surface));
  overflow: hidden;
}

.upset-plot svg {
  font-family: 'Roboto', sans-serif;
}

/* Source selection styles */
.source-selection-container {
  background: rgb(var(--v-theme-surface-variant));
  border-radius: 8px;
  padding: 16px;
  border: 1px solid rgb(var(--v-theme-outline-variant));
}

.source-chips {
  min-height: 40px;
  display: flex;
  flex-wrap: wrap;
  align-items: center;
  gap: 4px;
}

.source-chips .v-chip {
  font-weight: 500;
}

.source-chips .v-chip--variant-outlined {
  border-style: dashed;
  color: rgb(var(--v-theme-primary));
}

/* Empty state */
.empty-state {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  min-height: 300px;
  padding: 48px 24px;
  text-align: center;
}

/* Responsive adjustments */
@media (max-width: 600px) {
  .intersections-container {
    min-height: 200px;
    padding: 8px;
  }

  .intersection-item {
    padding: 8px;
  }

  .intersection-header {
    gap: 8px;
  }

  .intersection-count {
    font-size: 12px;
  }
}
</style>
