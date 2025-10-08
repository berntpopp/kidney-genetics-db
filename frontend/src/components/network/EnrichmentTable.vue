<template>
  <v-card elevation="2" class="enrichment-table-card" rounded="lg">
    <v-card-title class="d-flex align-center justify-space-between pa-4">
      <div>
        <h3 class="text-h6 font-weight-medium">Functional Enrichment Analysis</h3>
        <p class="text-caption text-medium-emphasis mt-1">
          {{ enrichmentStats }}
        </p>
      </div>
      <div class="d-flex ga-2">
        <v-tooltip location="bottom">
          <template #activator="{ props: tooltipProps }">
            <v-btn
              icon="mdi-download"
              variant="text"
              size="small"
              v-bind="tooltipProps"
              :disabled="!results || results.length === 0"
              @click="exportResults"
            />
          </template>
          <span>Export results as CSV</span>
        </v-tooltip>

        <v-tooltip location="bottom">
          <template #activator="{ props: tooltipProps }">
            <v-btn
              icon="mdi-refresh"
              variant="text"
              size="small"
              v-bind="tooltipProps"
              :loading="loading"
              @click="$emit('refresh')"
            />
          </template>
          <span>Refresh enrichment</span>
        </v-tooltip>
      </div>
    </v-card-title>

    <v-divider />

    <!-- Controls -->
    <v-card-text class="pa-3">
      <v-row dense align="center">
        <v-col cols="12" sm="6" md="4">
          <v-select
            :model-value="enrichmentType"
            :items="enrichmentTypeOptions"
            label="Enrichment Type"
            density="compact"
            variant="outlined"
            hide-details
            @update:model-value="$emit('update:enrichmentType', $event)"
          />
        </v-col>

        <v-col v-if="enrichmentType === 'go'" cols="12" sm="6" md="4">
          <v-select
            :model-value="geneSet"
            :items="geneSetOptions"
            label="Gene Set"
            density="compact"
            variant="outlined"
            hide-details
            @update:model-value="$emit('update:geneSet', $event)"
          />
        </v-col>

        <v-col cols="12" sm="6" md="4">
          <v-text-field
            :model-value="fdrThreshold"
            label="FDR Threshold"
            type="number"
            min="0.001"
            max="0.2"
            step="0.01"
            density="compact"
            variant="outlined"
            hide-details
            @update:model-value="$emit('update:fdrThreshold', $event)"
          />
        </v-col>
      </v-row>
    </v-card-text>

    <v-divider />

    <!-- Results Table -->
    <v-card-text class="pa-0">
      <!-- Loading State -->
      <div v-if="loading" class="text-center pa-8">
        <v-progress-circular indeterminate color="primary" size="48" />
        <p class="text-body-2 text-medium-emphasis mt-4">Running enrichment analysis...</p>
      </div>

      <!-- Error State -->
      <div v-else-if="error" class="pa-4">
        <v-alert type="error" variant="outlined">
          <template #title>Enrichment Error</template>
          {{ error }}
        </v-alert>
      </div>

      <!-- Empty State -->
      <div
        v-else-if="!results || results.length === 0"
        class="text-center pa-8 text-medium-emphasis"
      >
        <v-icon icon="mdi-chart-box-outline" size="64" class="mb-4" />
        <p class="text-body-1">No significant enrichment found</p>
        <p class="text-caption">Try adjusting the FDR threshold or cluster selection</p>
      </div>

      <!-- Data Table -->
      <v-data-table
        v-else
        :headers="headers"
        :items="paginatedResults"
        :items-per-page="itemsPerPage"
        :page="page"
        hide-default-footer
        class="enrichment-table"
      >
        <!-- Term Name with tooltip -->
        <template #item.term_name="{ item }">
          <v-tooltip location="bottom" max-width="400">
            <template #activator="{ props: tooltipProps }">
              <span v-bind="tooltipProps" class="term-name">
                {{ truncateTerm(item.term_name) }}
              </span>
            </template>
            <div class="pa-2">
              <strong>{{ item.term_id }}</strong>
              <br />
              {{ item.term_name }}
            </div>
          </v-tooltip>
        </template>

        <!-- P-value with scientific notation -->
        <template #item.p_value="{ item }">
          <span class="text-mono">{{ formatPValue(item.p_value) }}</span>
        </template>

        <!-- FDR with scientific notation -->
        <template #item.fdr="{ item }">
          <v-chip :color="getFdrColor(item.fdr)" size="small" label class="text-mono">
            {{ formatPValue(item.fdr) }}
          </v-chip>
        </template>

        <!-- Enrichment Score with color -->
        <template #item.enrichment_score="{ item }">
          <v-chip :color="getEnrichmentColor(item.enrichment_score)" size="small" label>
            {{ item.enrichment_score.toFixed(2) }}
          </v-chip>
        </template>

        <!-- Odds Ratio -->
        <template #item.odds_ratio="{ item }">
          {{ item.odds_ratio.toFixed(2) }}
        </template>

        <!-- Gene Ratio -->
        <template #item.gene_ratio="{ item }">
          {{ item.gene_count }}/{{ item.cluster_size }}
        </template>

        <!-- Genes with expandable list -->
        <template #item.genes="{ item }">
          <v-chip size="small" variant="outlined" @click="showGenes(item)">
            {{ item.genes.length }} genes
            <v-icon end icon="mdi-chevron-right" size="small" />
          </v-chip>
        </template>
      </v-data-table>
    </v-card-text>

    <!-- Pagination -->
    <v-divider v-if="results && results.length > 0" />
    <v-card-text v-if="results && results.length > 0" class="pa-3">
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

    <!-- Gene List Dialog -->
    <v-dialog v-model="geneDialog" max-width="600">
      <v-card v-if="selectedTerm">
        <v-card-title>
          <h3 class="text-h6">{{ selectedTerm.term_name }}</h3>
          <p class="text-caption text-medium-emphasis mt-1">
            {{ selectedTerm.term_id }}
          </p>
        </v-card-title>
        <v-divider />
        <v-card-text>
          <div class="d-flex flex-wrap ga-2">
            <v-chip
              v-for="gene in selectedTerm.genes"
              :key="gene"
              size="small"
              color="primary"
              variant="outlined"
              @click="$emit('geneClick', gene)"
            >
              {{ gene }}
            </v-chip>
          </div>
        </v-card-text>
        <v-card-actions>
          <v-spacer />
          <v-btn variant="text" @click="geneDialog = false">Close</v-btn>
        </v-card-actions>
      </v-card>
    </v-dialog>
  </v-card>
