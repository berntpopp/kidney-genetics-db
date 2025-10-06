<template>
  <v-card class="evidence-composition-container">
    <v-card-title class="d-flex align-center">
      <v-icon class="me-2">mdi-chart-donut</v-icon>
      Evidence Composition
      <v-tooltip location="bottom">
        <template #activator="{ props }">
          <v-icon v-bind="props" class="me-2 text-medium-emphasis" size="small">
            mdi-help-circle-outline
          </v-icon>
        </template>
        <span>{{ getViewDescription() }}</span>
      </v-tooltip>
      <v-spacer />
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
            <div v-if="data?.source_coverage_distribution" class="coverage-bars">
              <div
                v-for="item in data.source_coverage_distribution"
                :key="item.source_count"
                class="coverage-item"
              >
                <div class="coverage-label">
                  {{ item.source_count }} source{{ item.source_count !== 1 ? 's' : '' }}
                </div>
                <div class="coverage-bar-container">
                  <v-progress-linear
                    :model-value="item.percentage"
                    height="20"
                    rounded
                    color="info"
                    class="coverage-bar"
                  />
                  <div class="coverage-count">{{ item.gene_count }} genes</div>
                </div>
              </div>
            </div>
          </div>

          <!-- Source contribution weights -->
          <div v-else-if="activeView === 'weights'">
            <h3 class="text-h6 mb-4">Source Contribution Weights</h3>
            <div v-if="data?.source_contribution_weights" class="weights-list">
              <div
                v-for="(weight, source) in data.source_contribution_weights"
                :key="source"
                class="weight-item"
              >
                <div class="weight-header">
                  <div class="weight-source">{{ source }}</div>
                  <div class="weight-value">{{ (weight * 100).toFixed(1) }}%</div>
                </div>
                <v-progress-linear
                  :model-value="weight * 100"
                  height="20"
                  rounded
                  color="secondary"
                  class="weight-bar"
                />
              </div>
            </div>
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

// Computed properties
const tierChartData = computed(() => {
  if (!data.value?.evidence_tier_distribution) return []

  return data.value.evidence_tier_distribution.map(tier => ({
    category: tier.tier_label || tier.score_range,
    gene_count: tier.gene_count,
    color: tier.color || '#6B7280'
  }))
})

const totalGenes = computed(() => {
  if (!data.value?.evidence_tier_distribution) return 0
  return data.value.evidence_tier_distribution.reduce((sum, tier) => sum + tier.gene_count, 0)
})

// Methods
const loadData = async () => {
  loading.value = true
  error.value = null

  try {
    const response = await statisticsApi.getEvidenceComposition(props.minTier)
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

// Watch for minTier changes and reload data
watch(
  () => props.minTier,
  async (newTier, oldTier) => {
    if (newTier !== oldTier) {
      await loadData()
    }
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

/* Coverage bars */
.coverage-bars {
  display: flex;
  flex-direction: column;
  gap: 16px;
}

.coverage-item {
  display: flex;
  flex-direction: column;
  gap: 8px;
}

.coverage-label {
  font-weight: 500;
  color: rgb(var(--v-theme-on-surface));
  font-size: 14px;
}

.coverage-bar-container {
  position: relative;
  display: flex;
  align-items: center;
  gap: 12px;
}

.coverage-bar {
  flex: 1;
  min-width: 100px;
}

.coverage-count {
  font-weight: 500;
  font-size: 14px;
  color: rgb(var(--v-theme-info));
  min-width: 80px;
  text-align: right;
  font-variant-numeric: tabular-nums;
}

/* Weights list */
.weights-list {
  display: flex;
  flex-direction: column;
  gap: 16px;
}

.weight-item {
  display: flex;
  flex-direction: column;
  gap: 8px;
}

.weight-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.weight-source {
  font-weight: 500;
  color: rgb(var(--v-theme-on-surface));
  font-size: 14px;
}

.weight-value {
  font-weight: 600;
  font-size: 14px;
  color: rgb(var(--v-theme-secondary));
  font-variant-numeric: tabular-nums;
}

.weight-bar {
  flex: 1;
  min-height: 20px !important;
  height: 20px !important;
}

/* Responsive adjustments */
@media (max-width: 600px) {
  .chart-container {
    min-height: 300px;
    padding: 8px;
  }

  .coverage-bar-container,
  .weight-header {
    gap: 8px;
  }

  .coverage-count,
  .weight-value {
    min-width: 60px;
    font-size: 12px;
  }
}
</style>
