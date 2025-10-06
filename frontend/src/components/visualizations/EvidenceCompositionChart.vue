<template>
  <v-card class="evidence-composition-container">
    <v-card-title class="d-flex align-center">
      <v-icon class="me-2">mdi-chart-donut</v-icon>
      Evidence Composition
      <v-tooltip location="bottom">
        <template #activator="{ props: tooltipProps }">
          <v-icon v-bind="tooltipProps" class="me-2 text-medium-emphasis" size="small">
            mdi-help-circle-outline
          </v-icon>
        </template>
        <span>{{ getViewDescription() }}</span>
      </v-tooltip>
      <v-spacer />
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
      <v-btn-toggle v-model="activeView" variant="outlined" density="compact" class="me-2">
        <v-btn value="tiers" size="small">Tiers</v-btn>
        <v-btn value="coverage" size="small">Coverage</v-btn>
        <v-btn value="weights" size="small">Weights</v-btn>
      </v-btn-toggle>
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

      <!-- Chart visualization -->
      <div v-else-if="data">
        <!-- Chart container -->
        <div class="chart-container">
          <!-- Evidence Tier Distribution -->
          <div v-if="activeView === 'tiers'">
            <h3 class="text-h6 mb-4">Evidence Tier Distribution</h3>
            <div v-if="tierChartData.length > 0">
              <D3DonutChart :data="tierChartData" :total="totalGenes" center-label="Total Genes" />
            </div>
            <v-alert v-else type="info" variant="outlined">
              No tier distribution data available
            </v-alert>
          </div>

          <!-- Source coverage chart -->
          <div v-else-if="activeView === 'coverage'">
            <h3 class="text-h6 mb-4">Source Coverage Distribution</h3>
            <div v-if="coverageChartData.length > 0">
              <D3BarChart
                :data="coverageChartData"
                x-axis-label="Number of Sources"
                y-axis-label="Gene Count"
                bar-color="#2196F3"
                value-label="genes"
              />
            </div>
            <v-alert v-else type="info" variant="outlined">
              No coverage distribution data available
            </v-alert>
          </div>

          <!-- Source contribution weights -->
          <div v-else-if="activeView === 'weights'">
            <h3 class="text-h6 mb-4">Source Contribution Weights</h3>
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
            <v-alert v-else type="info" variant="outlined">
              No weight distribution data available
            </v-alert>
          </div>
        </div>
      </div>
    </v-card-text>
  </v-card>
</template>

<script setup>
import { ref, computed, onMounted, watch } from 'vue'
import { statisticsApi } from '@/api/statistics'
import D3DonutChart from './D3DonutChart.vue'
import D3BarChart from './D3BarChart.vue'

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
const activeView = ref('tiers') // Default to tiers view
const showInsufficientEvidence = ref(false) // Default: hide genes with score = 0

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
      minTier: props.minTier,
      hideZeroScores: !showInsufficientEvidence.value
    })
    const response = await statisticsApi.getEvidenceComposition(
      props.minTier,
      !showInsufficientEvidence.value // Invert: checkbox ON = show, API param = hide
    )
    data.value = response.data
  } catch (err) {
    error.value = err.message || 'Failed to load evidence composition data'
    window.logService.error('Error loading evidence composition:', err)
  } finally {
    loading.value = false
  }
}

const refreshData = () => {
  loadData()
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

// Watch for minTier and showInsufficientEvidence changes and reload data
watch(
  () => props.minTier,
  async (newTier, oldTier) => {
    if (newTier !== oldTier) {
      await loadData()
    }
  }
)

watch(
  () => showInsufficientEvidence.value,
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
.evidence-composition-container {
  width: 100%;
}

.chart-container {
  min-height: 400px;
  padding: 16px;
  background: rgb(var(--v-theme-surface));
  border-radius: 4px;
  border: 1px solid rgb(var(--v-theme-outline-variant));
}

/* Responsive adjustments */
@media (max-width: 600px) {
  .chart-container {
    min-height: 300px;
    padding: 8px;
  }
}
</style>
