<template>
  <Card class="w-full">
    <CardHeader class="flex flex-row items-center space-y-0 pb-2">
      <div class="flex items-center flex-1">
        <ChartScatter class="size-5 mr-2" />
        <CardTitle class="text-lg font-semibold">Gene Source Overlaps</CardTitle>
        <TooltipProvider>
          <Tooltip>
            <TooltipTrigger as-child>
              <CircleHelp class="size-4 ml-2 text-muted-foreground cursor-help" />
            </TooltipTrigger>
            <TooltipContent side="bottom">
              <span
                >UpSet plot showing intersections between gene data sources. Click bars or dots to
                see genes in each intersection.</span
              >
            </TooltipContent>
          </Tooltip>
        </TooltipProvider>
      </div>
      <Badge v-if="data" variant="outline">
        {{ data.total_unique_genes.toLocaleString() }}/{{ totalGenes.toLocaleString() }} genes
      </Badge>
    </CardHeader>

    <CardContent>
      <!-- Loading state (only on initial load) -->
      <div v-if="loading && !data" class="flex justify-center items-center" style="height: 400px">
        <div
          class="h-16 w-16 animate-spin rounded-full border-4 border-primary border-t-transparent"
        />
      </div>

      <!-- Error state -->
      <Alert v-else-if="error" variant="destructive" class="mb-4">
        <AlertDescription>{{ error }}</AlertDescription>
      </Alert>

      <!-- UpSet visualization -->
      <div v-else-if="data" class="relative">
        <!-- Loading overlay for data updates -->
        <div
          v-if="loading"
          class="absolute inset-0 z-10 flex items-center justify-center bg-background/80"
        >
          <div
            class="h-16 w-16 animate-spin rounded-full border-4 border-primary border-t-transparent"
          />
        </div>

        <!-- Summary stats -->
        <div class="mb-4">
          <div class="grid grid-cols-2 sm:grid-cols-4 gap-4 text-center">
            <div>
              <div class="text-lg font-semibold text-primary">{{ data.sets.length }}</div>
              <div class="text-xs text-muted-foreground">Data Sources</div>
            </div>
            <div>
              <div class="text-lg font-semibold text-primary">
                {{ data.intersections.length }}
              </div>
              <div class="text-xs text-muted-foreground">Intersections</div>
            </div>
            <div>
              <div class="text-lg font-semibold text-primary">
                {{ data.overlap_statistics.genes_in_all_sources }}
              </div>
              <div class="text-xs text-muted-foreground">In All Sources</div>
            </div>
            <div>
              <div class="text-lg font-semibold text-primary">
                {{ data.overlap_statistics.single_source_combinations }}
              </div>
              <div class="text-xs text-muted-foreground">Single Source Only</div>
            </div>
          </div>
        </div>

        <Separator class="mb-4" />

        <!-- Source Selection Interface -->
        <div class="source-selection-container mb-4">
          <div class="flex items-center flex-wrap gap-2">
            <div class="flex items-center">
              <Filter class="size-4 mr-2" />
              <span class="text-sm font-medium"
                >Selected Sources ({{ selectedSources.length }}):</span
              >
            </div>

            <!-- Source chips inline -->
            <Badge v-for="source in selectedSources" :key="source" class="gap-1 m-1">
              {{ source }}
              <button
                class="ml-1 rounded-full hover:bg-destructive/20"
                @click="removeSource(source)"
              >
                <X :size="12" />
              </button>
            </Badge>

            <!-- Select All chip -->
            <Badge
              v-if="selectedSources.length < availableSources.length"
              variant="outline"
              class="cursor-pointer m-1"
              @click="selectAllSources"
            >
              <CheckSquare :size="14" class="mr-1" />
              Select All
            </Badge>

            <!-- Add source menu -->
            <DropdownMenu v-if="availableToAdd.length > 0">
              <DropdownMenuTrigger as-child>
                <Badge variant="outline" class="cursor-pointer m-1">
                  <Plus :size="14" class="mr-1" /> Add Source
                </Badge>
              </DropdownMenuTrigger>
              <DropdownMenuContent>
                <DropdownMenuItem
                  v-for="source in availableToAdd"
                  :key="source"
                  @click="addSource(source)"
                >
                  {{ source }}
                </DropdownMenuItem>
              </DropdownMenuContent>
            </DropdownMenu>
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
          <h3 class="text-lg font-semibold mt-4 mb-2 text-muted-foreground">No Sources Selected</h3>
          <p class="text-sm text-muted-foreground">
            Select one or more data sources above to view the UpSet plot visualization.
          </p>
        </div>

        <!-- Selected intersection details -->
        <Card v-if="selectedIntersection" variant="outline" class="mt-4 border">
          <CardHeader class="pb-2">
            <CardTitle class="text-lg font-semibold">
              Selected Intersection: {{ selectedIntersection.name }}
            </CardTitle>
          </CardHeader>
          <CardContent>
            <div class="mb-2">
              <strong>{{ selectedIntersection.cardinality }}</strong> genes in this intersection
            </div>
            <div v-if="selectedIntersection.elems.length <= 20" class="flex flex-wrap gap-1">
              <Badge v-for="elem in selectedIntersection.elems" :key="elem.name" variant="outline">
                {{ elem.name }}
              </Badge>
            </div>
            <div v-else>
              <div class="mb-2">First 20 genes:</div>
              <div class="flex flex-wrap gap-1">
                <Badge
                  v-for="elem in selectedIntersection.elems.slice(0, 20)"
                  :key="elem.name"
                  variant="outline"
                >
                  {{ elem.name }}
                </Badge>
              </div>
              <div class="text-xs text-muted-foreground mt-2">
                ... and {{ selectedIntersection.elems.length - 20 }} more genes
              </div>
            </div>
          </CardContent>
        </Card>
      </div>
    </CardContent>
  </Card>