</template>

<script setup>
import { ref, computed } from 'vue'

// Props
const props = defineProps({
  results: {
    type: Array,
    default: () => []
  },
  loading: {
    type: Boolean,
    default: false
  },
  error: {
    type: String,
    default: null
  },
  enrichmentType: {
    type: String,
    default: 'hpo'
  },
  geneSet: {
    type: String,
    default: 'GO_Biological_Process_2023'
  },
  fdrThreshold: {
    type: Number,
    default: 0.05
  }
})

// Emits
defineEmits([
  'refresh',
  'update:enrichmentType',
  'update:geneSet',
  'update:fdrThreshold',
  'geneClick'
])

// Refs
const page = ref(1)
const itemsPerPage = ref(10)
const geneDialog = ref(false)
const selectedTerm = ref(null)

// Computed
const enrichmentStats = computed(() => {
  if (!props.results || props.results.length === 0) {
    return 'No significant terms'
  }
  return `${props.results.length} significant term(s) at FDR < ${props.fdrThreshold}`
})

const totalPages = computed(() => Math.ceil((props.results?.length || 0) / itemsPerPage.value))

const paginatedResults = computed(() => {
  if (!props.results) return []
  const start = (page.value - 1) * itemsPerPage.value
  const end = start + itemsPerPage.value
  return props.results.slice(start, end)
})

