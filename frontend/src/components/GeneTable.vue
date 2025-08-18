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
              :disabled="loading"
              title="Export filtered results"
              @click="exportData"
            />
            <v-btn
              icon="mdi-filter-variant"
              variant="outlined"
              :color="hasActiveFilters ? 'primary' : ''"
              title="Advanced filters"
              @click="showAdvancedFilters = !showAdvancedFilters"
            />
            <v-btn
              icon="mdi-refresh"
              variant="outlined"
              :loading="loading"
              title="Refresh data"
              @click="refreshData"
            />
          </div>
        </div>

        <!-- Primary Search -->
        <v-row class="mb-3">
          <v-col cols="12" md="8">
            <v-text-field
              v-model="search"
              prepend-inner-icon="mdi-magnify"
              label="Search genes"
              placeholder="e.g. PKD1, HGNC:9008, polycystic kidney"
              clearable
              hide-details
              variant="outlined"
              density="compact"
              class="search-field"
              @input="debouncedSearch"
            >
            </v-text-field>
          </v-col>
          <v-col cols="12" md="4">
            <v-range-slider
              v-model="scoreRange"
              label="Score Range"
              :min="0"
              :max="100"
              :step="5"
              thumb-label
              hide-details
              color="primary"
              density="compact"
              @end="debouncedSearch"
            >
              <template #prepend>
                <v-chip size="x-small" variant="tonal">
                  {{ scoreRange[0] }}
                </v-chip>
              </template>
              <template #append>
                <v-chip size="x-small" variant="tonal">
                  {{ scoreRange[1] }}
                </v-chip>
              </template>
            </v-range-slider>
          </v-col>
        </v-row>

        <!-- Advanced Filters -->
        <v-expand-transition>
          <div v-if="showAdvancedFilters">
            <v-divider class="mb-3" />
            <v-row>
              <v-col cols="12" md="4">
                <v-select
                  v-model="selectedSources"
                  :items="availableSources"
                  label="Data Sources"
                  multiple
                  chips
                  closable-chips
                  hide-details
                  variant="outlined"
                  density="compact"
                  @update:model-value="debouncedSearch"
                >
                  <template #selection="{ item, index }">
                    <v-chip
                      v-if="index < 2"
                      :color="getSourceColor(item.value)"
                      size="small"
                      variant="tonal"
                    >
                      {{ item.title }}
                    </v-chip>
                    <span v-if="index === 2" class="text-caption text-medium-emphasis">
                      (+{{ selectedSources.length - 2 }} others)
                    </span>
                  </template>
                </v-select>
              </v-col>
              <v-col cols="12" md="4">
                <v-text-field
                  v-model.number="minEvidenceCount"
                  label="Min Evidence Count"
                  type="number"
                  min="0"
                  hide-details
                  variant="outlined"
                  density="compact"
                  clearable
                  @input="debouncedSearch"
                />
              </v-col>
              <v-col cols="12" md="4">
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
            <v-row class="mt-1">
              <v-col cols="12">
                <div class="d-flex align-center ga-2">
                  <v-chip
                    v-if="hasActiveFilters"
                    color="primary"
                    variant="tonal"
                    size="small"
                    prepend-icon="mdi-filter"
                  >
                    {{ activeFilterCount }} active filter{{ activeFilterCount !== 1 ? 's' : '' }}
                  </v-chip>
                  <v-btn
                    v-if="hasActiveFilters"
                    variant="text"
                    size="small"
                    prepend-icon="mdi-close"
                    @click="clearAllFilters"
                  >
                    Clear All
                  </v-btn>
                </div>
              </v-col>
            </v-row>
          </div>
        </v-expand-transition>
      </v-card-text>
    </v-card>

    <!-- Prominent Results Summary -->
    <v-card class="results-summary-card mb-4" elevation="0" rounded="lg">
      <v-card-text class="pa-4">
        <div class="d-flex align-center justify-space-between">
          <!-- Gene Count Display -->
          <div class="d-flex align-center ga-4">
            <div class="gene-count-display">
              <div class="text-h5 font-weight-bold text-primary">
                {{ totalItems.toLocaleString() }}
              </div>
              <div class="text-caption text-medium-emphasis">
                {{ totalItems === 1 ? 'Gene Found' : 'Genes Found' }}
              </div>
            </div>

            <v-divider vertical />

            <div class="page-info">
              <div class="text-body-1 font-weight-medium">
                {{ ((page - 1) * itemsPerPage + 1).toLocaleString() }}–{{
                  Math.min(page * itemsPerPage, totalItems).toLocaleString()
                }}
              </div>
              <div class="text-caption text-medium-emphasis">
                Page {{ page }} of {{ pageCount }}
              </div>
            </div>

            <!-- Active Filter Indicators -->
            <div v-if="hasActiveFilters" class="d-flex align-center ga-2">
              <v-divider vertical />
              <div class="d-flex flex-wrap ga-1">
                <v-chip
                  v-if="search"
                  size="small"
                  variant="tonal"
                  color="primary"
                  prepend-icon="mdi-magnify"
                  closable
                  @click:close="
                    () => {
                      search = ''
                      debouncedSearch()
                    }
                  "
                >
                  "{{ search }}"
                </v-chip>
                <v-chip
                  v-if="scoreRange[0] > 0 || scoreRange[1] < 100"
                  size="small"
                  variant="tonal"
                  color="info"
                  prepend-icon="mdi-chart-line"
                  closable
                  @click:close="
                    () => {
                      scoreRange = [0, 100]
                      debouncedSearch()
                    }
                  "
                >
                  Score: {{ scoreRange[0] }}–{{ scoreRange[1] }}
                </v-chip>
                <v-chip
                  v-if="selectedSources.length > 0"
                  size="small"
                  variant="tonal"
                  color="success"
                  prepend-icon="mdi-database"
                  closable
                  @click:close="
                    () => {
                      selectedSources = []
                      debouncedSearch()
                    }
                  "
                >
                  {{ selectedSources.length }} Source{{ selectedSources.length !== 1 ? 's' : '' }}
                </v-chip>
              </div>
            </div>
          </div>

          <!-- Pagination Controls -->
          <div class="d-flex align-center ga-2">
            <v-select
              v-model="itemsPerPage"
              :items="[10, 25, 50, 100]"
              label="Per page"
              hide-details
              variant="outlined"
              density="compact"
              style="width: 100px"
              @update:model-value="loadGenes"
            />
            <v-pagination
              v-model="page"
              :length="pageCount"
              :total-visible="5"
              size="small"
              density="compact"
              @update:model-value="loadGenes"
            />
          </div>
        </div>
      </v-card-text>
    </v-card>

    <!-- Enhanced Data Table -->
    <v-card rounded="lg" :loading="loading">
      <v-data-table-server
        :headers="headers"
        :items="genes"
        :items-length="totalItems"
        :loading="loading"
        :items-per-page="itemsPerPage"
        :page="page"
        class="gene-table"
        density="compact"
        hover
        :no-data-text="noDataText"
        loading-text="Loading gene data..."
        @update:options="updateOptions"
      >
        <!-- Gene Symbol with Link -->
        <template #[`item.approved_symbol`]="{ item }">
          <div class="d-flex align-center">
            <router-link
              :to="`/genes/${item.approved_symbol}`"
              class="text-decoration-none font-weight-medium gene-link"
            >
              {{ item.approved_symbol }}
            </router-link>
            <v-tooltip v-if="item.alias_symbol?.length" location="bottom">
              <template #activator="{ props }">
                <v-icon
                  icon="mdi-information-outline"
                  size="small"
                  v-bind="props"
                  class="ml-1 text-medium-emphasis"
                />
              </template>
              <div class="pa-2">
                <strong>Aliases:</strong><br />
                {{ item.alias_symbol.join(', ') }}
              </div>
            </v-tooltip>
          </div>
        </template>

        <!-- HGNC ID -->
        <template #[`item.hgnc_id`]="{ item }">
          <code v-if="item.hgnc_id" class="text-caption bg-surface-variant pa-1 rounded">
            {{ item.hgnc_id }}
          </code>
          <v-chip v-else color="grey" variant="tonal" size="x-small"> N/A </v-chip>
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
              style="width: 32px"
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
            <v-chip v-else color="grey" variant="tonal" size="x-small"> N/A </v-chip>
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
              <v-icon :icon="getSourceIcon(source)" size="x-small" start />
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

        <!-- Loading State -->
        <template #loading>
          <v-skeleton-loader
            v-for="n in itemsPerPage"
            :key="n"
            type="table-row"
            class="mx-4 my-2"
          />
        </template>

        <!-- Simplified Bottom -->
        <template #bottom>
          <div class="pa-2 text-center">
            <div class="text-caption text-medium-emphasis">Page {{ page }} of {{ pageCount }}</div>
          </div>
        </template>
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
import { ref, computed, onMounted } from 'vue'
import { geneApi } from '../api/genes'
import ScoreBreakdown from './ScoreBreakdown.vue'

