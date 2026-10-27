<template>
  <Card class="w-full">
    <CardHeader class="flex flex-row flex-wrap items-center gap-2 space-y-0 pb-2">
      <div class="flex min-w-60 flex-1 items-center gap-2">
        <ChartScatter class="size-5 shrink-0" aria-hidden="true" />
        <CardTitle tag="h2" class="text-lg font-semibold">Gene Source Overlaps</CardTitle>
        <TooltipProvider>
          <Tooltip>
            <TooltipTrigger as-child>
              <button
                type="button"
                aria-label="About this chart"
                class="inline-flex size-6 shrink-0 items-center justify-center rounded-sm text-muted-foreground hover:text-foreground focus-visible:ring-2 focus-visible:ring-ring focus-visible:outline-none"
              >
                <CircleHelp class="size-4" aria-hidden="true" />
              </button>
            </TooltipTrigger>
            <TooltipContent side="bottom" class="max-w-xs">
              <span
                >UpSet plot showing intersections between gene data sources. Click bars or dots to
                see the gene count of each intersection.</span
              >
            </TooltipContent>
          </Tooltip>
        </TooltipProvider>
      </div>
      <!-- Always rendered so the header keeps its height when data arrives (#324) -->
      <Badge variant="outline" class="tabular-nums" :class="{ invisible: !data }">
        {{ (data?.total_unique_genes ?? totalGenes).toLocaleString() }}/{{
          totalGenes.toLocaleString()
        }}
        genes
      </Badge>
    </CardHeader>

    <CardContent>
      <!-- Provider for the SourceLabel tooltips (also when rendered outside App) -->
      <TooltipProvider>
        <DataState
          :loading="loading && !data"
          :error="error"
          :empty="!data"
          error-title="Could not load source overlaps"
          empty-message="No source overlap data for the selected tiers."
          @retry="reload"
        >
          <template #loading><ChartSkeleton /></template>

          <div v-if="data" class="relative">
            <!-- Loading overlay for data updates -->
            <div
              v-if="loading"
              class="absolute inset-0 z-10 flex items-center justify-center bg-background/80"
              role="status"
            >
              <LoaderCircle class="size-8 text-muted-foreground motion-safe:animate-spin" />
              <span class="sr-only">Updating overlaps…</span>
            </div>

            <!-- Summary stats -->
            <dl class="mb-4 grid grid-cols-2 gap-4 text-center sm:grid-cols-4">
              <div v-for="stat in summaryStats" :key="stat.label" class="flex flex-col-reverse">
                <dt class="text-xs text-muted-foreground">{{ stat.label }}</dt>
                <dd class="text-lg font-semibold tabular-nums text-foreground">
                  {{ stat.value.toLocaleString() }}
                </dd>
              </div>
            </dl>

            <Separator class="mb-4" />

            <!-- Source selection -->
            <div class="mb-4 flex flex-wrap items-center gap-2 rounded-md bg-muted/50 p-3">
              <span class="inline-flex items-center gap-2 text-sm font-medium">
                <Filter class="size-4" aria-hidden="true" />
                Selected sources ({{ selectedSources.length }}):
              </span>
              <span
                v-for="source in selectedSources"
                :key="source"
                class="inline-flex items-center gap-0.5 rounded-md border bg-background pl-2 text-xs font-medium"
              >
                <SourceLabel :source="source" />
                <button
                  type="button"
                  :aria-label="`Remove ${sourceDisplayName(source)}`"
                  class="inline-flex size-6 items-center justify-center rounded-md text-muted-foreground hover:bg-muted hover:text-foreground focus-visible:ring-2 focus-visible:ring-ring focus-visible:outline-none"
                  @click="removeSource(source)"
                >
                  <X class="size-3.5" aria-hidden="true" />
                </button>
              </span>
              <Button
                v-if="selectedSources.length < availableSources.length"
                variant="outline"
                size="sm"
                class="h-7"
                @click="selectAllSources"
              >
                <CheckSquare aria-hidden="true" />
                Select all
              </Button>
              <DropdownMenu v-if="availableToAdd.length > 0">
                <DropdownMenuTrigger as-child>
                  <Button variant="outline" size="sm" class="h-7">
                    <Plus aria-hidden="true" />
                    Add source
                  </Button>
                </DropdownMenuTrigger>
                <DropdownMenuContent>
                  <DropdownMenuItem
                    v-for="source in availableToAdd"
                    :key="source"
                    @click="addSource(source)"
                  >
                    <SourceLabel :source="source" />
                  </DropdownMenuItem>
                </DropdownMenuContent>
              </DropdownMenu>
            </div>

            <p v-show="selectedSources.length > 0" class="mb-2 text-xs text-muted-foreground">
              Distinct intersections: each gene is counted once, under exactly the selected sources
              it is found in. Showing the
              {{ Math.min(UPSET_COMBINATION_LIMIT, data.intersections.length) }} largest of
              {{ data.intersections.length }}.
            </p>

            <!-- UpSet Plot Container -->
            <div
              v-show="selectedSources.length > 0"
              ref="upsetContainer"
              class="upset-plot w-full"
            />

            <DataState
              v-if="selectedSources.length === 0"
              empty
              empty-message="No sources selected. Add one or more data sources above to see their overlaps."
            />

            <!-- Selected intersection details -->
            <div v-if="selectedIntersection" class="mt-4 rounded-lg border p-4" aria-live="polite">
              <h3 class="mb-1 text-base font-semibold">
                Selected Intersection: {{ selectedIntersection.name }}
              </h3>
              <p class="text-sm">
                <strong class="tabular-nums">{{
                  selectedIntersection.cardinality.toLocaleString()
                }}</strong>
                genes found only in these sources, among the selected sources
              </p>
            </div>
          </div>
        </DataState>
      </TooltipProvider>
    </CardContent>
  </Card>
</template>

<script setup>
import { ref, computed, onMounted, onUnmounted, nextTick, watch } from 'vue'
import {
  ChartScatter,
  CheckSquare,
  CircleHelp,
  Filter,
  LoaderCircle,
  Plus,
  X
} from 'lucide-vue-next'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { TooltipProvider, Tooltip, TooltipTrigger, TooltipContent } from '@/components/ui/tooltip'
import { Badge } from '@/components/ui/badge'
import {
  DropdownMenu,
  DropdownMenuTrigger,
  DropdownMenuContent,
  DropdownMenuItem
} from '@/components/ui/dropdown-menu'
import { Button } from '@/components/ui/button'
import { DataState, SourceLabel } from '@/components/shared'
import { resolveCssColor, sourceDisplayName } from '@/utils/sources'
import ChartSkeleton from './ChartSkeleton.vue'
import { Separator } from '@/components/ui/separator'
import { statisticsApi } from '@/api/statistics'
import { renderUpSet } from '@upsetjs/bundle'
import { buildUpSetCombinations, UPSET_COMBINATION_LIMIT } from './upsetData'
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
const loading = ref(true) // until the first load settles, so nothing flashes "empty"
const error = ref(null)
const data = ref(null)
const selectedIntersection = ref(null)
const upsetContainer = ref(null)
const selectedSources = ref([])
const availableSources = ref([])
const totalGenes = ref(0)
let resizeObserver = null

// Computed properties
// Counts are defined by the API; this only labels them
const summaryStats = computed(() =>
  data.value
    ? [
        { label: 'Data Sources', value: data.value.sets.length },
        { label: 'Intersections', value: data.value.intersections.length },
        { label: 'In All Sources', value: data.value.overlap_statistics.genes_in_all_sources },
        {
          label: 'Single Source Only',
          value: data.value.overlap_statistics.single_source_combinations
        }
      ]
    : []
)

const availableToAdd = computed(() =>
  availableSources.value.filter(source => !selectedSources.value.includes(source))
)

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
    // A failed source list must not leave a blank card
    error.value = err.message || 'Failed to load the data sources'
    window.logService.error('Error loading available sources:', err)
  }
}

