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
            : 'Select a source to see distribution of evidence counts'
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
      <div v-else-if="data && selectedSource">
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

        <!-- Simple bar visualization -->
        <div v-if="sourceData" class="chart-container">
          <div class="distribution-bars">
            <div
              v-for="item in sourceData.distribution"
              :key="item.source_count"
              class="distribution-item"
            >
              <div class="distribution-label">
                {{ item.source_count }} {{ getItemLabel(item.source_count) }}
              </div>
              <div class="distribution-bar-container">
                <v-progress-linear
                  :model-value="(item.gene_count / maxCount) * 100"
                  height="24"
                  rounded
                  color="primary"
                  class="distribution-bar"
                />
                <div class="distribution-count">{{ item.gene_count }} genes</div>
              </div>
            </div>
          </div>
        </div>
      </div>
    </v-card-text>
  </v-card>
</template>

<script setup>
import { ref, computed, onMounted } from 'vue'
import { statisticsApi } from '@/api/statistics'

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

const maxCount = computed(() => {
  if (!sourceData.value?.distribution) return 0
  return Math.max(...sourceData.value.distribution.map(item => item.gene_count))
})

// Methods
const loadData = async () => {
  loading.value = true
  error.value = null

  try {
    const response = await statisticsApi.getSourceDistributions()
    data.value = response.data

    // Set default selected source
    if (data.value && Object.keys(data.value).length > 0) {
      selectedSource.value = Object.keys(data.value)[0]
    }
  } catch (err) {
    error.value = err.message || 'Failed to load source distribution data'
    console.error('Error loading source distributions:', err)
  } finally {
    loading.value = false
  }
}

const refreshData = () => {
  loadData()
}

const getItemLabel = count => {
  if (selectedSource.value === 'PanelApp') return count === 1 ? 'panel' : 'panels'
  if (selectedSource.value === 'PubTator') return count === 1 ? 'publication' : 'publications'
  if (selectedSource.value === 'DiagnosticPanels') return count === 1 ? 'panel' : 'panels'
  return count === 1 ? 'evidence item' : 'evidence items'
}

const formatMetadataLabel = key => {
  return key.replace(/_/g, ' ').replace(/\b\w/g, char => char.toUpperCase())
}

const getSourceDescription = source => {
  const descriptions = {
    PanelApp: 'Shows distribution of genes by number of diagnostic panels they appear in',
    PubTator: 'Shows distribution of genes by number of publications mentioning them',
    DiagnosticPanels: 'Shows distribution of genes by number of commercial diagnostic panels',
    ClinGen: 'Shows genes with ClinGen evidence (typically one evidence record per gene)',
    GenCC: 'Shows genes with GenCC curation (typically one record per gene)',
    HPO: 'Shows genes with HPO phenotype associations (typically one record per gene)'
  }
  return descriptions[source] || `Distribution of evidence counts for ${source} data source`
}

// Watch for data changes - no need to do anything, computed properties handle it

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
  min-height: 200px;
  padding: 16px;
  background: rgb(var(--v-theme-surface));
  border-radius: 4px;
  border: 1px solid rgb(var(--v-theme-outline-variant));
}

.distribution-bars {
  display: flex;
  flex-direction: column;
  gap: 16px;
}

.distribution-item {
  display: flex;
  flex-direction: column;
  gap: 8px;
}

.distribution-label {
  font-weight: 500;
  color: rgb(var(--v-theme-on-surface));
  font-size: 14px;
}

.distribution-bar-container {
  position: relative;
  display: flex;
  align-items: center;
  gap: 12px;
}

.distribution-bar {
  flex: 1;
  min-width: 100px;
}

.distribution-count {
  font-weight: 500;
  font-size: 14px;
  color: rgb(var(--v-theme-primary));
  min-width: 80px;
  text-align: right;
  font-variant-numeric: tabular-nums;
}

/* Responsive adjustments */
@media (max-width: 600px) {
  .chart-container {
    padding: 8px;
  }

  .distribution-bar-container {
    gap: 8px;
  }

  .distribution-count {
    min-width: 60px;
    font-size: 12px;
  }
}
</style>
