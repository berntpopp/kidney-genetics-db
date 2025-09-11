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
        :items-per-page="itemsPerPage"
        :page="page"
        :sort-by="sortBy"
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
        @update:options="handleTableUpdate"
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
import { useRoute, useRouter } from 'vue-router'
import { geneApi } from '../api/genes'
import ScoreBreakdown from './ScoreBreakdown.vue'

const route = useRoute()
const router = useRouter()

// Data
const genes = ref([])
const loading = ref(false)
const totalItems = ref(0)
const page = ref(1)
const itemsPerPage = ref(10)
const search = ref('')
const evidenceScoreRange = ref([0, 100])
const selectedSources = ref([])
const evidenceCountRange = ref([0, 7]) // Initialize with a sensible default
const sortOption = ref('score_desc')
const filterMeta = ref(null)
const sortBy = ref([{ key: 'evidence_score', order: 'desc' }])

// Track initialization to prevent circular updates
const isInitializing = ref(true)
const isNavigating = ref(false)

// Options
const itemsPerPageOptions = [
  { value: 5, title: '5' },
  { value: 10, title: '10' },
  { value: 20, title: '20' },
  { value: 50, title: '50' },
  { value: 100, title: '100' }
]

// Dynamic sources list - will be populated from API
const availableSources = ref([])

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

// Parse URL parameters and apply to component state
const parseUrlParams = () => {
  const query = route.query

  if (query.page) {
    const parsedPage = parseInt(query.page)
    if (!isNaN(parsedPage) && parsedPage > 0) {
      page.value = parsedPage
    }
  }

  if (query.per_page) {
    const parsedPerPage = parseInt(query.per_page)
    if (!isNaN(parsedPerPage) && itemsPerPageOptions.some(opt => opt.value === parsedPerPage)) {
      itemsPerPage.value = parsedPerPage
    }
  }

  if (query.search) {
    search.value = query.search
  }

  if (query.sort_by && query.sort_order) {
    sortBy.value = [{ key: query.sort_by, order: query.sort_order }]
    // Update sortOption for dropdown
    const sortMap = {
      evidence_score_desc: 'score_desc',
      evidence_score_asc: 'score_asc',
      approved_symbol_asc: 'symbol_asc',
      approved_symbol_desc: 'symbol_desc',
      evidence_count_desc: 'count_desc',
      evidence_count_asc: 'count_asc'
    }
    sortOption.value = sortMap[`${query.sort_by}_${query.sort_order}`] || 'score_desc'
  }

  if (query.min_score) {
    evidenceScoreRange.value[0] = parseInt(query.min_score) || 0
  }
  if (query.max_score) {
    evidenceScoreRange.value[1] = parseInt(query.max_score) || 100
  }

  if (query.min_count) {
    evidenceCountRange.value[0] = parseInt(query.min_count) || 0
  }
  if (query.max_count) {
    evidenceCountRange.value[1] = parseInt(query.max_count) || 7
  }

  if (query.source) {
    selectedSources.value = [query.source]
  }
}

// Update URL with current state
const updateUrl = () => {
  if (isInitializing.value) return

  const query = {}

  if (page.value !== 1) query.page = page.value
  if (itemsPerPage.value !== 10) query.per_page = itemsPerPage.value
  if (search.value) query.search = search.value

  if (sortBy.value.length > 0) {
    query.sort_by = sortBy.value[0].key
    query.sort_order = sortBy.value[0].order
  }

  if (evidenceScoreRange.value[0] > 0) query.min_score = evidenceScoreRange.value[0]
  if (evidenceScoreRange.value[1] < 100) query.max_score = evidenceScoreRange.value[1]
  if (evidenceCountRange.value[0] > 0) query.min_count = evidenceCountRange.value[0]
  if (evidenceCountRange.value[1] < 7) query.max_count = evidenceCountRange.value[1]
  if (selectedSources.value.length > 0) query.source = selectedSources.value[0]

  router.replace({ query })
}

// Handle table update events
const handleTableUpdate = options => {
  // During initialization or navigation, ignore the table's events
  if (isInitializing.value || isNavigating.value) {
    return
  }

  // Update our local state from the table options
  let needsReload = false

  if (options.page !== undefined && options.page !== page.value) {
    page.value = options.page
    needsReload = true
  }

  if (options.itemsPerPage !== undefined && options.itemsPerPage !== itemsPerPage.value) {
    itemsPerPage.value = options.itemsPerPage
    page.value = 1 // Reset to first page when changing items per page
    needsReload = true
  }

  if (
    options.sortBy?.length > 0 &&
    JSON.stringify(options.sortBy) !== JSON.stringify(sortBy.value)
  ) {
    sortBy.value = options.sortBy
    needsReload = true
  }

  if (needsReload) {
    // Update URL with the new state
    updateUrl()
    // Load data with the new options
    loadGenes()
  }
}

