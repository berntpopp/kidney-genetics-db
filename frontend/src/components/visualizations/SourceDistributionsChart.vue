<template>
  <Card class="source-distributions-container w-full">
    <CardHeader class="flex flex-row items-center space-y-0 pb-2">
      <ChartBar class="size-5 mr-2" />
      <CardTitle class="text-lg font-semibold">Source Distributions</CardTitle>
      <TooltipProvider>
        <Tooltip>
          <TooltipTrigger as-child>
            <CircleHelp class="size-4 ml-2 text-muted-foreground cursor-help" />
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
      <TooltipProvider>
        <Tooltip>
          <TooltipTrigger as-child>
            <div class="flex items-center space-x-2 mr-2">
              <Checkbox
                id="show-insufficient-src"
                :checked="showInsufficientEvidence"
                @update:checked="showInsufficientEvidence = $event"
              />
              <Label for="show-insufficient-src" class="text-sm">Show insufficient evidence</Label>
            </div>
          </TooltipTrigger>
          <TooltipContent side="bottom">
            <span>Include genes with percentage_score = 0 (no meaningful evidence)</span>
          </TooltipContent>
        </Tooltip>
      </TooltipProvider>
      <Select
        v-if="data && Object.keys(data).length > 0"
        v-model="selectedSource"
      >
        <SelectTrigger class="w-[200px] h-8 mr-2">
          <SelectValue placeholder="Select source" />
        </SelectTrigger>
        <SelectContent>
          <SelectItem
            v-for="option in sourceOptions"
            :key="option.value"
            :value="option.value"
          >
            {{ option.title }}
          </SelectItem>
        </SelectContent>
      </Select>
      <Button
        variant="ghost"
        size="icon-sm"
        :disabled="loading"
        @click="refreshData"
      >
        <RefreshCw class="size-4" :class="{ 'animate-spin': loading }" />
      </Button>
    </CardHeader>

    <CardContent>
      <!-- Loading state -->
      <div v-if="loading" class="flex items-center justify-center" style="height: 400px">
        <div class="h-16 w-16 animate-spin rounded-full border-4 border-primary border-t-transparent" />
      </div>

      <!-- Error state -->
      <Alert v-else-if="error" variant="destructive" class="mb-4">
        <AlertDescription>{{ error }}</AlertDescription>
      </Alert>

      <!-- Chart visualization -->
      <div v-else-if="data && selectedSource && sourceData">
        <!-- Source metadata -->
        <Card class="mb-4">
          <CardContent class="pt-6">
            <div class="grid grid-cols-2 md:grid-cols-4 gap-4 text-center">
              <div v-for="(value, key) in sourceMetadata" :key="key">
                <div class="text-lg font-semibold text-primary">{{ value }}</div>
                <div class="text-xs text-muted-foreground">{{ formatMetadataLabel(key) }}</div>
              </div>
            </div>
          </CardContent>
        </Card>

        <!-- Dynamic chart based on visualization type -->
        <div v-if="hasDistributionData" class="chart-container">
          <!-- ClinGen/GenCC: D3 Donut for classifications -->
          <D3DonutChart
            v-if="visualizationType === 'classification_donut'"
            :data="d3ChartData"
            :total="sourceMetadata.total_genes"
            :average="sourceMetadata.average"
            center-label="Total"
          />

          <!-- All other sources: D3 Bar Chart with blue color -->
          <D3BarChart
            v-else
            :data="d3ChartData"
            :x-axis-label="getXAxisLabel(selectedSource)"
            :y-axis-label="'Gene Count'"
            bar-color="#1E88E5"
          />
        </div>

        <!-- No data message -->
        <Alert v-else class="mb-4">
          <AlertDescription>No distribution data available for this source</AlertDescription>
        </Alert>
      </div>
    </CardContent>
  </Card>
</template>

<script setup>
import { ref, computed, onMounted, watch } from 'vue'
import { ChartBar, CircleHelp, RefreshCw } from 'lucide-vue-next'
import { statisticsApi } from '@/api/statistics'
import D3DonutChart from './D3DonutChart.vue'
import D3BarChart from './D3BarChart.vue'