// Data
const genes = ref([])
const loading = ref(false)
const totalItems = ref(0)
const page = ref(1)
const itemsPerPage = ref(10)
const search = ref('')
const scoreRange = ref([0, 100])
const selectedSources = ref([])
const minEvidenceCount = ref(null)
const showAdvancedFilters = ref(false)
const sortOption = ref('score_desc')

// Available options
const availableSources = [
  { title: 'PanelApp', value: 'PanelApp' },
  { title: 'HPO', value: 'HPO' },
  { title: 'PubTator', value: 'PubTator' },
  { title: 'Literature', value: 'Literature' }
]

const sortOptions = [
  { title: 'Score (High to Low)', value: 'score_desc' },
  { title: 'Score (Low to High)', value: 'score_asc' },
  { title: 'Symbol (A-Z)', value: 'symbol_asc' },
  { title: 'Symbol (Z-A)', value: 'symbol_desc' },
  { title: 'Evidence Count (High to Low)', value: 'evidence_desc' },
  { title: 'Recently Updated', value: 'updated_desc' }
]

// Enhanced table headers
const headers = [
  {
    title: 'Gene Symbol',
    key: 'approved_symbol',
    sortable: true,
    width: '140px'
  },
  {
    title: 'HGNC ID',
    key: 'hgnc_id',
    sortable: true,
    width: '120px'
  },
  {
    title: 'Evidence Count',
    key: 'evidence_count',
    sortable: true,
    width: '140px'
  },
  {
    title: 'Evidence Score',
    key: 'evidence_score',
    sortable: true,
    width: '140px',
    align: 'center'
  },
  {
    title: 'Data Sources',
    key: 'sources',
    sortable: false,
    width: '200px'
  }
]

