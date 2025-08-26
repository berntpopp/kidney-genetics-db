<template>
  <div>
    <!-- Loading State -->
    <v-container v-if="loading" class="text-center py-12">
      <v-progress-circular indeterminate color="primary" size="64" />
      <p class="text-h6 mt-4 text-medium-emphasis">Loading gene information...</p>
    </v-container>

    <!-- Main Content -->
    <div v-else-if="gene">
      <!-- Breadcrumb Navigation -->
      <v-container fluid class="pa-0">
        <v-breadcrumbs :items="breadcrumbs" density="compact" class="px-6 py-2 bg-surface-light">
          <template #prepend>
            <v-icon icon="mdi-home" size="small" />
          </template>
          <template #divider>
            <v-icon icon="mdi-chevron-right" size="small" />
          </template>
        </v-breadcrumbs>
      </v-container>

      <v-container>
        <!-- Gene Header -->
        <div class="d-flex align-start justify-space-between mb-6">
          <div class="flex-grow-1">
            <div class="d-flex align-center mb-2">
              <v-btn icon="mdi-arrow-left" variant="text" size="small" to="/genes" class="mr-3" />
              <div>
                <h1 class="text-h3 font-weight-bold">{{ gene.approved_symbol }}</h1>
                <p class="text-body-1 text-medium-emphasis">Gene information</p>
              </div>
            </div>
          </div>

          <!-- Action Buttons -->
          <div class="d-flex ga-2">
            <v-btn variant="outlined" size="small" prepend-icon="mdi-download">Save</v-btn>
            <v-btn variant="outlined" size="small" prepend-icon="mdi-share-variant">Share</v-btn>
            <v-btn variant="outlined" size="small" prepend-icon="mdi-export">Export</v-btn>
            <v-menu>
              <template #activator="{ props }">
                <v-btn icon="mdi-dots-vertical" variant="text" size="small" v-bind="props" />
              </template>
              <v-list density="compact">
                <v-list-item @click="copyGeneId">
                  <v-list-item-title>Copy Gene ID</v-list-item-title>
                </v-list-item>
                <v-list-item @click="viewInHGNC">
                  <v-list-item-title>View in HGNC</v-list-item-title>
                </v-list-item>
              </v-list>
            </v-menu>
          </div>
        </div>

        <!-- Overview Cards -->
        <v-row class="mb-6 align-stretch">
          <!-- Gene Information Card -->
          <v-col cols="12" md="8" lg="8" class="d-flex">
            <GeneInformationCard
              :gene="gene"
              :annotations="annotations"
              :loading-annotations="loadingAnnotations"
              class="flex-grow-1"
            />
          </v-col>

          <!-- Evidence Score Visualization with Breakdown -->
          <v-col cols="12" md="4" lg="4" class="d-flex">
            <ScoreBreakdown
              :score="gene.evidence_score"
              :breakdown="gene.score_breakdown"
              variant="card"
              class="flex-grow-1"
            />
          </v-col>
        </v-row>

        <!-- Evidence Details Section -->
        <div class="mb-6">
          <div class="d-flex align-center justify-space-between mb-4">
            <h2 class="text-h4 font-weight-medium">Evidence Details</h2>
            <div class="d-flex ga-2">
              <v-btn
                prepend-icon="mdi-refresh"
                variant="outlined"
                size="small"
                :loading="loadingEvidence"
                @click="refreshEvidence"
              >
                Refresh
              </v-btn>
              <v-btn
                prepend-icon="mdi-filter"
                variant="outlined"
                size="small"
                @click="showFilterPanel = !showFilterPanel"
              >
                Filter
              </v-btn>
            </div>
          </div>

          <!-- Filter Panel -->
          <v-expand-transition>
            <v-card v-show="showFilterPanel" class="mb-4">
              <v-card-text>
                <v-row>
                  <v-col cols="12" md="4">
                    <v-select
                      v-model="selectedEvidenceSources"
                      :items="availableEvidenceSources"
                      label="Filter by Source"
                      multiple
                      chips
                      density="comfortable"
                      variant="outlined"
                    />
                  </v-col>
                  <v-col cols="12" md="4">
                    <v-select
                      v-model="evidenceSortOrder"
                      :items="evidenceSortOptions"
                      label="Sort by"
                      density="comfortable"
                      variant="outlined"
                    />
                  </v-col>
                  <v-col cols="12" md="4" class="d-flex align-center">
                    <v-btn variant="text" @click="clearEvidenceFilters"> Clear Filters </v-btn>
                  </v-col>
                </v-row>
              </v-card-text>
            </v-card>
          </v-expand-transition>

          <!-- Evidence Cards -->
          <v-expansion-panels v-if="evidence.length > 0" variant="accordion">
            <EvidenceCard
              v-for="item in sortedEvidence"
              :key="`${item.source}_${item.source_id}`"
              :evidence="item"
            />
          </v-expansion-panels>
          <div v-else-if="loadingEvidence" class="text-center py-8">
            <v-progress-circular indeterminate color="primary" />
            <p class="text-body-2 mt-2 text-medium-emphasis">Loading evidence...</p>
          </div>
          <div v-else class="text-center py-8">
            <v-icon icon="mdi-information-outline" size="48" color="grey-lighten-1" />
            <p class="text-body-1 mt-2 text-medium-emphasis">No evidence records available</p>
          </div>
        </div>
      </v-container>
    </div>

    <!-- Error State -->
    <v-container v-else class="text-center py-12">
      <v-icon icon="mdi-alert-circle" size="64" color="error" class="mb-4" />
      <h2 class="text-h4 mb-2">Gene Not Found</h2>
      <p class="text-body-1 text-medium-emphasis mb-4">
        The gene "{{ $route.params.symbol }}" could not be found in our database.
      </p>
      <v-btn color="primary" to="/genes" prepend-icon="mdi-arrow-left">
        Back to Gene Browser
      </v-btn>
    </v-container>
  </div>