</template>

<script setup>
import { ref, computed, onMounted, onUnmounted, nextTick, watch } from 'vue'
import { ChartScatter, CircleHelp, Filter, X, Plus, CheckSquare } from 'lucide-vue-next'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { TooltipProvider, Tooltip, TooltipTrigger, TooltipContent } from '@/components/ui/tooltip'
import { Badge } from '@/components/ui/badge'
import {
  DropdownMenu,
  DropdownMenuTrigger,
  DropdownMenuContent,
  DropdownMenuItem
} from '@/components/ui/dropdown-menu'
import { Alert, AlertDescription } from '@/components/ui/alert'
import { Separator } from '@/components/ui/separator'
import { statisticsApi } from '@/api/statistics'
import { extractCombinations, renderUpSet } from '@upsetjs/bundle'
import { useAppTheme } from '@/composables/useAppTheme'

// Props
const props = defineProps({
  selectedTiers: {
    type: Array,
    default: () => []
  },
  showInsufficientEvidence: {
    type: Boolean,
    default: false
  }
})

const { isDark } = useAppTheme()

// Reactive data
const loading = ref(false)
const error = ref(null)
const data = ref(null)
const selectedIntersection = ref(null)
const upsetContainer = ref(null)
const selectedSources = ref([])
const availableSources = ref([])
const totalGenes = ref(0)
let resizeObserver = null

// Computed properties
const availableToAdd = computed(() =>
  availableSources.value.filter(source => !selectedSources.value.includes(source))
)

// Transform API data to UpSet.js format
const transformToUpSetFormat = apiData => {
  if (!apiData || !apiData.intersections) return { elements: [], sets: [] }

  // API returns intersections with {sets, size} but no gene lists.
  // Generate synthetic elements: for each intersection, create `size`
  // placeholder elements that belong to exactly those sets.
  const elements = []
  let elementIndex = 0

  apiData.intersections.forEach(intersection => {
    const sourceSets = intersection.sets
    const count = intersection.size || 0

    for (let i = 0; i < count; i++) {
      elements.push({
        name: `gene_${elementIndex++}`,
        sets: [...sourceSets]
      })
    }
  })

  return { elements }
}

// Load available sources
const loadAvailableSources = async () => {
  try {
    const response = await statisticsApi.getSourceOverlaps(
      null,
      props.selectedTiers,
      !props.showInsufficientEvidence
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
      hideZeroScores: !props.showInsufficientEvidence
    })

    const response = await statisticsApi.getSourceOverlaps(
      selectedSources.value,
      props.selectedTiers,
      !props.showInsufficientEvidence
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
  () => props.showInsufficientEvidence,
  async () => {
    window.logService.info('Insufficient evidence toggle changed', {
      showInsufficientEvidence: props.showInsufficientEvidence
    })
    await loadAvailableSources()
    await loadData()
  }
)

// Watch for theme changes and re-render
watch(
  () => isDark.value,
  () => {
    if (data.value && upsetContainer.value) {
      nextTick(renderUpSetPlot)
    }
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

  // Show simplified table view on narrow screens instead of blocking
  if (containerWidth < 280) {
    const topIntersections = data.value.intersections
      .slice()
      .sort((a, b) => (b.size || 0) - (a.size || 0))
      .slice(0, 10)
    const rows = topIntersections
      .map(
        i =>
          `<tr><td style="padding:6px 8px;border-bottom:1px solid var(--border);font-size:12px;">${(i.sets || []).join(' ∩ ')}</td><td style="padding:6px 8px;border-bottom:1px solid var(--border);text-align:right;font-weight:600;font-size:12px;">${i.size || 0}</td></tr>`
      )
      .join('')
    upsetContainer.value.innerHTML = `
      <div style="padding:12px 0;">
        <p style="font-size:13px;font-weight:600;margin-bottom:8px;color:var(--foreground);">Top Source Overlaps</p>
        <p style="font-size:11px;color:var(--muted-foreground);margin-bottom:12px;">Rotate device for full UpSet plot</p>
        <table style="width:100%;border-collapse:collapse;color:var(--foreground);">
          <thead><tr>
            <th style="padding:6px 8px;text-align:left;font-size:11px;font-weight:500;color:var(--muted-foreground);border-bottom:2px solid var(--border);">Sources</th>
            <th style="padding:6px 8px;text-align:right;font-size:11px;font-weight:500;color:var(--muted-foreground);border-bottom:2px solid var(--border);">Genes</th>
          </tr></thead>
          <tbody>${rows}</tbody>
        </table>
      </div>
    `
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
        theme: isDark.value ? 'dark' : 'light',
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

// Load total gene count (baseline for x/y display)
const loadTotalGenes = async () => {
  try {
    const response = await statisticsApi.getSourceOverlaps(null, [], false)
    totalGenes.value = response.data?.total_unique_genes || 0
  } catch {
    totalGenes.value = 0
  }
}

// Setup ResizeObserver
onMounted(async () => {
  await loadTotalGenes()
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
.upset-plot {
  overflow-x: auto;
  overflow-y: hidden;
}

.source-selection-container {
  background-color: hsl(var(--card));
  border-radius: 4px;
  padding: 12px;
}

.empty-state {
  text-align: center;
  padding: 60px 20px;
}
</style>
