<template>
  <v-dialog v-model="dialog" max-width="800" scrollable>
    <v-card>
      <!-- Header -->
      <v-card-title class="d-flex align-center justify-space-between pa-4">
        <div class="d-flex align-center">
          <v-chip :color="clusterColor" size="small" label class="mr-3">
            <Atom class="size-5 mr-1" />
            {{ clusterDisplayName || `Cluster ${clusterId + 1}` }}
          </v-chip>
          <div>
            <h3 class="text-h6 font-weight-medium">Cluster Details</h3>
            <p class="text-caption text-medium-emphasis mt-1">
              {{ geneCount }} gene{{ geneCount !== 1 ? 's' : '' }} in cluster
            </p>
          </div>
        </div>
        <v-btn icon="mdi-close" variant="text" size="small" @click="close" />
      </v-card-title>

      <v-divider />

      <!-- HPO Classification Statistics -->
      <v-card-text v-if="clusterStatistics" class="pa-4 bg-surface-variant">
        <div class="d-flex align-center mb-3">
          <ChartBarBig class="size-5 mr-2 text-primary" />
          <h4 class="text-subtitle-1 font-weight-medium">HPO Classification Summary</h4>
          <v-chip size="x-small" class="ml-auto" label>
            <Database class="size-3 mr-1" />
            {{ clusterStatistics.hpoDataCount }} / {{ clusterStatistics.total }} genes ({{
              clusterStatistics.hpoDataPercentage
            }}%)
          </v-chip>
        </div>

        <v-row dense>
          <!-- Clinical Classification -->
          <v-col v-if="clusterStatistics.clinical.length > 0" cols="12" md="4">
            <div class="stats-section">
              <div class="text-caption font-weight-medium text-medium-emphasis mb-2">
                Clinical Classification
              </div>
              <div class="d-flex flex-wrap ga-1">
                <v-chip
                  v-for="stat in clusterStatistics.clinical"
                  :key="stat.key"
                  :color="stat.color"
                  size="x-small"
                  label
                >
                  {{ stat.label }}: {{ stat.percentage }}%
                </v-chip>
              </div>
            </div>
          </v-col>

          <!-- Age of Onset -->
          <v-col v-if="clusterStatistics.onset.length > 0" cols="12" md="4">
            <div class="stats-section">
              <div class="text-caption font-weight-medium text-medium-emphasis mb-2">
                Age of Onset
              </div>
              <div class="d-flex flex-wrap ga-1">
                <v-chip
                  v-for="stat in clusterStatistics.onset"
                  :key="stat.key"
                  :color="stat.color"
                  size="x-small"
                  label
                >
                  {{ stat.label }}: {{ stat.percentage }}%
                </v-chip>
              </div>
            </div>
          </v-col>

          <!-- Syndromic Assessment -->
          <v-col v-if="clusterStatistics.syndromic.syndromicCount > 0" cols="12" md="4">
            <div class="stats-section">
              <div class="text-caption font-weight-medium text-medium-emphasis mb-2">
                Syndromic Assessment
              </div>
              <div class="d-flex flex-wrap ga-1">
                <v-chip
                  :color="networkAnalysisConfig.nodeColoring.colorSchemes.syndromic.true"
                  size="x-small"
                  label
                >
                  Syndromic: {{ clusterStatistics.syndromic.syndromicPercentage }}%
                </v-chip>
                <v-chip
                  :color="networkAnalysisConfig.nodeColoring.colorSchemes.syndromic.false"
                  size="x-small"
                  label
                >
                  Isolated: {{ clusterStatistics.syndromic.isolatedPercentage }}%
                </v-chip>
              </div>
            </div>
          </v-col>
        </v-row>
      </v-card-text>

      <v-divider v-if="clusterStatistics" />

      <!-- Gene Table -->
      <v-card-text class="pa-0">
        <v-data-table
          :headers="headers"
          :items="genes"
          :items-per-page="itemsPerPage"
          :page="page"
          hide-default-footer
          class="cluster-genes-table"
        >
          <!-- Gene Symbol with Link -->
          <template #item.symbol="{ item }">
            <router-link :to="`/genes/${item.symbol}`" class="gene-link">
              <v-chip size="small" color="primary" variant="outlined">
                <Dna class="size-4 mr-1" />
                {{ item.symbol }}
              </v-chip>
            </router-link>
          </template>

          <!-- Gene ID -->
          <template #item.gene_id="{ item }">
            <span class="text-mono text-caption">{{ item.gene_id }}</span>
          </template>

          <!-- Actions -->
          <template #item.actions="{ item }">
            <div class="d-flex ga-1">
              <v-tooltip location="bottom">
                <template #activator="{ props: tooltipProps }">
                  <v-btn
                    icon="mdi-eye"
                    variant="text"
                    size="x-small"
                    v-bind="tooltipProps"
                    :to="`/genes/${item.symbol}`"
                  />
                </template>
                <span>View gene details</span>
              </v-tooltip>

              <v-tooltip location="bottom">
                <template #activator="{ props: tooltipProps }">
                  <v-btn
                    icon="mdi-content-copy"
                    variant="text"
                    size="x-small"
                    v-bind="tooltipProps"
                    @click="copyGeneSymbol(item.symbol)"
                  />
                </template>
                <span>Copy gene symbol</span>
              </v-tooltip>

              <v-tooltip location="bottom">
                <template #activator="{ props: tooltipProps }">
                  <v-btn
                    icon="mdi-map-marker"
                    variant="text"
                    size="x-small"
                    v-bind="tooltipProps"
                    @click="$emit('highlightGene', item.gene_id)"
                  />
                </template>
                <span>Highlight in network</span>
              </v-tooltip>
            </div>
          </template>
        </v-data-table>
      </v-card-text>

      <!-- Pagination -->
      <v-divider v-if="totalPages > 1" />
      <v-card-text v-if="totalPages > 1" class="pa-3">
        <div class="d-flex align-center justify-space-between">
          <div class="text-caption text-medium-emphasis">
            {{ paginationText }}
          </div>
          <div class="d-flex align-center ga-2">
            <v-select
              v-model="itemsPerPage"
              :items="itemsPerPageOptions"
              label="Per page"
              density="compact"
              variant="outlined"
              hide-details
              style="max-width: 100px"
            />
            <v-btn
              icon="mdi-chevron-left"
              variant="text"
              size="small"
              :disabled="page === 1"
              @click="page--"
            />
            <span class="text-caption">{{ page }} / {{ totalPages }}</span>
            <v-btn
              icon="mdi-chevron-right"
              variant="text"
              size="small"
              :disabled="page === totalPages"
              @click="page++"
            />
          </div>
        </div>
      </v-card-text>

      <v-divider />

      <!-- Footer Actions -->
      <v-card-actions class="pa-3">
        <v-btn variant="text" prepend-icon="mdi-download" size="small" @click="exportClusterGenes">
          Export Genes
        </v-btn>
        <v-spacer />
        <v-btn variant="tonal" @click="close">Close</v-btn>
      </v-card-actions>
    </v-card>
  </v-dialog>
