<template>
  <div>
    <!-- Enhanced Search and Filter Bar -->
    <v-card elevation="0" class="search-card mb-4" rounded="lg">
      <v-card-text class="pa-4">
        <div class="d-flex align-center justify-space-between mb-3">
          <div>
            <h2 class="text-h6 font-weight-medium mb-1">Search & Filter</h2>
            <p class="text-caption text-medium-emphasis">
              Explore {{ totalItems.toLocaleString() }} curated kidney disease genes
            </p>
          </div>
          <div class="d-flex ga-2">
            <v-btn
              icon="mdi-download"
              variant="outlined"
              size="small"
              :disabled="loading"
              title="Export filtered results"
              @click="exportData"
            />
            <v-btn
              icon="mdi-filter-remove"
              variant="outlined"
              size="small"
              :color="hasActiveFilters ? 'warning' : ''"
              :disabled="!hasActiveFilters"
              title="Clear all filters"
              @click="clearAllFilters"
            />
            <v-btn
              icon="mdi-refresh"
              variant="outlined"
              size="small"
              :loading="loading"
              title="Refresh data"
              @click="refreshData"
            />
          </div>
        </div>

        <!-- Compact Filters Row -->
        <v-row align="center" class="mb-2">
          <!-- Search -->
          <v-col cols="12" lg="4">
            <v-text-field
              v-model="search"
              prepend-inner-icon="mdi-magnify"
              label="Search"
              placeholder="PKD1, HGNC:9008..."
              clearable
              hide-details
              variant="outlined"
              density="compact"
              single-line
              @update:model-value="debouncedSearch"
            />
          </v-col>
          
          <!-- Data Sources -->
          <v-col cols="12" lg="4">
            <v-select
              v-model="selectedSources"
              :items="availableSources"
              label="Sources"
              multiple
              chips
              closable-chips
              hide-details
              variant="outlined"
              density="compact"
              @update:model-value="debouncedSearch"
            />
          </v-col>
          
          <!-- Sort -->
          <v-col cols="12" lg="4">
            <v-select
              v-model="sortOption"
              :items="sortOptions"
              label="Sort by"
              hide-details
              variant="outlined"
              density="compact"
              @update:model-value="applySorting"
            />
          </v-col>
        </v-row>
        
        <!-- Range Sliders Row -->
        <v-row align="center" class="mb-2">
          <v-col cols="12" md="6">
            <div class="d-flex align-center ga-2">
              <span class="text-caption font-weight-medium" style="min-width: 90px">Score:</span>
              <v-chip size="x-small" variant="tonal">{{ evidenceScoreRange[0] }}</v-chip>
              <v-range-slider
                v-model="evidenceScoreRange"
                :min="0"
                :max="100"
                :step="1"
                hide-details
                color="primary"
                density="compact"
                class="flex-grow-1 mx-2"
                @update:model-value="debouncedSearch"
              />
              <v-chip size="x-small" variant="tonal">{{ evidenceScoreRange[1] }}</v-chip>
            </div>
          </v-col>
          
          <v-col cols="12" md="6">
            <div class="d-flex align-center ga-2">
              <span class="text-caption font-weight-medium" style="min-width: 90px">Count:</span>
              <v-chip size="x-small" variant="tonal">{{ evidenceCountRange[0] }}</v-chip>
              <v-range-slider
                v-model="evidenceCountRange"
                :min="0"
                :max="filterMeta?.evidence_count?.max || 6"
                :step="1"
                hide-details
                color="secondary"
                density="compact"
                class="flex-grow-1 mx-2"
                @update:model-value="debouncedSearch"
              />
              <v-chip size="x-small" variant="tonal">{{ evidenceCountRange[1] }}</v-chip>
            </div>
          </v-col>
        </v-row>

      </v-card-text>
    </v-card>

    <!-- Top Pagination Controls (per Style Guide) -->
    <v-card elevation="0" class="mb-2" rounded="lg">
      <v-card-text class="pa-3">
        <div class="d-flex align-center justify-space-between">
          <div class="d-flex align-center ga-4">
            <div class="text-body-2">
              <span class="font-weight-medium">{{ totalItems.toLocaleString() }}</span>
              <span class="text-medium-emphasis"> Genes Found</span>
            </div>
            <v-divider vertical />
            <div class="text-body-2 text-medium-emphasis">
              {{ pageRangeText }}
            </div>
          </div>
          <div class="d-flex align-center ga-2">
            <span class="text-caption text-medium-emphasis mr-2">Per page:</span>
            <v-select
              v-model="itemsPerPage"
              :items="itemsPerPageOptions"
              density="compact"
              variant="outlined"
              hide-details
              style="width: 100px"
              @update:model-value="updateItemsPerPage"
            />
            <v-pagination
              v-model="page"
              :length="pageCount"
              :total-visible="5"
              density="compact"
              @update:model-value="updatePage"
            />
          </div>
        </div>
      </v-card-text>
    </v-card>

    <!-- Data Table -->
    <v-card rounded="lg">
      <v-data-table-server
        v-model:items-per-page="itemsPerPage"
        v-model:page="page"
        v-model:sort-by="sortBy"
        :headers="headers"
        :items="genes"
        :items-length="totalItems"
        :loading="loading"
        :items-per-page-options="itemsPerPageOptions"
        density="compact"
        :hover="true"
        :show-select="false"
        :must-sort="true"
        :no-data-text="noDataText"
        @update:options="loadGenes"
      >
        <!-- Gene Symbol with Link -->
        <template #[`item.approved_symbol`]="{ item }">
          <div class="d-flex align-center">
            <router-link
              :to="`/genes/${item.approved_symbol}`"
              class="gene-symbol text-primary text-decoration-none font-weight-medium"
            >
              {{ item.approved_symbol }}
            </router-link>
            <v-tooltip v-if="item.aliases?.length" location="bottom">
              <template #activator="{ props }">
                <v-icon
                  icon="mdi-information-outline"
                  size="x-small"
                  v-bind="props"
                  class="ml-1 text-medium-emphasis"
                />
              </template>
              <div class="pa-2">
                <strong>Aliases:</strong><br />
                {{ item.aliases.join(', ') }}
              </div>
            </v-tooltip>
          </div>
        </template>

        <!-- HGNC ID -->
        <template #[`item.hgnc_id`]="{ item }">
          <code v-if="item.hgnc_id" class="text-caption bg-surface-variant pa-1 rounded">
            {{ item.hgnc_id }}
          </code>
          <v-chip v-else color="grey" variant="tonal" size="x-small">N/A</v-chip>
        </template>

        <!-- Evidence Count with Visual Indicator -->
        <template #[`item.evidence_count`]="{ item }">
          <div class="d-flex align-center">
            <v-chip
              :color="getEvidenceCountColor(item.evidence_count)"
              size="x-small"
              variant="tonal"
              class="font-weight-medium"
            >
              {{ item.evidence_count }}
            </v-chip>
            <v-progress-linear
              :model-value="getEvidenceStrength(item.evidence_count)"
              :color="getEvidenceCountColor(item.evidence_count)"
              height="2"
              class="ml-2"
              style="width: 40px"
            />
          </div>
        </template>

        <!-- Enhanced Evidence Score with Breakdown -->
        <template #[`item.evidence_score`]="{ item }">
          <div class="text-center">
            <ScoreBreakdown
              v-if="item.evidence_score !== null && item.evidence_score !== undefined"
              :score="item.evidence_score"
              :breakdown="item.score_breakdown"
              variant="inline"
              size="small"
            />
            <v-chip v-else color="grey" variant="tonal" size="x-small">N/A</v-chip>
          </div>
        </template>

        <!-- Enhanced Sources -->
        <template #[`item.sources`]="{ item }">
          <div class="d-flex flex-wrap ga-1">
            <v-chip
              v-for="source in item.sources?.slice(0, 3)"
              :key="source"
              size="x-small"
              :color="getSourceColor(source)"
              variant="tonal"
              class="font-weight-medium"
            >
              {{ source }}
            </v-chip>
            <v-menu v-if="item.sources?.length > 3" location="bottom">
              <template #activator="{ props }">
                <v-chip size="x-small" variant="outlined" v-bind="props">
                  +{{ item.sources.length - 3 }}
                </v-chip>
              </template>
              <v-list density="compact">
                <v-list-item v-for="source in item.sources.slice(3)" :key="source">
                  <v-chip size="x-small" :color="getSourceColor(source)" variant="tonal">
                    {{ source }}
                  </v-chip>
                </v-list-item>
              </v-list>
            </v-menu>
          </div>
        </template>

        <!-- No bottom slot - pagination is at the top per style guide -->
        <template #bottom></template>
      </v-data-table-server>
    </v-card>

    <!-- Empty State -->
    <v-card v-if="!loading && genes.length === 0" class="text-center pa-12" rounded="lg">
      <v-icon icon="mdi-database-search" size="x-large" class="mb-4 text-medium-emphasis" />
      <h3 class="text-h6 mb-2">No genes found</h3>
      <p class="text-body-2 text-medium-emphasis mb-4">
        {{ search ? `No results for "${search}"` : 'Try adjusting your filters' }}
      </p>
      <v-btn v-if="hasActiveFilters" color="primary" variant="outlined" @click="clearAllFilters">
        Clear Filters
      </v-btn>
    </v-card>
  </div>
