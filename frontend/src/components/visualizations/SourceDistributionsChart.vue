<template>
  <Card class="source-distributions-container w-full">
    <CardHeader class="flex flex-row flex-wrap items-center gap-2 space-y-0 pb-2">
      <ChartBar class="size-5" aria-hidden="true" />
      <CardTitle tag="h2" class="text-lg font-semibold">Source Distributions</CardTitle>
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
          <TooltipContent side="bottom">
            <span>{{
              selectedSource
                ? getSourceDescription(selectedSource)
                : 'Select a source to see distribution'
            }}</span>
          </TooltipContent>
        </Tooltip>
      </TooltipProvider>
      <div class="flex-1" />
      <!-- Always rendered (disabled until loaded) so the header does not jump -->
      <Select v-model="selectedSource" :disabled="sourceOptions.length === 0">
        <SelectTrigger aria-label="Data source" class="h-8 w-full sm:w-[200px]">
          <SelectValue placeholder="Select source" />
        </SelectTrigger>
        <SelectContent>
          <SelectItem v-for="option in sourceOptions" :key="option.value" :value="option.value">
            {{ option.title }}
          </SelectItem>
        </SelectContent>
      </Select>
    </CardHeader>

    <CardContent>
      <DataState
        :loading="loading && !data"
        :error="error"
        :empty="!data || Object.keys(data).length === 0"
        error-title="Could not load source distributions"
        empty-message="No distribution data for the selected tiers."
        @retry="loadData"
      >
        <template #loading><ChartSkeleton /></template>

        <div
          v-if="selectedSource && sourceData"
          :class="['transition-opacity', loading && 'opacity-60']"
          :aria-busy="loading"
        >
          <!-- A shared link's source with no genes in these tiers: say so, don't swap silently -->
          <p
            v-if="sourceParam && sourceParam !== selectedSource"
            class="mb-3 text-center text-xs text-muted-foreground"
            role="status"
          >
            {{ sourceDisplayName(sourceParam) }} has no genes in the selected tiers; showing
            {{ sourceDisplayName(selectedSource) }}.
          </p>
          <!-- Source metadata -->
          <!-- Fixed two columns, Genes always first: switching sources never moves the stats -->
          <dl class="mx-auto mb-4 grid min-h-15 max-w-md grid-cols-2 items-end gap-x-6 text-center">
            <div v-for="(value, key) in displayedMetadata" :key="key" class="flex flex-col-reverse">
              <dt class="text-xs text-muted-foreground">{{ formatMetadataLabel(key) }}</dt>
              <dd class="text-lg font-semibold tabular-nums text-foreground">
                {{ formatMetadataValue(value) }}
              </dd>
            </div>
          </dl>

          <DataState
            :empty="!hasDistributionData"
            empty-message="No distribution data available for this source."
          >
            <!-- Bars for every source: classifications are multi-label (a gene can hold
                 several), so they cannot be parts of a whole as a donut would claim -->
            <D3BarChart
              :data="d3ChartData"
              :x-axis-label="getXAxisLabel(selectedSource)"
              y-axis-label="Genes"
              :bar-color="getSourceConfig(selectedSource).chartColor"
            />
            <!-- Always rendered at a fixed height so switching sources never shifts the page -->
            <p class="mt-2 min-h-8 text-center text-xs text-muted-foreground">
              <template v-if="visualizationType === 'classification_donut'">
                Genes can hold several classifications, so bars may sum to more than the gene total.
              </template>
            </p>
          </DataState>
        </div>
      </DataState>
    </CardContent>
  </Card>
</template>

<script setup>
import { ref, computed, onMounted, watch } from 'vue'
import { ChartBar, CircleHelp } from 'lucide-vue-next'
import { statisticsApi } from '@/api/statistics'
import { useQueryParam } from '@/composables/useQueryParam'
import D3BarChart from './D3BarChart.vue'

import { Card, CardHeader, CardTitle, CardContent } from '@/components/ui/card'
import { TooltipProvider, Tooltip, TooltipTrigger, TooltipContent } from '@/components/ui/tooltip'
import {
  Select,
  SelectTrigger,
  SelectValue,
  SelectContent,
  SelectItem
} from '@/components/ui/select'
import { DataState } from '@/components/shared'
import { getClassificationConfig } from '@/utils/evidenceTiers'
import { getSourceConfig, sourceDisplayName } from '@/utils/sources'
import ChartSkeleton from './ChartSkeleton.vue'
import { binCounts } from './histogramBins'

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

// Reactive data
const loading = ref(true) // until the first load settles, so nothing flashes "empty"
const error = ref(null)
const data = ref(null)
// Selected source is the ?source= URL parameter; falls back to the first available source
const sourceParam = useQueryParam('source')
const selectedSource = computed({
  get: () => {
    const sources = data.value ? Object.keys(data.value) : []
    return sources.includes(sourceParam.value) ? sourceParam.value : (sources[0] ?? null)
  },
  set: v => (sourceParam.value = v)
})