// Computed
const pageCount = computed(() => Math.ceil(totalItems.value / itemsPerPage.value))

const maxEvidenceCount = computed(() => {
  if (genes.value.length === 0) return 4 // fallback to API max
  return Math.max(...genes.value.map(gene => gene.evidence_count || 0))
})

const hasActiveFilters = computed(() => {
  return (
    search.value ||
    scoreRange.value[0] > 0 ||
    scoreRange.value[1] < 100 ||
    selectedSources.value.length > 0 ||
    minEvidenceCount.value
  )
})

const activeFilterCount = computed(() => {
  let count = 0
  if (search.value) count++
  if (scoreRange.value[0] > 0 || scoreRange.value[1] < 100) count++
  if (selectedSources.value.length > 0) count++
  if (minEvidenceCount.value) count++
  return count
})

const noDataText = computed(() => {
  if (hasActiveFilters.value) {
    return 'No genes match your current filters'
  }
  return 'No gene data available'
})

// Methods
const loadGenes = async (sortBy = null, sortDesc = false) => {
  loading.value = true
  try {
    const response = await geneApi.getGenes({
      page: page.value,
      perPage: itemsPerPage.value,
      search: search.value,
      minScore: scoreRange.value[0],
      maxScore: scoreRange.value[1],
      sources: selectedSources.value,
      minEvidenceCount: minEvidenceCount.value,
      sortBy: sortBy,
      sortDesc: sortDesc
    })
    genes.value = response.items
    totalItems.value = response.total
  } catch (error) {
    console.error('Error loading genes:', error)
    genes.value = []
    totalItems.value = 0
  } finally {
    loading.value = false
  }
}

const updateOptions = options => {
  page.value = options.page
  itemsPerPage.value = options.itemsPerPage

  // Handle sorting
  if (options.sortBy && options.sortBy.length > 0) {
    const sortField = options.sortBy[0].key
    const sortOrder = options.sortBy[0].order === 'desc'
    loadGenes(sortField, sortOrder)
  } else {
    loadGenes()
  }
}