// Load data
const loadData = async () => {
  // Nothing selected: keep the last data so the source chips stay to re-add from
  if (selectedSources.value.length === 0) {
    loading.value = false
    return
  }
  loading.value = true
  error.value = null

  try {
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

const reload = async () => {
  error.value = null
  loading.value = true
  await loadTotalGenes()
  await loadAvailableSources()
  await loadData()
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

  // Narrow screens get the table: the plot's labels collide below this width
  if (containerWidth < 480) {
    const topIntersections = data.value.intersections
      .slice()
      .sort((a, b) => (b.size || 0) - (a.size || 0))
      .slice(0, UPSET_COMBINATION_LIMIT)
    const rows = topIntersections
      .map(
        i =>
          `<tr><td style="padding:6px 8px;border-bottom:1px solid var(--border);font-size:12px;">${(i.sets || []).map(sourceDisplayName).join(' ∩ ')}</td><td style="padding:6px 8px;border-bottom:1px solid var(--border);text-align:right;font-weight:600;font-size:12px;">${i.size || 0}</td></tr>`
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

  if (data.value.intersections.length === 0) {
    upsetContainer.value.innerHTML =
      '<p style="text-align: center; padding: 40px; color: var(--muted-foreground);">No overlaps for the selected sources.</p>'
    return
  }

  const { sets, combinations } = buildUpSetCombinations(
    data.value.intersections.map(i => ({ ...i, sets: (i.sets || []).map(sourceDisplayName) }))
  )
  // The widget draws SVG: hand it the app's font and resolved theme tokens
  const el = upsetContainer.value
  const token = name => resolveCssColor(`var(${name})`, el)
  const theme = {
    theme: isDark.value ? 'dark' : 'light',
    fontFamily: window.getComputedStyle(el).fontFamily,
    fontSizes: { setLabel: '13px', axisTick: '11px', barLabel: '11px', chartLabel: '12px' },
    color: token('--foreground'),
    textColor: token('--foreground'),
    selectionColor: token('--primary'),
    hoverHintColor: token('--muted'),
    alternatingBackgroundColor: token('--muted'),
    notMemberColor: token('--input'),
    setName: 'Genes per source',
    combinationName: 'Genes per intersection',
    exportButtons: false
  }

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
        ...theme,
        selection: selectedIntersection.value,
        onClick: set => {
          // A set row's size counts every gene in that source, not an exclusive intersection
          if (set?.type === 'set') return
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
      error.value = `The chart could not be drawn: ${err.message}`
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

// Re-render on resize; the container appears and disappears with the data/error states
onMounted(() => {
  resizeObserver =
    typeof window.ResizeObserver === 'function'
      ? new window.ResizeObserver(() => renderUpSetPlot())
      : null
  reload()
})

watch(upsetContainer, (el, old) => {
  if (old) resizeObserver?.unobserve(old)
  if (el) resizeObserver?.observe(el)
})

onUnmounted(() => {
  resizeObserver?.disconnect()
})
</script>

<style scoped>
.upset-plot {
  overflow-x: auto;
  overflow-y: hidden;
}
</style>
