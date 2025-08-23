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
      <v-chip v-if="data" variant="outlined" size="small" class="me-2">
        {{ data.total_unique_genes }} total genes
      </v-chip>
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

        <!-- UpSet Plot -->
        <div ref="upsetContainer" class="upset-plot" style="min-height: 500px; width: 100%"></div>

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
import { ref, onMounted, nextTick } from 'vue'
import { statisticsApi } from '@/api/statistics'
import * as d3 from 'd3'

// Reactive data
const loading = ref(false)
const error = ref(null)
const data = ref(null)
const selectedIntersection = ref(null)
const upsetContainer = ref(null)

// Load data
const loadData = async () => {
  loading.value = true
  error.value = null

  try {
    const response = await statisticsApi.getSourceOverlaps()
    data.value = response.data

    // Render UpSet plot after data is loaded
    await nextTick()
    // Add a small delay to ensure DOM is fully rendered
    setTimeout(() => {
      renderUpSetPlot()
    }, 100)
  } catch (err) {
    error.value = err.message || 'Failed to load source overlap data'
    console.error('Error loading source overlaps:', err)
  } finally {
    loading.value = false
  }
}

const refreshData = () => {
  loadData()
}

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
  const maxSetSize = Math.max(...sets.map(d => d.size))
  const maxIntersectionSize = Math.max(...intersections.map(d => d.size))

  // Horizontal scale for set sizes (left bars)
  const setScale = d3
    .scaleLinear()
    .domain([0, maxSetSize])
    .range([0, width * 0.25])

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
    .range([width * 0.3, width])
    .padding(0.1)

  // 1. Draw set size bars (horizontal bars on the left)
  g.selectAll('.set-bar')
    .data(sets)
    .enter()
    .append('rect')
    .attr('class', 'set-bar')
    .attr('x', width * 0.25 - setScale.range()[1])
    .attr('y', d => setsY(d.name))
    .attr('width', d => setScale(d.size))
    .attr('height', setsY.bandwidth())
    .attr('fill', '#0EA5E9')
    .attr('opacity', 0.8)
    .style('cursor', 'pointer')
    .on('mouseover', function () {
      d3.select(this).attr('opacity', 1).attr('stroke', 'rgb(var(--v-theme-on-surface))').attr('stroke-width', 1)
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
    .attr('width', intersectionsX.bandwidth())
    .attr('height', d => height * 0.6 - intersectionScale(d.size))
    .attr('fill', '#10B981')
    .attr('opacity', 0.8)
    .style('cursor', 'pointer')
    .on('click', (event, d) => {
      selectedIntersection.value = d
      console.log('Selected intersection:', d)
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
        .attr('fill', isInIntersection ? 'rgb(var(--v-theme-on-surface))' : 'rgb(var(--v-theme-surface-variant))')
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
          console.log('Selected intersection via dot:', intersection)
        })
    })
  })
}

// Initialize
onMounted(() => {
  loadData()
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