const applySorting = () => {
  const [field, order] = sortOption.value.split('_')
  loadGenes(field, order === 'desc')
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
  scoreRange.value = [0, 100]
  selectedSources.value = []
  minEvidenceCount.value = null
  sortOption.value = 'score_desc'
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

// Color and icon methods
const getSourceColor = source => {
  const colors = {
    PanelApp: 'primary',
    HPO: 'secondary',
    PubTator: 'info',
    Literature: 'success'
  }
  return colors[source] || 'grey'
}

const getSourceIcon = source => {
  const icons = {
    PanelApp: 'mdi-view-dashboard',
    HPO: 'mdi-human',
    PubTator: 'mdi-file-document',
    Literature: 'mdi-book-open'
  }
  return icons[source] || 'mdi-database'
}

// Removed unused score functions - these are now handled by ScoreBreakdown component

const getEvidenceCountColor = count => {
  if (count >= 10) return 'success'
  if (count >= 5) return 'info'
  if (count >= 2) return 'warning'
  return 'error'
}

const getEvidenceStrength = count => {
  const max = maxEvidenceCount.value
  return max > 0 ? Math.min((count / max) * 100, 100) : 0
}

// Action methods
// Removed unused function - will implement later

// Removed unused function - will implement later

// Removed unused function - will implement later

// Lifecycle
onMounted(() => {
  loadGenes()
})
</script>

<style scoped>
/* Search & Filter Card */
.search-card {
  border: 1px solid rgb(var(--v-theme-surface-variant));
  background: rgb(var(--v-theme-surface));
  transition: all 0.3s cubic-bezier(0.4, 0, 0.2, 1);
}

.search-card:hover {
  box-shadow: 0 2px 8px rgba(var(--v-theme-shadow-key-penumbra-opacity));
}

.search-field :deep(.v-field__input) {
  font-size: 1rem;
}

/* Results Summary Card */
.results-summary-card {
  border: 1px solid rgb(var(--v-theme-surface-variant));
  background: rgb(var(--v-theme-surface));
  transition: all 0.3s cubic-bezier(0.4, 0, 0.2, 1);
}

.gene-count-display {
  text-align: center;
  min-width: 80px;
}

.page-info {
  text-align: center;
  min-width: 100px;
}

/* Data Table Styling */
.gene-table :deep(.v-data-table__th) {
  font-weight: 600;
  background: rgb(var(--v-theme-surface-light));
  border-bottom: 2px solid rgb(var(--v-theme-surface-variant));
  padding: 12px 16px;
  height: 56px;
}

.gene-table :deep(.v-data-table__td) {
  border-bottom: 1px solid rgb(var(--v-theme-surface-variant));
  padding: 8px 12px;
  height: 48px;
  vertical-align: middle;
}

.gene-table :deep(.v-data-table__tr:hover) {
  background: rgb(var(--v-theme-primary-lighten-3)) !important;
  transition: background-color 0.2s ease;
}

/* Gene Link Styling */
.gene-link {
  color: rgb(var(--v-theme-primary));
  transition: all 0.2s ease;
  font-weight: 500;
}

.gene-link:hover {
  color: rgb(var(--v-theme-primary-darken-1));
  text-decoration: underline;
  transform: translateX(2px);
}

/* Dark Theme Adjustments */
.v-theme--dark .search-card,
.v-theme--dark .results-summary-card {
  background: rgb(var(--v-theme-surface-bright));
  border-color: rgba(var(--v-theme-on-surface), 0.12);
}

.v-theme--dark .gene-table :deep(.v-data-table__th) {
  background: rgb(var(--v-theme-surface-variant));
}

/* Responsive Adjustments */
@media (max-width: 768px) {
  .results-summary-card .d-flex {
    flex-direction: column;
    gap: 16px;
  }

  .gene-count-display,
  .page-info {
    text-align: center;
  }
}

/* Component Sizing System - Following Style Guide */
.gene-table :deep(.v-chip) {
  font-variant-numeric: tabular-nums;
}

.gene-table :deep(.v-progress-linear) {
  border-radius: 2px;
}

/* Smooth Transitions */
* {
  transition:
    color 0.2s ease,
    background-color 0.2s ease;
}

/* Focus States */
.gene-table :deep(.v-btn:focus-visible),
.search-card :deep(.v-field:focus-within) {
  outline: 2px solid rgb(var(--v-theme-primary));
  outline-offset: 2px;
}
</style>
