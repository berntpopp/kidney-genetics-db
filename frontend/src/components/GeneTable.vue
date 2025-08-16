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
              @click="exportData"
              :disabled="loading"
              title="Export filtered results"
            />
            <v-btn
              icon="mdi-filter-variant"
              variant="outlined"
              :color="hasActiveFilters ? 'primary' : ''"
              @click="showAdvancedFilters = !showAdvancedFilters"
              title="Advanced filters"
            />
            <v-btn
              icon="mdi-refresh"
              variant="outlined"
              @click="refreshData"
              :loading="loading"
              title="Refresh data"
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
              @input="debouncedSearch"
              class="search-field"
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
              @end="debouncedSearch"
              color="primary"
              density="compact"
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
                    <span
                      v-if="index === 2"
                      class="text-caption text-medium-emphasis"
                    >
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
                  @input="debouncedSearch"
                  clearable
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
                <div class="d-flex justify-space-between align-center">
                  <div class="d-flex ga-2">
                    <v-chip
                      v-if="hasActiveFilters"
                      color="primary"
                      variant="tonal"
                      size="x-small"
                      prepend-icon="mdi-filter"
                    >
                      {{ activeFilterCount }} active
                    </v-chip>
                    <v-btn
                      v-if="hasActiveFilters"
                      variant="text"
                      size="x-small"
                      @click="clearAllFilters"
                    >
                      Clear
                    </v-btn>
                  </div>
                  <v-select
                    v-model="itemsPerPage"
                    :items="[10, 25, 50, 100]"
                    label="Per page"
                    hide-details
                    variant="outlined"
                    density="compact"
                    style="width: 100px;"
                    @update:model-value="loadGenes"
                  />
                </div>
              </v-col>
            </v-row>
          </div>
        </v-expand-transition>
      </v-card-text>
    </v-card>

    <!-- Results Summary with Pagination -->
    <div class="d-flex align-center justify-space-between mb-3">
      <div class="d-flex align-center ga-3">
        <div class="text-body-2 text-medium-emphasis">
          <span v-if="!loading">
            {{ ((page - 1) * itemsPerPage + 1).toLocaleString() }}–{{ 
              Math.min(page * itemsPerPage, totalItems).toLocaleString() 
            }} of {{ totalItems.toLocaleString() }}
          </span>
          <span v-else>Loading...</span>
        </div>
        <div class="d-flex ga-1">
          <v-chip
            v-if="search"
            size="x-small"
            variant="tonal"
            prepend-icon="mdi-magnify"
          >
            "{{ search }}"
          </v-chip>
          <v-chip
            v-if="scoreRange[0] > 0 || scoreRange[1] < 100"
            size="x-small"
            variant="tonal"
            prepend-icon="mdi-chart-line"
          >
            {{ scoreRange[0] }}–{{ scoreRange[1] }}
          </v-chip>
        </div>
      </div>
      
      <!-- Top Pagination Controls -->
      <div class="d-flex align-center ga-2">
        <v-select
          v-model="itemsPerPage"
          :items="[10, 25, 50, 100]"
          label="Per page"
          hide-details
          variant="outlined"
          density="compact"
          style="width: 100px;"
          @update:model-value="loadGenes"
        />
        <v-pagination
          v-model="page"
          :length="pageCount"
          :total-visible="5"
          size="small"
          @update:model-value="loadGenes"
          density="compact"
        />
      </div>
    </div>

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
        @update:options="updateOptions"
        :no-data-text="noDataText"
        loading-text="Loading gene data..."
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
                <strong>Aliases:</strong><br>
                {{ item.alias_symbol.join(', ') }}
              </div>
            </v-tooltip>
          </div>
        </template>

        <!-- HGNC ID -->
        <template #[`item.hgnc_id`]="{ item }">
          <code class="text-caption bg-surface-variant pa-1 rounded">
            {{ item.hgnc_id }}
          </code>
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
              style="width: 32px;"
            />
          </div>
        </template>

        <!-- Enhanced Evidence Score -->
        <template #[`item.evidence_score`]="{ item }">
          <div v-if="item.evidence_score !== null && item.evidence_score !== undefined" class="text-center">
            <v-tooltip location="bottom">
              <template #activator="{ props }">
                <v-chip
                  :color="getScoreColor(item.evidence_score)"
                  variant="flat"
                  size="small"
                  class="font-weight-medium"
                  v-bind="props"
                >
                  <v-icon 
                    :icon="getScoreIcon(item.evidence_score)" 
                    size="small" 
                    start 
                  />
                  {{ item.evidence_score.toFixed(1) }}
                </v-chip>
              </template>
              <div class="pa-2">
                <strong>Classification:</strong> {{ getScoreLabel(item.evidence_score) }}<br>
                <span class="text-caption">
                  Evidence strength based on curated data sources
                </span>
              </div>
            </v-tooltip>
          </div>
          <div v-else class="text-center">
            <v-chip color="grey" variant="tonal" size="x-small">
              N/A
            </v-chip>
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
              <v-icon 
                :icon="getSourceIcon(source)" 
                size="x-small" 
                start 
              />
              {{ source }}
            </v-chip>
            <v-menu v-if="item.sources?.length > 3" location="bottom">
              <template #activator="{ props }">
                <v-chip
                  size="x-small"
                  variant="outlined"
                  v-bind="props"
                >
                  +{{ item.sources.length - 3 }}
                </v-chip>
              </template>
              <v-list density="compact">
                <v-list-item
                  v-for="source in item.sources.slice(3)"
                  :key="source"
                >
                  <v-chip
                    size="x-small"
                    :color="getSourceColor(source)"
                    variant="tonal"
                  >
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
            <div class="text-caption text-medium-emphasis">
              Page {{ page }} of {{ pageCount }}
            </div>
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
      <v-btn
        v-if="hasActiveFilters"
        color="primary"
        variant="outlined"
        @click="clearAllFilters"
      >
        Clear Filters
      </v-btn>
    </v-card>
  </div>