</template>

<script setup>
import { ref, computed, onMounted, watch } from 'vue'
import { geneApi } from '../api/genes'
import ScoreBreakdown from './ScoreBreakdown.vue'

// Data
const genes = ref([])
const loading = ref(false)
const totalItems = ref(0)
const page = ref(1)
const itemsPerPage = ref(10)
const search = ref('')
const evidenceScoreRange = ref([0, 100])
const selectedSources = ref([])
const evidenceCountRange = ref([0, 6])
const sortOption = ref('score_desc')
const filterMeta = ref(null)
const sortBy = ref([{ key: 'evidence_score', order: 'desc' }])

// Options
const itemsPerPageOptions = [
  { value: 10, title: '10' },
  { value: 20, title: '20' },
  { value: 50, title: '50' },
  { value: 100, title: '100' }
]

const availableSources = [
  { title: 'ClinGen', value: 'ClinGen' },
  { title: 'PanelApp', value: 'PanelApp' },
  { title: 'GenCC', value: 'GenCC' },
  { title: 'HPO', value: 'HPO' },
  { title: 'DiagnosticPanels', value: 'DiagnosticPanels' },
  { title: 'PubTator', value: 'PubTator' }
]


const sortOptions = [
  { title: 'Evidence Score (High to Low)', value: 'score_desc' },
  { title: 'Evidence Score (Low to High)', value: 'score_asc' },
  { title: 'Gene Symbol (A-Z)', value: 'symbol_asc' },
  { title: 'Gene Symbol (Z-A)', value: 'symbol_desc' },
  { title: 'Evidence Count (High to Low)', value: 'count_desc' },
  { title: 'Evidence Count (Low to High)', value: 'count_asc' }
]

