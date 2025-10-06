<template>
  <v-card class="source-distributions-container">
    <v-card-title class="d-flex align-center">
      <v-icon class="me-2">mdi-chart-bar</v-icon>
      Source Distributions
      <v-tooltip location="bottom">
        <template #activator="{ props }">
          <v-icon v-bind="props" class="me-2 text-medium-emphasis" size="small">
            mdi-help-circle-outline
          </v-icon>
        </template>
        <span>{{
          selectedSource
            ? getSourceDescription(selectedSource)
            : 'Select a source to see distribution'
        }}</span>
      </v-tooltip>
      <v-spacer />
      <v-select
        v-if="data && Object.keys(data).length > 0"
        v-model="selectedSource"
        :items="sourceOptions"
        density="compact"
        variant="outlined"
        class="me-2"
        style="max-width: 200px"
      />
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
      <div v-else-if="data && selectedSource && sourceData">
        <!-- Source metadata -->
        <v-card variant="outlined" class="mb-4">
          <v-card-text>
            <v-row class="text-center">
              <v-col v-for="(value, key) in sourceMetadata" :key="key" cols="12" sm="6" md="3">
                <div class="text-h6 text-primary">{{ value }}</div>
                <div class="text-caption">{{ formatMetadataLabel(key) }}</div>
              </v-col>
            </v-row>
          </v-card-text>
        </v-card>

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

          <!-- All other sources: D3 Bar Chart -->
          <D3BarChart
            v-else
            :data="d3ChartData"
            :x-axis-label="getXAxisLabel(selectedSource)"
            :y-axis-label="'Gene Count'"
          />
        </div>

        <!-- No data message -->
        <v-alert v-else type="info" variant="outlined" class="mb-4">
          No distribution data available for this source
        </v-alert>
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
const selectedSource = ref(null)

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
    const params = {}
    if (props.minTier) {
      params.min_tier = props.minTier
    }

    const response = await statisticsApi.getSourceDistributions(params.min_tier)
    data.value = response.data

    // Set default selected source
    if (data.value && Object.keys(data.value).length > 0) {
      selectedSource.value = Object.keys(data.value)[0]

      // Debug logging
      window.logService.info('Source distribution data loaded', {
        source: selectedSource.value,
        metadata: data.value[selectedSource.value]?.metadata,
        distributionCount: data.value[selectedSource.value]?.distribution?.length
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
    DiagnosticPanels: 'Shows distribution of genes by commercial diagnostic panel providers',
    ClinGen: 'Shows distribution of genes by ClinGen classification level',
    GenCC: 'Shows distribution of genes by GenCC classification level',
    HPO: 'Shows distribution of genes by number of HPO phenotype associations'
  }
  return descriptions[source] || `Distribution for ${source} data source`
}

const getXAxisLabel = source => {
  const labels = {
    PanelApp: 'Panel Count',
    PubTator: 'Publication Count',
    DiagnosticPanels: 'Provider',
    ClinGen: 'Classification',
    GenCC: 'Classification',
    HPO: 'Phenotype Count Range'
  }
  return labels[source] || 'Category'
}

// Watch for tier changes
watch(
  () => props.minTier,
  () => {
    loadData()
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
  background: rgb(var(--v-theme-surface));
  border-radius: 8px;
  border: 1px solid rgb(var(--v-theme-outline-variant));
}

/* Responsive adjustments */
@media (max-width: 600px) {
  .chart-container {
    padding: 16px;
    min-height: 300px;
  }
}
</style>
