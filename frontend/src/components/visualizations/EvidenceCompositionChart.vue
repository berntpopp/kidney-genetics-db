<template>
  <Card class="evidence-composition-container w-full">
    <CardHeader class="flex flex-col gap-2 pb-2 sm:flex-row sm:items-center">
      <div class="flex items-center gap-2">
        <Circle class="size-5 shrink-0" aria-hidden="true" />
        <CardTitle tag="h2" class="text-lg font-semibold">Evidence Composition</CardTitle>
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
              <span>{{ getViewDescription() }}</span>
            </TooltipContent>
          </Tooltip>
        </TooltipProvider>
      </div>
      <div class="sm:flex-1" />
      <ToggleGroup
        type="single"
        variant="outline"
        size="sm"
        aria-label="Composition view"
        :model-value="activeView"
        @update:model-value="v => v && (activeView = v)"
      >
        <ToggleGroupItem
          v-for="view in views"
          :key="view.value"
          :value="view.value"
          class="data-[state=on]:bg-primary data-[state=on]:text-primary-foreground"
        >
          {{ view.label }}
        </ToggleGroupItem>
      </ToggleGroup>
    </CardHeader>

    <CardContent>
      <DataState
        :loading="loading"
        :error="error"
        :empty="!data"
        error-title="Could not load evidence composition"
        empty-message="No composition data for the selected tiers."
        @retry="loadData"
      >
        <template #loading><ChartSkeleton :stats="0" /></template>

        <div v-if="activeView === 'tiers'">
          <h3 class="mb-4 text-base font-semibold">Evidence Tier Distribution</h3>
          <DataState :empty="tierChartData.length === 0" empty-message="No tier distribution data.">
            <D3DonutChart :data="tierChartData" :total="totalGenes" center-label="Total Genes" />
          </DataState>
        </div>

        <div v-else-if="activeView === 'coverage'">
          <h3 class="mb-4 text-base font-semibold">Source Coverage Distribution</h3>
          <DataState
            :empty="coverageChartData.length === 0"
            empty-message="No coverage distribution data."
          >
            <D3BarChart
              :data="coverageChartData"
              x-axis-label="Number of Sources"
              y-axis-label="Gene Count"
              value-label="genes"
            />
          </DataState>
        </div>

        <div v-else-if="activeView === 'weights'">
          <h3 class="mb-4 text-base font-semibold">Source Contribution Weights</h3>
          <DataState
            :empty="weightsChartData.length === 0"
            empty-message="No weight distribution data."
          >
            <D3DonutChart
              :data="weightsChartData"
              :show-total="true"
              :total="100"
              :center-label="`Total Coverage (${totalGenes.toLocaleString()} genes)`"
              :is-percentage="true"
              :value-formatter="v => v.toFixed(1)"
            />
          </DataState>
        </div>
      </DataState>
    </CardContent>
  </Card>
</template>

<script setup>
import { ref, computed, onMounted, watch } from 'vue'
import { Circle, CircleHelp } from 'lucide-vue-next'
import { statisticsApi } from '@/api/statistics'
import { Card, CardHeader, CardTitle, CardContent } from '@/components/ui/card'
import { Tooltip, TooltipContent, TooltipProvider, TooltipTrigger } from '@/components/ui/tooltip'
import { ToggleGroup, ToggleGroupItem } from '@/components/ui/toggle-group'
import { DataState } from '@/components/shared'
import ChartSkeleton from './ChartSkeleton.vue'
import D3DonutChart from './D3DonutChart.vue'
import D3BarChart from './D3BarChart.vue'
import { TIER_CONFIG } from '@/utils/evidenceTiers'
import { getSourceConfig, SOURCE_NAMES } from '@/utils/sources'

const views = [
  { value: 'tiers', label: 'Tiers' },
  { value: 'coverage', label: 'Coverage' },
  { value: 'weights', label: 'Weights' }
]

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
const activeView = ref('tiers') // Default to tiers view

// Computed properties
const tierChartData = computed(() => {
  if (!data.value?.evidence_tier_distribution) return []

  // Labels and colors from TIER_CONFIG, as everywhere else; unknown tiers stay neutral
  return data.value.evidence_tier_distribution.map(tier => ({
    category: TIER_CONFIG[tier.tier]?.label ?? tier.tier_label,
    gene_count: tier.gene_count,
    color: TIER_CONFIG[tier.tier]?.color ?? 'var(--muted-foreground)',
    icon: TIER_CONFIG[tier.tier]?.icon
  }))
})

const totalGenes = computed(() => {
  if (!data.value?.evidence_tier_distribution) return 0
  return data.value.evidence_tier_distribution.reduce((sum, tier) => sum + tier.gene_count, 0)
})

const coverageChartData = computed(() => {
  if (!data.value?.source_coverage_distribution) return []

  // Sort by source_count ascending (1 → 7) for natural left-to-right reading
  return data.value.source_coverage_distribution
    .map(item => ({
      category: `${item.source_count} source${item.source_count !== 1 ? 's' : ''}`,
      gene_count: item.gene_count,
      source_count: item.source_count // Keep for sorting
    }))
    .sort((a, b) => a.source_count - b.source_count) // Ascending order
})

const weightsChartData = computed(() => {
  if (!data.value?.source_contribution_weights) return []

  // Fixed source order and chart colours from utils/sources.ts, as on every chart
  const order = source => {
    const i = SOURCE_NAMES.indexOf(source)
    return i === -1 ? SOURCE_NAMES.length : i
  }
  return Object.entries(data.value.source_contribution_weights)
    .sort(([a], [b]) => order(a) - order(b))
    .map(([source, weight]) => {
      const config = getSourceConfig(source)
      return {
        category: config.displayName,
        gene_count: parseFloat((weight * 100).toFixed(1)), // Keep 1 decimal for display
        color: config.chartColor
      }
    })
})

// Methods
const loadData = async () => {
  loading.value = true
  error.value = null

  try {
    window.logService.info('Loading evidence composition', {
      selectedTiers: props.selectedTiers,
      hideZeroScores: !props.showInsufficientEvidence
    })
    const response = await statisticsApi.getEvidenceComposition(
      props.selectedTiers,
      !props.showInsufficientEvidence
    )
    data.value = response.data
  } catch (err) {
    error.value = err.message || 'Failed to load evidence composition data'
    window.logService.error('Error loading evidence composition:', err)
  } finally {
    loading.value = false
  }
}

const getViewDescription = () => {
  const descriptions = {
    tiers:
      'Distribution of genes across evidence tiers based on aggregated scores from all sources. Higher tiers indicate stronger evidence.',
    coverage:
      'Distribution showing how many sources each gene appears in. Genes in more sources generally have stronger evidence.',
    weights:
      'Relative contribution of each data source to the overall evidence base, calculated by evidence record counts.'
  }
  return descriptions[activeView.value] || ''
}

// Watch for selectedTiers and showInsufficientEvidence changes and reload data
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

watch(
  () => props.showInsufficientEvidence,
  async () => {
    await loadData()
  }
)

// Initialize
onMounted(() => {
  loadData()
})
</script>