const headers = [
  { title: 'Gene Symbol', key: 'approved_symbol', sortable: true },
  { title: 'HGNC ID', key: 'hgnc_id', sortable: true },
  { title: 'Evidence Count', key: 'evidence_count', sortable: true },
  { title: 'Evidence Score', key: 'evidence_score', sortable: true },
  { title: 'Data Sources', key: 'sources', sortable: false }
]

// Computed
const pageCount = computed(() => Math.ceil(totalItems.value / itemsPerPage.value))

const pageRangeText = computed(() => {
  if (totalItems.value === 0) return 'No results'
  const start = (page.value - 1) * itemsPerPage.value + 1
  const end = Math.min(page.value * itemsPerPage.value, totalItems.value)
  return `Showing ${start}–${end} of ${totalItems.value}`
})


const hasActiveFilters = computed(() => {
  return (
    search.value ||
    evidenceScoreRange.value[0] > 0 ||
    evidenceScoreRange.value[1] < 100 ||
    evidenceCountRange.value[0] > 0 ||
    evidenceCountRange.value[1] < (filterMeta.value?.evidence_count?.max || 6) ||
    selectedSources.value.length > 0
  )
})



const noDataText = computed(() => {
  if (hasActiveFilters.value) {
    return 'No genes match your current filters'
  }
  return 'No gene data available'
})