</template>

<script setup>
import { ref, computed, onMounted } from 'vue'
import { useRoute } from 'vue-router'
import { geneApi } from '../api/genes'
import ScoreBreakdown from '../components/ScoreBreakdown.vue'
import EvidenceCard from '../components/evidence/EvidenceCard.vue'
import GeneInformationCard from '../components/gene/GeneInformationCard.vue'

const route = useRoute()

// Data
const gene = ref(null)
const evidence = ref([])
const annotations = ref(null)
const loading = ref(true)
const loadingEvidence = ref(false)
const loadingAnnotations = ref(false)
const showFilterPanel = ref(false)
const selectedEvidenceSources = ref([])
const evidenceSortOrder = ref('score_desc')

// Computed
const breadcrumbs = computed(() => [
  { title: 'Home', to: '/' },
  { title: 'Gene Browser', to: '/genes' },
  { title: gene.value?.approved_symbol || 'Loading...', disabled: true }
])

const availableEvidenceSources = computed(() => {
  const sources = [...new Set(evidence.value.map(e => e.source))]
  return sources.sort()
})

const evidenceSortOptions = [
  { title: 'Score (High to Low)', value: 'score_desc' },
  { title: 'Score (Low to High)', value: 'score_asc' },
  { title: 'Source (A-Z)', value: 'source_asc' },
  { title: 'Source (Z-A)', value: 'source_desc' }
]

const filteredEvidence = computed(() => {
  if (selectedEvidenceSources.value.length === 0) {
    return evidence.value
  }
  return evidence.value.filter(e => selectedEvidenceSources.value.includes(e.source))
})

const sortedEvidence = computed(() => {
  const sorted = [...filteredEvidence.value]
  switch (evidenceSortOrder.value) {
    case 'score_asc':
      return sorted.sort((a, b) => (a.score || 0) - (b.score || 0))
    case 'score_desc':
      return sorted.sort((a, b) => (b.score || 0) - (a.score || 0))
    case 'source_asc':
      return sorted.sort((a, b) => a.source.localeCompare(b.source))
    case 'source_desc':
      return sorted.sort((a, b) => b.source.localeCompare(a.source))
    default:
      return sorted
  }
})

// Methods
const fetchGeneDetails = async () => {
  loading.value = true
  try {
    const response = await geneApi.getGene(route.params.symbol)
    gene.value = response
    await Promise.all([fetchEvidence(), fetchAnnotations()])
  } catch (error) {
    console.error('Failed to fetch gene details:', error)
    gene.value = null
  } finally {
    loading.value = false
  }
}

const fetchEvidence = async () => {
  if (!gene.value) return

  loadingEvidence.value = true
  try {
    const response = await geneApi.getGeneEvidence(gene.value.approved_symbol)
    evidence.value = response.evidence || []
  } catch (error) {
    console.error('Failed to fetch evidence:', error)
    evidence.value = []
  } finally {
    loadingEvidence.value = false
  }
}

const fetchAnnotations = async () => {
  if (!gene.value) return

  loadingAnnotations.value = true
  try {
    const response = await geneApi.getGeneAnnotations(gene.value.id)
    annotations.value = response
  } catch (error) {
    console.error('Failed to fetch annotations:', error)
    annotations.value = null
  } finally {
    loadingAnnotations.value = false
  }
}

const refreshEvidence = () => {
  fetchEvidence()
}

const clearEvidenceFilters = () => {
  selectedEvidenceSources.value = []
  evidenceSortOrder.value = 'score_desc'
}

const copyGeneId = () => {
  if (gene.value?.hgnc_id) {
    navigator.clipboard.writeText(gene.value.hgnc_id)
  }
}

const viewInHGNC = () => {
  if (gene.value?.hgnc_id) {
    const hgncId = gene.value.hgnc_id.replace('HGNC:', '')
    window.open(
      `https://www.genenames.org/data/gene-symbol-report/#!/hgnc_id/HGNC:${hgncId}`,
      '_blank'
    )
  }
}

// Lifecycle
onMounted(() => {
  fetchGeneDetails()
})
</script>