const paginationText = computed(() => {
  if (!props.results || props.results.length === 0) return ''
  const start = (page.value - 1) * itemsPerPage.value + 1
  const end = Math.min(page.value * itemsPerPage.value, props.results.length)
  return `Showing ${start}–${end} of ${props.results.length}`
})

// Options
const enrichmentTypeOptions = [
  { title: 'HPO (Human Phenotype Ontology)', value: 'hpo' },
  { title: 'GO (Gene Ontology)', value: 'go' }
]

const geneSetOptions = [
  { title: 'GO Biological Process', value: 'GO_Biological_Process_2023' },
  { title: 'GO Molecular Function', value: 'GO_Molecular_Function_2023' },
  { title: 'GO Cellular Component', value: 'GO_Cellular_Component_2023' },
  { title: 'KEGG Pathways', value: 'KEGG_2021_Human' },
  { title: 'Reactome Pathways', value: 'Reactome_2022' },
  { title: 'WikiPathways', value: 'WikiPathway_2023_Human' }
]

const itemsPerPageOptions = [10, 20, 50, 100]

const headers = [
  { title: 'Term', key: 'term_name', sortable: true },
  { title: 'P-value', key: 'p_value', sortable: true },
  { title: 'FDR', key: 'fdr', sortable: true },
  { title: 'Enrichment Score', key: 'enrichment_score', sortable: true },
  { title: 'Odds Ratio', key: 'odds_ratio', sortable: true },
  { title: 'Ratio', key: 'gene_ratio', sortable: false },
  { title: 'Genes', key: 'genes', sortable: false }
]

// Methods
const truncateTerm = term => {
  const maxLength = 60
  if (term.length <= maxLength) return term
  return term.substring(0, maxLength) + '...'
}

const formatPValue = value => {
  if (value < 0.0001) return value.toExponential(2)
  if (value < 0.01) return value.toFixed(4)
  return value.toFixed(3)
}

const getFdrColor = fdr => {
  if (fdr < 0.001) return 'success'
  if (fdr < 0.01) return 'info'
  if (fdr < 0.05) return 'warning'
  return 'grey'
}

const getEnrichmentColor = score => {
  if (score >= 5) return 'success'
  if (score >= 3) return 'info'
  if (score >= 1.3) return 'warning'
  return 'grey'
}

const showGenes = term => {
  selectedTerm.value = term
  geneDialog.value = true
}

const exportResults = () => {
  if (!props.results || props.results.length === 0) return

  // Create CSV content
  const headers = [
    'Term ID',
    'Term Name',
    'P-value',
    'FDR',
    'Enrichment Score',
    'Odds Ratio',
    'Gene Count',
    'Cluster Size',
    'Genes'
  ]
  const rows = props.results.map(r => [
    r.term_id,
    r.term_name,
    r.p_value,
    r.fdr,
    r.enrichment_score,
    r.odds_ratio,
    r.gene_count,
    r.cluster_size,
    r.genes.join('; ')
  ])

  const csv = [headers.join(','), ...rows.map(row => row.map(cell => `"${cell}"`).join(','))].join(
    '\n'
  )

  // Download CSV
  const blob = new Blob([csv], { type: 'text/csv' })
  const link = document.createElement('a')
  link.href = URL.createObjectURL(blob)
  link.download = `enrichment_${props.enrichmentType}_${Date.now()}.csv`
  link.click()
}
</script>

<style scoped>
.enrichment-table-card {
  width: 100%;
}

.term-name {
  cursor: help;
}

.text-mono {
  font-family: 'Courier New', monospace;
  font-size: 0.875rem;
}

.enrichment-table :deep(table) {
  table-layout: auto;
}

.enrichment-table :deep(th) {
  white-space: nowrap;
  font-weight: 600;
}
</style>
