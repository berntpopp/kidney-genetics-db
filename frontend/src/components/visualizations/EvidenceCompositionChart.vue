<template>
  <Card class="evidence-composition-container w-full">
    <CardHeader class="flex flex-row items-center space-y-0 pb-2">
      <Circle class="size-5 mr-2" />
      <CardTitle class="text-base">Evidence Composition</CardTitle>
      <TooltipProvider>
        <Tooltip>
          <TooltipTrigger as-child>
            <CircleHelp class="size-4 ml-2 text-muted-foreground cursor-help" />
          </TooltipTrigger>
          <TooltipContent side="bottom" class="max-w-xs">
            <span>{{ getViewDescription() }}</span>
          </TooltipContent>
        </Tooltip>
      </TooltipProvider>
      <div class="flex-1" />
      <div class="inline-flex rounded-md border mr-2">
        <Button
          :variant="activeView === 'tiers' ? 'default' : 'ghost'"
          size="sm"
          class="rounded-none first:rounded-l-md last:rounded-r-md"
          @click="activeView = 'tiers'"
        >
          Tiers
        </Button>
        <Button
          :variant="activeView === 'coverage' ? 'default' : 'ghost'"
          size="sm"
          class="rounded-none first:rounded-l-md last:rounded-r-md"
          @click="activeView = 'coverage'"
        >
          Coverage
        </Button>
        <Button
          :variant="activeView === 'weights' ? 'default' : 'ghost'"
          size="sm"
          class="rounded-none first:rounded-l-md last:rounded-r-md"
          @click="activeView = 'weights'"
        >
          Weights
        </Button>
      </div>
    </CardHeader>

    <CardContent>
      <!-- Loading state -->
      <div v-if="loading" class="flex items-center justify-center" style="height: 400px">
        <div
          class="h-16 w-16 animate-spin rounded-full border-4 border-primary border-t-transparent"
        />
      </div>

      <!-- Error state -->
      <Alert v-else-if="error" variant="destructive" class="mb-4">
        <AlertDescription>{{ error }}</AlertDescription>
      </Alert>

      <!-- Chart visualization -->
      <div v-else-if="data">
        <!-- Chart container -->
        <div class="chart-container">
          <!-- Evidence Tier Distribution -->
          <div v-if="activeView === 'tiers'">
            <h3 class="text-lg font-semibold mb-4">Evidence Tier Distribution</h3>
            <div v-if="tierChartData.length > 0">
              <D3DonutChart :data="tierChartData" :total="totalGenes" center-label="Total Genes" />
            </div>
            <Alert v-else class="mb-4">
              <AlertDescription>No tier distribution data available</AlertDescription>
            </Alert>
          </div>

          <!-- Source coverage chart -->
          <div v-else-if="activeView === 'coverage'">
            <h3 class="text-lg font-semibold mb-4">Source Coverage Distribution</h3>
            <div v-if="coverageChartData.length > 0">
              <D3BarChart
                :data="coverageChartData"
                x-axis-label="Number of Sources"
                y-axis-label="Gene Count"
                bar-color="#2196F3"
                value-label="genes"
              />
            </div>
            <Alert v-else class="mb-4">
              <AlertDescription>No coverage distribution data available</AlertDescription>
            </Alert>
          </div>

          <!-- Source contribution weights -->
          <div v-else-if="activeView === 'weights'">
            <h3 class="text-lg font-semibold mb-4">Source Contribution Weights</h3>
            <div v-if="weightsChartData.length > 0">
              <D3DonutChart
                :data="weightsChartData"
                :show-total="true"
                :total="100"
                :center-label="`Total Coverage (${totalGenes.toLocaleString()} genes)`"
                :is-percentage="true"
                :value-formatter="v => v.toFixed(1)"
              />
            </div>
            <Alert v-else class="mb-4">
              <AlertDescription>No weight distribution data available</AlertDescription>
            </Alert>
          </div>
        </div>
      </div>
    </CardContent>
  </Card>
</template>

<script setup>
import { ref, computed, onMounted, watch } from 'vue'
import { Circle, CircleHelp } from 'lucide-vue-next'
import { statisticsApi } from '@/api/statistics'
import { Card, CardHeader, CardTitle, CardContent } from '@/components/ui/card'
import { Tooltip, TooltipContent, TooltipProvider, TooltipTrigger } from '@/components/ui/tooltip'
import { Button } from '@/components/ui/button'
import { Alert, AlertDescription } from '@/components/ui/alert'
import D3DonutChart from './D3DonutChart.vue'
import D3BarChart from './D3BarChart.vue'

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
const loading = ref(false)
const error = ref(null)
const data = ref(null)
const activeView = ref('tiers') // Default to tiers view

// Computed properties
const tierChartData = computed(() => {
  if (!data.value?.evidence_tier_distribution) return []

  // Use tier_label from backend (matches evidenceTiers.js labels)
  return data.value.evidence_tier_distribution.map(tier => ({
    category: tier.tier_label,
    gene_count: tier.gene_count,
    color: tier.color
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

  // Define source colors for donut chart
  const sourceColors = {
    PubTator: '#FF6384',
    HPO: '#36A2EB',
    DiagnosticPanels: '#FFCE56',
    Literature: '#4BC0C0',
    PanelApp: '#9966FF',
    GenCC: '#FF9F40',
    ClinGen: '#C9CBCF'
  }

  // Convert weights object to array for donut chart (percentages)
  return Object.entries(data.value.source_contribution_weights)
    .map(([source, weight]) => ({
      category: source,
      gene_count: parseFloat((weight * 100).toFixed(1)), // Keep 1 decimal for display
      color: sourceColors[source] || '#9E9E9E'
    }))
    .sort((a, b) => b.gene_count - a.gene_count)
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

<style scoped>
.chart-container {
  min-height: 400px;
  padding: 16px;
  background: hsl(var(--card));
  border-radius: 4px;
  border: 1px solid hsl(var(--border));
}

/* Responsive adjustments */
@media (max-width: 600px) {
  .chart-container {
    min-height: 300px;
    padding: 8px;
  }
}
</style>
