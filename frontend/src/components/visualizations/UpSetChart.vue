<template>
  <v-card class="upset-chart-container">
    <v-card-title class="d-flex align-center">
      <ChartScatter class="size-5 me-2" />
      Gene Source Overlaps
      <v-tooltip location="bottom">
        <template #activator="{ props: tooltipProps }">
          <CircleHelp v-bind="tooltipProps" class="size-4 me-2 text-medium-emphasis" />
        </template>
        <span
          >UpSet plot showing intersections between gene data sources. Click bars or dots to see
          genes in each intersection.</span
        >
      </v-tooltip>
      <v-spacer />
      <v-tooltip v-if="data" location="bottom" max-width="300">
        <template #activator="{ props: tooltipProps }">
          <v-chip v-bind="tooltipProps" variant="outlined" size="small" class="me-2">
            {{ data.total_unique_genes.toLocaleString() }} genes
          </v-chip>
        </template>
        <div class="pa-2">
          <strong>Genes with evidence:</strong> {{ data.total_unique_genes.toLocaleString() }} genes
          with evidence score > 0 <br />These genes have kidney disease associations from at least
          one data source
        </div>
      </v-tooltip>
      <v-tooltip location="bottom">
        <template #activator="{ props: tooltipProps }">
          <v-checkbox
            v-model="showInsufficientEvidence"
            v-bind="tooltipProps"
            label="Show insufficient evidence"
            density="compact"
            hide-details
            class="me-2"
          />
        </template>
        <span>Include genes with percentage_score = 0 (no meaningful evidence)</span>
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
      <!-- Loading state (only on initial load) -->
      <div v-if="loading && !data" class="d-flex justify-center align-center" style="height: 400px">
        <v-progress-circular indeterminate size="64" />
      </div>

      <!-- Error state -->
      <v-alert v-else-if="error" type="error" variant="outlined" class="mb-4">
        {{ error }}
      </v-alert>

      <!-- UpSet visualization -->
      <div v-else-if="data">
        <!-- Loading overlay for data updates -->
        <v-overlay :model-value="loading" contained persistent class="align-center justify-center">
          <v-progress-circular indeterminate size="64" />
        </v-overlay>
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
              <Filter class="size-4 me-2" />
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

            <!-- Select All chip -->
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
              <template #activator="{ props: menuProps }">
                <v-chip
                  v-bind="menuProps"
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

        <!-- UpSet Plot Container -->
        <div
          v-show="selectedSources.length > 0"
          ref="upsetContainer"
          class="upset-plot"
          style="width: 100%"
        ></div>

        <!-- Empty state when no sources selected -->
        <div v-show="selectedSources.length === 0" class="empty-state">
          <ChartScatter class="size-16 text-muted-foreground" />
          <h3 class="text-h6 mt-4 mb-2 text-grey-lighten-1">No Sources Selected</h3>
          <p class="text-body-2 text-grey">
            Select one or more data sources above to view the UpSet plot visualization.
          </p>
        </div>

        <!-- Selected intersection details -->
        <v-card v-if="selectedIntersection" variant="outlined" class="mt-4">
          <v-card-title class="text-h6">
            Selected Intersection: {{ selectedIntersection.name }}
          </v-card-title>
          <v-card-text>
            <div class="mb-2">
              <strong>{{ selectedIntersection.cardinality }}</strong> genes in this intersection
            </div>
            <v-chip-group v-if="selectedIntersection.elems.length <= 20">
              <v-chip
                v-for="elem in selectedIntersection.elems"
                :key="elem.name"
                size="small"
                variant="outlined"
              >
                {{ elem.name }}
              </v-chip>
            </v-chip-group>
            <div v-else>
              <div class="mb-2">First 20 genes:</div>
              <v-chip-group>
                <v-chip
                  v-for="elem in selectedIntersection.elems.slice(0, 20)"
                  :key="elem.name"
                  size="small"
                  variant="outlined"
                >
                  {{ elem.name }}
                </v-chip>
              </v-chip-group>
              <div class="text-caption mt-2">
                ... and {{ selectedIntersection.elems.length - 20 }} more genes
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
import { ChartScatter, CircleHelp, Filter } from 'lucide-vue-next'
import { statisticsApi } from '@/api/statistics'
import { extractCombinations, renderUpSet } from '@upsetjs/bundle'