// Methods
const loadGenes = async () => {
  // Prevent duplicate loading
  if (loading.value) return

  loading.value = true
  try {
    // Parse sorting for API - always use current state values
    let sortByField = sortBy.value?.[0]?.key || 'evidence_score'
    let sortDesc = sortBy.value?.[0]?.order === 'desc'
    const response = await geneApi.getGenes({
      page: page.value,
      perPage: itemsPerPage.value,
      search: search.value,
      minScore: evidenceScoreRange.value[0],
      maxScore: evidenceScoreRange.value[1],
      minCount: evidenceCountRange.value[0],
      maxCount:
        evidenceCountRange.value[1] < (filterMeta.value?.evidence_count?.max || 7)
          ? evidenceCountRange.value[1]
          : null,
      source: selectedSources.value.length > 0 ? selectedSources.value[0] : null,
      sortBy: sortByField,
      sortDesc: sortDesc
    })

    genes.value = response.items
    totalItems.value = response.total

    // Store filter metadata for dynamic ranges
    if (response.meta && response.meta.filters) {
      filterMeta.value = response.meta.filters

      // Update available sources dynamically from API metadata
      if (response.meta.filters.available_sources) {
        availableSources.value = response.meta.filters.available_sources.map(source => ({
          title: source,
          value: source
        }))
      }

      // Update the evidence count range max only on first load
      // Check if we haven't set filterMeta yet (first load)
      if (response.meta.filters.evidence_count?.max && !filterMeta.value) {
        evidenceCountRange.value = [0, response.meta.filters.evidence_count.max]
      }
    }
  } catch (error) {
    window.logService.error('Error loading genes:', error)
    genes.value = []
    totalItems.value = 0
  } finally {
    loading.value = false
  }
}

// Event handlers
const updatePage = newPage => {
  page.value = newPage
  updateUrl()
  loadGenes()
}

const updateItemsPerPage = newValue => {
  itemsPerPage.value = newValue
  page.value = 1 // Reset to first page
  updateUrl()
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
  updateUrl()
  loadGenes()
}

let searchTimeout
const debouncedSearch = () => {
  clearTimeout(searchTimeout)
  searchTimeout = setTimeout(() => {
    page.value = 1
    updateUrl()
    loadGenes()
  }, 300)
}

const clearAllFilters = () => {
  search.value = ''
  evidenceScoreRange.value = [0, 100]
  evidenceCountRange.value = [0, filterMeta.value?.evidence_count?.max || 7]
  selectedSources.value = []
  sortOption.value = 'score_desc'
  sortBy.value = [{ key: 'evidence_score', order: 'desc' }]
  page.value = 1
  updateUrl()
  loadGenes()
}

const refreshData = () => {
  loadGenes()
}

const exportData = () => {
  // TODO: Implement export functionality
  window.logService.info('Export functionality to be implemented')
}

// Color and helper methods
const getSourceColor = source => {
  const colors = {
    PanelApp: 'primary',
    HPO: 'secondary',
    PubTator: 'info',
    ClinGen: 'success',
    GenCC: 'warning',
    DiagnosticPanels: 'error',
    Literature: 'purple'
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

// Watch for route changes - this handles when the component is kept alive
// and the route changes (e.g., query parameter changes on the same page)
watch(
  () => route.query,
  (newQuery, oldQuery) => {
    // Only react if we're not initializing and the query actually changed
    if (!isInitializing.value && JSON.stringify(newQuery) !== JSON.stringify(oldQuery)) {
      isNavigating.value = true
      parseUrlParams()
      loadGenes().then(() => {
        setTimeout(() => {
          isNavigating.value = false
        }, 100)
      })
    }
  },
  { deep: true }
)

// Lifecycle - Parse URL and load data on mount
// This runs when component is created (including when navigating back)
onMounted(async () => {
  // Reset initialization flag on mount
  isInitializing.value = true

  // Parse URL parameters first
  parseUrlParams()

  // Load the data with parsed parameters
  await loadGenes()

  // Wait for the data table to stabilize
  await new Promise(resolve => setTimeout(resolve, 100))

  // Mark initialization as complete
  isInitializing.value = false
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