import { Card, CardHeader, CardTitle, CardContent } from '@/components/ui/card'
import { TooltipProvider, Tooltip, TooltipTrigger, TooltipContent } from '@/components/ui/tooltip'
import { Checkbox } from '@/components/ui/checkbox'
import { Label } from '@/components/ui/label'
import { Select, SelectTrigger, SelectValue, SelectContent, SelectItem } from '@/components/ui/select'
import { Button } from '@/components/ui/button'
import { Alert, AlertDescription } from '@/components/ui/alert'

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
const selectedSource = ref(null)
const showInsufficientEvidence = ref(false) // Default: hide genes with score = 0

// Computed properties
const sourceOptions = computed(() => {
  if (!data.value) return []
  return Object.keys(data.value).map(source => ({
    title: source,
    value: source
  }))
})

const sourceMetadata = computed(() => {
  if (!data.value || !selectedSource.value) return {}
  return data.value[selectedSource.value]?.metadata || {}
})

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

  // Color palette for donut charts
  const colors = [
    '#1f77b4',
    '#ff7f0e',
    '#2ca02c',
    '#d62728',
    '#9467bd',
    '#8c564b',
    '#e377c2',
    '#7f7f7f'
  ]

  return sourceData.value.distribution
    .filter(d => d && d.category !== undefined && d.gene_count !== undefined)
    .map((d, i) => ({
      category: String(d.category),
      gene_count: Number(d.gene_count),
      color: colors[i % colors.length] // Only used by donut chart
    }))
})

// Methods
const loadData = async () => {
  loading.value = true
  error.value = null

  try {
    const response = await statisticsApi.getSourceDistributions(
      props.selectedTiers,
      !showInsufficientEvidence.value // Invert: checkbox OFF = hide (true), checkbox ON = show (false)
    )
    data.value = response.data

    // Set default selected source only if not already set or if current selection is no longer available
    if (data.value && Object.keys(data.value).length > 0) {
      const availableSources = Object.keys(data.value)

      // Only reset selectedSource if it's not set OR if it's no longer in the available sources
      if (!selectedSource.value || !availableSources.includes(selectedSource.value)) {
        selectedSource.value = availableSources[0]
      }

      window.logService.info('Source distribution data loaded', {
        source: selectedSource.value,
        availableSources: availableSources,
        metadata: data.value[selectedSource.value]?.metadata,
        distributionCount: data.value[selectedSource.value]?.distribution?.length,
        hideZeroScores: !showInsufficientEvidence.value
      })
    }
  } catch (err) {
    error.value = err.message || 'Failed to load source distribution data'
    window.logService.error('Error loading source distributions:', err)
  } finally {
    loading.value = false
  }
}

const refreshData = () => {
  loadData()
}

const formatMetadataLabel = key => {
  return key.replace(/_/g, ' ').replace(/\b\w/g, char => char.toUpperCase())
}

const getSourceDescription = source => {
  const descriptions = {
    PanelApp: 'Shows distribution of genes by number of diagnostic panels they appear in',
    PubTator: 'Shows distribution of genes by number of publications mentioning them',
    DiagnosticPanels:
      'Shows distribution of genes by number of commercial diagnostic providers offering tests',
    ClinGen: 'Shows distribution of genes by ClinGen classification level',
    GenCC: 'Shows distribution of genes by GenCC classification level',
    HPO: 'Shows distribution of genes by number of HPO term associations'
  }
  return descriptions[source] || `Distribution for ${source} data source`
}

const getXAxisLabel = source => {
  const labels = {
    PanelApp: 'Panel Count',
    PubTator: 'Publication Count',
    DiagnosticPanels: 'Provider Count',
    ClinGen: 'Classification',
    GenCC: 'Classification',
    HPO: 'HPO Term Count Range'
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
  () => showInsufficientEvidence.value,
  async () => {
    window.logService.info('Insufficient evidence toggle changed', {
      showInsufficientEvidence: showInsufficientEvidence.value
    })
    await loadData()
  }
)

// Initialize
onMounted(() => {
  loadData()
})
</script>

<style scoped>
.source-distributions-container {
  width: 100%;
}

.chart-container {
  min-height: 400px;
  padding: 24px;
  background: hsl(var(--card));
  border-radius: 8px;
  border: 1px solid hsl(var(--border));
}

/* Responsive adjustments */
@media (max-width: 600px) {
  .chart-container {
    padding: 16px;
    min-height: 300px;
  }
}
</style>