// Props
const props = defineProps({
  selectedTiers: {
    type: Array,
    default: () => []
  }
})

// Reactive data
const loading = ref(false)
const error = ref(null)
const data = ref(null)
const selectedIntersection = ref(null)
const upsetContainer = ref(null)
const selectedSources = ref([])
const availableSources = ref([])
const showInsufficientEvidence = ref(false) // Default: hide genes with score = 0
let resizeObserver = null

// Computed properties
const availableToAdd = computed(() =>
  availableSources.value.filter(source => !selectedSources.value.includes(source))
)

// Transform API data to UpSet.js format
const transformToUpSetFormat = apiData => {
  if (!apiData || !apiData.intersections) return { elements: [], sets: [] }

  // Build elements array: each element is a gene with its sets
  const geneToSetsMap = new Map()

  // Process each intersection
  apiData.intersections.forEach(intersection => {
    const sourceSets = intersection.sets
    const genes = intersection.genes || []

    // For each gene in this intersection, record which sets it belongs to
    genes.forEach(geneName => {
      if (!geneToSetsMap.has(geneName)) {
        geneToSetsMap.set(geneName, new Set())
      }
      // Add all sources from this intersection
      sourceSets.forEach(source => {
        geneToSetsMap.get(geneName).add(source)
      })
    })
  })

  // Convert map to elements array
  const elements = Array.from(geneToSetsMap.entries()).map(([geneName, sourceSets]) => ({
    name: geneName,
    sets: Array.from(sourceSets)
  }))

  return { elements }
}