</template>

<script setup>
import { ref, computed, watch } from 'vue'
import { Atom, ChartBarBig, Database, Dna } from 'lucide-vue-next'
import { networkAnalysisConfig } from '../../config/networkAnalysis'

// Props
const props = defineProps({
  modelValue: {
    type: Boolean,
    default: false
  },
  clusterId: {
    type: Number,
    default: null
  },
  clusterDisplayName: {
    type: String,
    default: ''
  },
  clusterColor: {
    type: String,
    default: '#1976D2'
  },
  genes: {
    type: Array,
    default: () => []
  },
  hpoClassifications: {
    type: Object,
    default: null
  }
})

// Emits
const emit = defineEmits(['update:modelValue', 'highlightGene'])

// Refs
const page = ref(1)
const itemsPerPage = ref(10)

// Computed
const dialog = computed({
  get: () => props.modelValue,
  set: value => emit('update:modelValue', value)
})

const geneCount = computed(() => props.genes.length)

const totalPages = computed(() => Math.ceil(geneCount.value / itemsPerPage.value))

const paginationText = computed(() => {
  if (geneCount.value === 0) return ''
  const start = (page.value - 1) * itemsPerPage.value + 1
  const end = Math.min(page.value * itemsPerPage.value, geneCount.value)
  return `Showing ${start}–${end} of ${geneCount.value}`
})