// Computed properties
const sourceOptions = computed(() => {
  if (!data.value) return []
  return Object.keys(data.value).map(source => ({
    title: sourceDisplayName(source),
    value: source
  }))
})

const sourceMetadata = computed(() => {
  if (!data.value || !selectedSource.value) return {}
  return data.value[selectedSource.value]?.metadata || {}
})

// Metadata shown to users; visualization_type is an internal chart id
const displayedMetadata = computed(() =>
  Object.fromEntries(
    Object.entries(sourceMetadata.value)
      .filter(
        ([key]) => !['visualization_type', 'total_classifications', 'total_ranges'].includes(key)
      )
      .sort(([a], [b]) => (b === 'total_genes') - (a === 'total_genes'))
  )
)

const sourceData = computed(() => {
  if (!data.value || !selectedSource.value) return null
  return data.value[selectedSource.value]
})

const visualizationType = computed(() => {
  return sourceMetadata.value?.visualization_type || 'histogram'
})

const hasDistributionData = computed(() => {
  return sourceData.value?.distribution && sourceData.value.distribution.length > 0
})

// Unified D3 dataset - simple format for both chart types
const d3ChartData = computed(() => {
  if (!sourceData.value?.distribution || !Array.isArray(sourceData.value.distribution)) {
    return []
  }

  const rows = sourceData.value.distribution
    .filter(d => d && d.category !== undefined && d.gene_count !== undefined)
    .map(d => ({ category: String(d.category), gene_count: Number(d.gene_count) }))
  if (visualizationType.value !== 'classification_donut') return binCounts(rows)

  // Classifications: ordinal strength colour and icon, strongest first (not index-based)
  return rows
    .map(d => {
      const c = getClassificationConfig(d.category)
      return { ...d, category: c.label, color: c.color, icon: c.icon, strength: c.strength ?? 0 }
    })
    .sort((a, b) => b.strength - a.strength)
})

// Methods
let loadSeq = 0
const loadData = async () => {
  loading.value = true
  error.value = null
  const request = ++loadSeq // ignore a slower, older response

  try {
    const response = await statisticsApi.getSourceDistributions(
      props.selectedTiers,
      !props.showInsufficientEvidence
    )
    if (request !== loadSeq) return
    data.value = response.data

    if (data.value && Object.keys(data.value).length > 0) {
      const availableSources = Object.keys(data.value)
      window.logService.info('Source distribution data loaded', {
        source: selectedSource.value,
        availableSources: availableSources,
        metadata: data.value[selectedSource.value]?.metadata,
        distributionCount: data.value[selectedSource.value]?.distribution?.length,
        hideZeroScores: !props.showInsufficientEvidence
      })
    }
  } catch (err) {
    error.value = err.message || 'Failed to load source distribution data'
    window.logService.error('Error loading source distributions:', err)
  } finally {
    if (request === loadSeq) loading.value = false
  }
}

const formatMetadataValue = value => (typeof value === 'number' ? value.toLocaleString() : value)

// Plain-language labels; counts of chart categories (total_classifications/ranges) are not shown
const METADATA_LABELS = {
  total_genes: 'Genes',
  max_panels: 'Most panels for one gene',
  max_providers: 'Most providers for one gene',
  max_publications: 'Most publications for one gene'
}
const formatMetadataLabel = key =>
  METADATA_LABELS[key] ?? key.replace(/_/g, ' ').replace(/^\w/, c => c.toUpperCase())

const getSourceDescription = source => {
  const descriptions = {
    PanelApp: 'Shows distribution of genes by number of diagnostic panels they appear in',
    PubTator: 'Shows distribution of genes by number of publications mentioning them',
    DiagnosticPanels:
      'Shows distribution of genes by number of commercial diagnostic providers offering tests',
    ClinGen: 'Shows distribution of genes by ClinGen classification level',
    GenCC: 'Shows distribution of genes by GenCC classification level',
    HPO: 'Shows distribution of genes by number of HPO term associations (bins of unequal width)',
    Literature: 'Shows distribution of genes by number of curated publications'
  }
  return descriptions[source] || `Distribution for ${source} data source`
}

const getXAxisLabel = source => {
  const labels = {
    PanelApp: 'Panels per gene',
    PubTator: 'Publications per gene',
    Literature: 'Curated publications per gene',
    DiagnosticPanels: 'Diagnostic providers per gene',
    ClinGen: 'Classification',
    GenCC: 'Classification',
    HPO: 'HPO terms per gene (unequal bins)'
  }
  return labels[source] || 'Category'
}

// Watch for tier changes
watch(
  () => props.selectedTiers,
  async (newTiers, oldTiers) => {
    // Deep comparison of arrays
    const tiersChanged =
      JSON.stringify(newTiers?.slice().sort()) !== JSON.stringify(oldTiers?.slice().sort())
    if (tiersChanged) {
      window.logService.info('Tier filter changed', { from: oldTiers, to: newTiers })
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
    await loadData()
  }
)

// Initialize
onMounted(() => {
  loadData()
})
</script>
