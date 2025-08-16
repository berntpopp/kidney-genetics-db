<template>
  <div>
    <!-- Search Bar -->
    <v-card flat class="mb-4">
      <v-card-text>
        <v-row>
          <v-col cols="12" md="6">
            <v-text-field
              v-model="search"
              prepend-inner-icon="mdi-magnify"
              label="Search genes by symbol or HGNC ID"
              clearable
              hide-details
              variant="outlined"
              density="compact"
              @input="debouncedSearch"
            />
          </v-col>
          <v-col cols="12" md="3">
            <v-text-field
              v-model.number="minScore"
              label="Min Score"
              type="number"
              min="0"
              max="100"
              hide-details
              variant="outlined"
              density="compact"
              @input="debouncedSearch"
            />
          </v-col>
          <v-col cols="12" md="3">
            <v-select
              v-model="itemsPerPage"
              :items="[10, 25, 50, 100]"
              label="Items per page"
              hide-details
              variant="outlined"
              density="compact"
              @update:model-value="loadGenes"
            />
          </v-col>
        </v-row>
      </v-card-text>
    </v-card>

    <!-- Data Table -->
    <v-data-table-server
      :headers="headers"
      :items="genes"
      :items-length="totalItems"
      :loading="loading"
      :items-per-page="itemsPerPage"
      class="elevation-1"
      @update:options="updateOptions"
    >
      <template #[`item.approved_symbol`]="{ item }">
        <router-link
          :to="`/genes/${item.approved_symbol}`"
          class="text-decoration-none font-weight-medium"
        >
          {{ item.approved_symbol }}
        </router-link>
      </template>

      <template #[`item.sources`]="{ item }">
        <v-chip
          v-for="source in item.sources"
          :key="source"
          size="small"
          class="ma-1"
          :color="getSourceColor(source)"
        >
          {{ source }}
        </v-chip>
      </template>

      <template #[`item.evidence_score`]="{ item }">
        <v-chip
          v-if="item.evidence_score"
          :color="getScoreColor(item.evidence_score)"
          variant="flat"
        >
          {{ item.evidence_score?.toFixed(1) }}
        </v-chip>
        <span v-else class="text-grey">-</span>
      </template>

      <template #[`item.actions`]="{ item }">
        <v-btn icon="mdi-eye" size="small" variant="text" :to="`/genes/${item.approved_symbol}`" />
      </template>

      <template #bottom>
        <v-divider />
        <div class="text-center pa-2">
          <v-pagination
            v-model="page"
            :length="pageCount"
            :total-visible="7"
            @update:model-value="loadGenes"
          />
        </div>
      </template>
    </v-data-table-server>
  </div>
</template>

<script setup>
import { ref, computed, onMounted } from 'vue'
import { geneApi } from '../api/genes'

// Data
const genes = ref([])
const loading = ref(false)
const totalItems = ref(0)
const page = ref(1)
const itemsPerPage = ref(25)
const search = ref('')
const minScore = ref(null)

// Table headers - enable sorting for relevant columns
const headers = [
  { title: 'Symbol', key: 'approved_symbol', sortable: true },
  { title: 'HGNC ID', key: 'hgnc_id', sortable: true },
  { title: 'Evidence Count', key: 'evidence_count', sortable: true },
  { title: 'Score', key: 'evidence_score', sortable: true },
  { title: 'Sources', key: 'sources', sortable: false },
  { title: 'Actions', key: 'actions', sortable: false, align: 'end' }
]

// Computed
const pageCount = computed(() => Math.ceil(totalItems.value / itemsPerPage.value))

// Methods
const loadGenes = async (sortBy = null, sortDesc = false) => {
  loading.value = true
  try {
    const response = await geneApi.getGenes({
      page: page.value,
      perPage: itemsPerPage.value,
      search: search.value,
      minScore: minScore.value,
      sortBy: sortBy,
      sortDesc: sortDesc
    })
    genes.value = response.items
    totalItems.value = response.total
  } catch (error) {
    console.error('Error loading genes:', error)
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

let searchTimeout
const debouncedSearch = () => {
  clearTimeout(searchTimeout)
  searchTimeout = setTimeout(() => {
    page.value = 1
    loadGenes()
  }, 500)
}

const getSourceColor = source => {
  const colors = {
    PanelApp: 'primary',
    HPO: 'secondary',
    PubTator: 'info',
    Literature: 'success'
  }
  return colors[source] || 'grey'
}

const getScoreColor = score => {
  if (score >= 80) return 'success'
  if (score >= 60) return 'warning'
  if (score >= 40) return 'orange'
  return 'error'
}

// Lifecycle
onMounted(() => {
  loadGenes()
})
</script>