// Load available sources
const loadAvailableSources = async () => {
  try {
    const response = await statisticsApi.getSourceOverlaps(
      null,
      props.selectedTiers,
      !showInsufficientEvidence.value // Invert: checkbox OFF = hide (true), checkbox ON = show (false)
    )
    if (response.data?.sets) {
      // Sort by cardinality descending (largest first) to match UpSet.js default
      const sources = response.data.sets
        .sort((a, b) => b.cardinality - a.cardinality)
        .map(set => set.name)
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
    if (selectedSources.value.length === 0) {
      data.value = null
      loading.value = false
      return
    }

    window.logService.info('Calling API with sources', {
      sources: selectedSources.value,
      selectedTiers: props.selectedTiers,
      hideZeroScores: !showInsufficientEvidence.value
    })

    const response = await statisticsApi.getSourceOverlaps(
      selectedSources.value,
      props.selectedTiers,
      !showInsufficientEvidence.value // Invert: checkbox OFF = hide (true), checkbox ON = show (false)
    )
    window.logService.info('API response received', { data: response.data })
    data.value = response.data

    // Render UpSet plot after data is loaded
    await nextTick()
    await nextTick() // Extra tick to ensure DOM is fully updated

    if (!upsetContainer.value) {
      window.logService.error('Container ref is null after data load')
    }

    renderUpSetPlot()
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
    window.logService.info('Adding source', { source })
    selectedSources.value = [...selectedSources.value, source]
  }
}

const removeSource = source => {
  const index = selectedSources.value.indexOf(source)
  if (index > -1) {
    window.logService.info('Removing source', { source })
    selectedSources.value = selectedSources.value.filter(s => s !== source)
  }
}

const selectAllSources = () => {
  window.logService.info('Selecting all sources')
  selectedSources.value = [...availableSources.value]
}

// Watch for changes in selectedSources and reload data
watch(
  selectedSources,
  async (newSources, oldSources) => {
    // Only reload if we have old sources (not initial load) and the count changed
    if (oldSources && oldSources.length > 0 && newSources.length !== oldSources.length) {
      window.logService.info('Source count changed', {
        from: oldSources.length,
        to: newSources.length,
        removed: oldSources.filter(s => !newSources.includes(s)),
        added: newSources.filter(s => !oldSources.includes(s))
      })
      await loadData()
    }
  },
  { immediate: false }
)

// Watch for tier changes and reload data
watch(
  () => props.selectedTiers,
  async (newTiers, oldTiers) => {
    // Deep comparison of arrays
    const tiersChanged =
      JSON.stringify(newTiers?.slice().sort()) !== JSON.stringify(oldTiers?.slice().sort())
    if (tiersChanged) {
      window.logService.info('Tier filter changed', { from: oldTiers, to: newTiers })
      await loadAvailableSources()
      await loadData()
    }
  },
  { deep: true }
)

// Watch for insufficient evidence toggle changes and reload data
watch(
  () => showInsufficientEvidence.value,
  async () => {
    window.logService.info('Insufficient evidence toggle changed', {
      showInsufficientEvidence: showInsufficientEvidence.value
    })
    await loadAvailableSources()
    await loadData()
  }
)

// Render UpSet plot using @upsetjs/bundle
const renderUpSetPlot = () => {
  window.logService.info('renderUpSetPlot called', {
    hasData: !!data.value,
    hasContainer: !!upsetContainer.value,
    dataKeys: data.value ? Object.keys(data.value) : []
  })

  if (!data.value || !upsetContainer.value) {
    window.logService.warn('Skipping render - missing requirements', {
      hasData: !!data.value,
      hasContainer: !!upsetContainer.value
    })
    return
  }

  // Clear any existing plot
  upsetContainer.value.innerHTML = ''

  // Get container dimensions
  const containerWidth = upsetContainer.value.clientWidth

  // Don't render if container is too small
  if (containerWidth < 400) {
    upsetContainer.value.innerHTML = `
      <div style="text-align: center; padding: 40px;">
        <p>📱 Screen too narrow</p>
        <p>Please rotate to landscape or use a larger screen</p>
      </div>
    `
    window.logService.warn('Container too small for UpSet plot', {
      containerWidth,
      minimumWidth: 400
    })
    return
  }

  // Calculate height based on number of sets
  const baseHeight = 400
  const heightPerSet = 30
  const calculatedHeight = Math.max(baseHeight, data.value.sets.length * heightPerSet + 200)

  // Transform data to UpSet.js format
  const { elements } = transformToUpSetFormat(data.value)

  if (elements.length === 0) {
    upsetContainer.value.innerHTML =
      '<p style="text-align: center; padding: 40px;">No data to display</p>'
    return
  }

  // Extract combinations from elements with sorting options
  const { sets, combinations } = extractCombinations(elements, {
    setOrder: 'cardinality:desc', // Sort sets by size (largest first)
    combinationOrder: 'cardinality:desc' // Sort combinations by size (largest first)
  })

  window.logService.info('Rendering UpSet plot', {
    setsCount: sets.length,
    combinationsCount: combinations.length,
    width: containerWidth,
    height: calculatedHeight
  })

  // Render function with current selection
  const render = () => {
    try {
      const props = {
        sets,
        combinations,
        width: containerWidth,
        height: calculatedHeight,
        selection: selectedIntersection.value,
        onClick: set => {
          // Toggle selection
          if (selectedIntersection.value === set) {
            selectedIntersection.value = null
          } else {
            selectedIntersection.value = set
          }
          render() // Re-render with new selection
        }
      }
      renderUpSet(upsetContainer.value, props)
      window.logService.info('UpSet plot rendered successfully')
    } catch (err) {
      window.logService.error('Error rendering UpSet plot', err)
      upsetContainer.value.innerHTML = `<p style="text-align: center; padding: 40px; color: red;">Error rendering chart: ${err.message}</p>`
    }
  }

  render()
}

// Setup ResizeObserver
onMounted(async () => {
  await loadAvailableSources()
  await loadData()

  // Set up ResizeObserver to handle window resizing
  if (upsetContainer.value) {
    // eslint-disable-next-line no-undef
    resizeObserver = new ResizeObserver(() => {
      // Re-render on resize
      renderUpSetPlot()
    })
    resizeObserver.observe(upsetContainer.value)
  }
})

// Cleanup
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
  overflow-x: auto;
  overflow-y: hidden;
}

.source-selection-container {
  background-color: rgb(var(--v-theme-surface));
  border-radius: 4px;
  padding: 12px;
}

.empty-state {
  text-align: center;
  padding: 60px 20px;
}
</style>