</template>

<script setup>
import { ref, computed, onMounted, watch } from 'vue'
import { geneApi } from '../api/genes'

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
  },
]

// Computed
const pageCount = computed(() => Math.ceil(totalItems.value / itemsPerPage.value))

const maxEvidenceCount = computed(() => {
  if (genes.value.length === 0) return 4 // fallback to API max
  return Math.max(...genes.value.map(gene => gene.evidence_count || 0))
})

const hasActiveFilters = computed(() => {
  return search.value || 
         (scoreRange.value[0] > 0 || scoreRange.value[1] < 100) ||
         selectedSources.value.length > 0 ||
         minEvidenceCount.value
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

const getScoreColor = score => {
  if (score >= 95) return 'success'
  if (score >= 80) return 'success'
  if (score >= 70) return 'info'
  if (score >= 50) return 'warning'
  if (score >= 30) return 'orange'
  return 'error'
}

const getScoreIcon = score => {
  if (score >= 80) return 'mdi-check-circle'
  if (score >= 50) return 'mdi-alert-circle'
  return 'mdi-close-circle'
}

const getScoreLabel = score => {
  if (score >= 95) return 'Definitive'
  if (score >= 80) return 'Strong'
  if (score >= 70) return 'Moderate'
  if (score >= 50) return 'Limited'
  if (score >= 30) return 'Minimal'
  return 'Disputed'
}

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
const showExternalLinks = (item) => {
  // TODO: Implement external links dialog
  console.log('Show external links for', item.approved_symbol)
}

const addToFavorites = (item) => {
  // TODO: Implement favorites functionality
  console.log('Add to favorites', item.approved_symbol)
}

const shareGene = (item) => {
  // TODO: Implement share functionality
  console.log('Share gene', item.approved_symbol)
}

// Lifecycle
onMounted(() => {
  loadGenes()
})
</script>

<style scoped>
.search-card {
  border: 1px solid rgb(var(--v-theme-surface-variant));
  background: rgb(var(--v-theme-surface));
}

.search-field :deep(.v-field__input) {
  font-size: 1rem;
}

.gene-table :deep(.v-data-table__th) {
  font-weight: 600;
  background: rgb(var(--v-theme-surface-light));
  border-bottom: 2px solid rgb(var(--v-theme-surface-variant));
}

.gene-table :deep(.v-data-table__td) {
  border-bottom: 1px solid rgb(var(--v-theme-surface-variant));
  padding: 8px 12px;
  height: 48px;
}

.gene-table :deep(.v-data-table__tr:hover) {
  background: rgb(var(--v-theme-primary-lighten-3)) !important;
}

.gene-link {
  color: rgb(var(--v-theme-primary));
  transition: color 0.2s ease;
}

.gene-link:hover {
  color: rgb(var(--v-theme-primary-darken-1));
  text-decoration: underline;
}

.v-theme--dark .search-card {
  background: rgb(var(--v-theme-surface-bright));
}
</style>