// HPO classification statistics for this cluster
const clusterStatistics = computed(() => {
  if (!props.hpoClassifications?.data || props.genes.length === 0) {
    return null
  }

  // Build HPO lookup
  const hpoLookup = new Map()
  props.hpoClassifications.data.forEach(item => {
    hpoLookup.set(item.gene_id, item)
  })

  // Compute statistics for this cluster's genes
  const clinicalCounts = {}
  const onsetCounts = {}
  let syndromicCount = 0
  let isolatedCount = 0
  let hpoDataCount = 0
  const total = props.genes.length

  props.genes.forEach(gene => {
    const classification = hpoLookup.get(gene.gene_id)
    if (classification) {
      hpoDataCount++

      // Clinical group
      const clinicalGroup = classification.clinical_group || 'null'
      clinicalCounts[clinicalGroup] = (clinicalCounts[clinicalGroup] || 0) + 1

      // Onset group
      const onsetGroup = classification.onset_group || 'null'
      onsetCounts[onsetGroup] = (onsetCounts[onsetGroup] || 0) + 1

      // Syndromic status
      if (classification.is_syndromic) {
        syndromicCount++
      } else {
        isolatedCount++
      }
    }
  })

  if (hpoDataCount === 0) return null

  // Convert to sorted arrays
  const clinicalBreakdown = Object.entries(clinicalCounts)
    .map(([key, count]) => ({
      key,
      label: networkAnalysisConfig.nodeColoring.labels.clinical_group[key] || key,
      color: networkAnalysisConfig.nodeColoring.colorSchemes.clinical_group[key],
      count,
      percentage: ((count / hpoDataCount) * 100).toFixed(1)
    }))
    .sort((a, b) => b.count - a.count)

  const onsetBreakdown = Object.entries(onsetCounts)
    .map(([key, count]) => ({
      key,
      label: networkAnalysisConfig.nodeColoring.labels.onset_group[key] || key,
      color: networkAnalysisConfig.nodeColoring.colorSchemes.onset_group[key],
      count,
      percentage: ((count / hpoDataCount) * 100).toFixed(1)
    }))
    .sort((a, b) => b.count - a.count)

  return {
    total,
    hpoDataCount,
    hpoDataPercentage: ((hpoDataCount / total) * 100).toFixed(1),
    clinical: clinicalBreakdown,
    onset: onsetBreakdown,
    syndromic: {
      syndromicCount,
      syndromicPercentage: ((syndromicCount / hpoDataCount) * 100).toFixed(1),
      isolatedCount,
      isolatedPercentage: ((isolatedCount / hpoDataCount) * 100).toFixed(1)
    }
  }
})

// Options
const itemsPerPageOptions = [10, 20, 50, 100]

const headers = [
  { title: 'Gene Symbol', key: 'symbol', sortable: true },
  { title: 'Gene ID', key: 'gene_id', sortable: true },
  { title: 'Actions', key: 'actions', sortable: false, align: 'end' }
]

// Methods
const close = () => {
  dialog.value = false
}

const copyGeneSymbol = symbol => {
  navigator.clipboard
    .writeText(symbol)
    .then(() => {
      // Successfully copied - silent success (standard UX pattern for copy operations)
      window.logService?.debug('[ClusterDetails] Gene symbol copied to clipboard', { symbol })
    })
    .catch(error => {
      // Log copy failure
      window.logService?.error('[ClusterDetails] Failed to copy gene symbol', {
        symbol,
        error: error.message
      })
    })
}

const exportClusterGenes = () => {
  if (props.genes.length === 0) return

  // Use display name or fallback to cluster ID
  const clusterName = props.clusterDisplayName || `Cluster ${props.clusterId + 1}`

  // Create CSV content
  const headers = ['Gene Symbol', 'Gene ID', 'Cluster']
  const rows = props.genes.map(g => [g.symbol, g.gene_id, clusterName])

  const csv = [headers.join(','), ...rows.map(row => row.join(','))].join('\n')

  // Download CSV
  const blob = new Blob([csv], { type: 'text/csv' })
  const link = document.createElement('a')
  link.href = URL.createObjectURL(blob)
  const sanitizedName = clusterName.toLowerCase().replace(/\s+/g, '_')
  link.download = `${sanitizedName}_genes_${Date.now()}.csv`
  link.click()
}

// Reset page when genes change
watch(
  () => props.genes,
  () => {
    page.value = 1
  }
)
</script>

<style scoped>
/* Following Style Guide - Clean table display */
.cluster-genes-table :deep(table) {
  table-layout: auto;
}

.cluster-genes-table :deep(th) {
  font-weight: 600;
  white-space: nowrap;
}

.cluster-genes-table :deep(td) {
  padding: 12px 16px;
}

.gene-link {
  text-decoration: none;
  transition: opacity 0.2s;
}

.gene-link:hover {
  opacity: 0.8;
}

.text-mono {
  font-family: 'Courier New', monospace;
  font-size: 0.875rem;
}

/* Statistics section styling */
.stats-section {
  height: 100%;
}

/* Dark theme adjustments */
.v-theme--dark .v-card {
  background: rgb(var(--v-theme-surface));
}
</style>