// Methods
const loadGenes = async (options = {}) => {
  // Prevent duplicate loading
  if (loading.value) return
  
  loading.value = true
  try {
    // Update pagination from options if provided
    if (options.page) page.value = options.page
    if (options.itemsPerPage) itemsPerPage.value = options.itemsPerPage
    
    // Parse sorting from options
    let sortByField = null
    let sortDesc = false
    
    if (options.sortBy?.length > 0) {
      sortByField = options.sortBy[0].key
      sortDesc = options.sortBy[0].order === 'desc'
      sortBy.value = options.sortBy
    }
    
    const response = await geneApi.getGenes({
      page: page.value,
      perPage: itemsPerPage.value,
      search: search.value,
      minScore: evidenceScoreRange.value[0],
      maxScore: evidenceScoreRange.value[1],
      minCount: evidenceCountRange.value[0] > 0 ? evidenceCountRange.value[0] : null,
      maxCount: evidenceCountRange.value[1] < (filterMeta.value?.evidence_count?.max || 6) ? evidenceCountRange.value[1] : null,
      source: selectedSources.value.length > 0 ? selectedSources.value[0] : null,
      sortBy: sortByField,
      sortDesc: sortDesc
    })
    
    genes.value = response.items
    totalItems.value = response.total
    
    // Store filter metadata for dynamic ranges
    if (response.meta && response.meta.filters) {
      filterMeta.value = response.meta.filters
    }
  } catch (error) {
    console.error('Error loading genes:', error)
    genes.value = []
    totalItems.value = 0
  } finally {
    loading.value = false
  }
}

// Event handlers
const updatePage = (newPage) => {
  page.value = newPage
  loadGenes()
}

const updateItemsPerPage = (newValue) => {
  itemsPerPage.value = newValue
  page.value = 1 // Reset to first page
  loadGenes()
}

const applySorting = () => {
  const [field, order] = sortOption.value.split('_')
  const fieldMap = {
    score: 'evidence_score',
    symbol: 'approved_symbol',
    count: 'evidence_count'
  }
  sortBy.value = [{ key: fieldMap[field], order }]
  loadGenes({ sortBy: sortBy.value })
}

let searchTimeout
const debouncedSearch = () => {
  clearTimeout(searchTimeout)
  searchTimeout = setTimeout(() => {
    page.value = 1
    loadGenes()
  }, 300)
}


const clearAllFilters = () => {
  search.value = ''
  evidenceScoreRange.value = [0, 100]
  evidenceCountRange.value = [0, filterMeta.value?.evidence_count?.max || 6]
  selectedSources.value = []
  sortOption.value = 'score_desc'
  sortBy.value = [{ key: 'evidence_score', order: 'desc' }]
  page.value = 1
  loadGenes()
}


const refreshData = () => {
  loadGenes()
}

const exportData = () => {
  // TODO: Implement export functionality
  console.log('Export functionality to be implemented')
}

// Color and helper methods
const getSourceColor = source => {
  const colors = {
    PanelApp: 'primary',
    HPO: 'secondary',
    PubTator: 'info',
    ClinGen: 'success',
    GenCC: 'warning',
    DiagnosticPanels: 'error'
  }
  return colors[source] || 'grey'
}

const getEvidenceCountColor = count => {
  if (count >= 5) return 'success'
  if (count >= 3) return 'info'
  if (count >= 2) return 'warning'
  return 'error'
}

const getEvidenceStrength = count => {
  const max = filterMeta.value?.evidence_count?.max || 6
  return max > 0 ? Math.min((count / max) * 100, 100) : 0
}

const maxEvidenceCount = computed(() => filterMeta.value?.evidence_count?.max || 6)

// Lifecycle - Only load once on mount
onMounted(() => {
  loadGenes()
})
</script>

<style scoped>
.search-card {
  border: 1px solid rgba(var(--v-border-color), 0.12);
}

.search-field :deep(.v-field__input) {
  font-size: 0.95rem;
}

.gene-symbol {
  font-weight: 500;
}

.gene-symbol:hover {
  text-decoration: underline !important;
}

/* Compact data table styling per style guide */
:deep(.v-data-table) {
  font-size: 0.875rem;
}

:deep(.v-data-table-header__content) {
  font-weight: 600;
  font-size: 0.8125rem;
  text-transform: uppercase;
  letter-spacing: 0.05em;
}

:deep(.v-data-table__tr) {
  height: 48px !important;
}

:deep(.v-data-table__td) {
  padding: 8px 12px !important;
}

/* Ensure proper alignment in compact mode */
:deep(.v-chip--size-x-small) {
  height: 20px;
  font-size: 0.625rem;
}

/* Pagination styling */
:deep(.v-pagination__item) {
  min-width: 32px;
  height: 32px;
  font-size: 0.875rem;
}
</style>