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
              <v-btn
                icon="mdi-arrow-left"
                variant="text"
                to="/genes"
                class="mr-3"
                title="Back to gene browser"
              />
              <div>
                <h1 class="text-h3 font-weight-bold mb-1">
                  {{ gene.approved_symbol }}
                </h1>
                <p class="text-h6 text-medium-emphasis">
                  {{ gene.approved_name || 'Gene information' }}
                </p>
              </div>
            </div>
            <div class="d-flex align-center flex-wrap ga-2">
              <v-chip prepend-icon="mdi-identifier" variant="tonal" color="primary">
                {{ gene.hgnc_id }}
              </v-chip>
              <v-chip
                v-if="gene.evidence_score"
                :prepend-icon="getScoreIcon(gene.evidence_score)"
                :color="getScoreColor(gene.evidence_score)"
                variant="flat"
              >
                {{ gene.evidence_score.toFixed(1) }} - {{ getScoreLabel(gene.evidence_score) }}
              </v-chip>
              <v-chip
                v-if="gene.evidence_count"
                prepend-icon="mdi-file-document-multiple"
                variant="tonal"
              >
                {{ gene.evidence_count }} evidence{{ gene.evidence_count !== 1 ? 's' : '' }}
              </v-chip>
            </div>
          </div>

          <!-- Action Buttons -->
          <div class="d-flex ga-2 flex-wrap">
            <v-btn prepend-icon="mdi-bookmark-outline" variant="outlined" @click="addToFavorites">
              Save
            </v-btn>
            <v-btn prepend-icon="mdi-share-variant" variant="outlined" @click="shareGene">
              Share
            </v-btn>
            <v-btn prepend-icon="mdi-download" variant="outlined" @click="exportGene">
              Export
            </v-btn>
            <v-menu>
              <template #activator="{ props }">
                <v-btn icon="mdi-dots-vertical" variant="outlined" v-bind="props" />
              </template>
              <v-list density="compact">
                <v-list-item
                  v-for="link in externalLinks"
                  :key="link.name"
                  :prepend-icon="link.icon"
                  :title="link.name"
                  :href="link.url"
                  target="_blank"
                />
              </v-list>
            </v-menu>
          </div>
        </div>

        <!-- Overview Cards -->
        <v-row class="mb-6">
          <!-- Gene Information Card -->
          <v-col cols="12" md="6" lg="4">
            <v-card height="100%" class="info-card">
              <v-card-item>
                <template #prepend>
                  <v-avatar color="primary" size="40">
                    <v-icon icon="mdi-dna" color="white" />
                  </v-avatar>
                </template>
                <v-card-title>Gene Information</v-card-title>
              </v-card-item>
              <v-card-text>
                <v-list density="compact" class="transparent">
                  <v-list-item>
                    <template #prepend>
                      <v-icon icon="mdi-tag" size="small" class="text-medium-emphasis" />
                    </template>
                    <v-list-item-title class="text-body-2 font-weight-medium"
                      >Symbol</v-list-item-title
                    >
                    <v-list-item-subtitle class="font-mono">{{
                      gene.approved_symbol
                    }}</v-list-item-subtitle>
                  </v-list-item>

                  <v-list-item>
                    <template #prepend>
                      <v-icon icon="mdi-identifier" size="small" class="text-medium-emphasis" />
                    </template>
                    <v-list-item-title class="text-body-2 font-weight-medium"
                      >HGNC ID</v-list-item-title
                    >
                    <v-list-item-subtitle class="font-mono">{{
                      gene.hgnc_id
                    }}</v-list-item-subtitle>
                  </v-list-item>

                  <v-list-item v-if="gene.alias_symbol?.length">
                    <template #prepend>
                      <v-icon icon="mdi-tag-multiple" size="small" class="text-medium-emphasis" />
                    </template>
                    <v-list-item-title class="text-body-2 font-weight-medium"
                      >Aliases</v-list-item-title
                    >
                    <v-list-item-subtitle>
                      <div class="d-flex flex-wrap ga-1 mt-1">
                        <v-chip
                          v-for="alias in gene.alias_symbol.slice(0, 3)"
                          :key="alias"
                          size="x-small"
                          variant="outlined"
                        >
                          {{ alias }}
                        </v-chip>
                        <v-tooltip v-if="gene.alias_symbol.length > 3" location="bottom">
                          <template #activator="{ props }">
                            <v-chip size="x-small" variant="outlined" v-bind="props">
                              +{{ gene.alias_symbol.length - 3 }}
                            </v-chip>
                          </template>
                          <div class="pa-2">
                            {{ gene.alias_symbol.slice(3).join(', ') }}
                          </div>
                        </v-tooltip>
                      </div>
                    </v-list-item-subtitle>
                  </v-list-item>

                  <v-list-item v-if="gene.chromosome">
                    <template #prepend>
                      <v-icon icon="mdi-map-marker" size="small" class="text-medium-emphasis" />
                    </template>
                    <v-list-item-title class="text-body-2 font-weight-medium"
                      >Location</v-list-item-title
                    >
                    <v-list-item-subtitle>{{ gene.chromosome }}</v-list-item-subtitle>
                  </v-list-item>
                </v-list>
              </v-card-text>
            </v-card>
          </v-col>

          <!-- Evidence Score Visualization -->
          <v-col cols="12" md="6" lg="4">
            <v-card height="100%" class="score-card">
              <v-card-item>
                <template #prepend>
                  <v-avatar :color="getScoreColor(gene.evidence_score || 0)" size="40">
                    <v-icon :icon="getScoreIcon(gene.evidence_score || 0)" color="white" />
                  </v-avatar>
                </template>
                <v-card-title>Evidence Score</v-card-title>
              </v-card-item>
              <v-card-text>
                <div v-if="gene.evidence_score" class="text-center">
                  <div class="position-relative d-inline-block">
                    <v-progress-circular
                      :model-value="gene.evidence_score"
                      :color="getScoreColor(gene.evidence_score)"
                      size="120"
                      width="8"
                      class="score-circle"
                    >
                      <div class="text-center">
                        <div class="text-h4 font-weight-bold">
                          {{ gene.evidence_score.toFixed(1) }}
                        </div>
                        <div class="text-caption text-medium-emphasis">/ 100</div>
                      </div>
                    </v-progress-circular>
                  </div>
                  <div class="mt-3">
                    <v-chip
                      :color="getScoreColor(gene.evidence_score)"
                      variant="tonal"
                      size="small"
                    >
                      {{ getScoreLabel(gene.evidence_score) }}
                    </v-chip>
                  </div>
                  <p class="text-body-2 text-medium-emphasis mt-2">
                    {{ getScoreDescription(gene.evidence_score) }}
                  </p>
                </div>
                <div v-else class="text-center py-4">
                  <v-icon icon="mdi-help-circle" size="large" class="text-medium-emphasis mb-2" />
                  <p class="text-body-2 text-medium-emphasis">No evidence score available</p>
                </div>
              </v-card-text>
            </v-card>
          </v-col>

          <!-- Data Sources -->
          <v-col cols="12" lg="4">
            <v-card height="100%" class="sources-card">
              <v-card-item>
                <template #prepend>
                  <v-avatar color="info" size="40">
                    <v-icon icon="mdi-database" color="white" />
                  </v-avatar>
                </template>
                <v-card-title>Data Sources</v-card-title>
                <template #append>
                  <v-chip size="small" variant="tonal">
                    {{ gene.sources?.length || 0 }}
                  </v-chip>
                </template>
              </v-card-item>
              <v-card-text>
                <div v-if="gene.sources?.length" class="d-flex flex-wrap ga-2">
                  <v-chip
                    v-for="source in gene.sources"
                    :key="source"
                    :color="getSourceColor(source)"
                    variant="tonal"
                    size="small"
                  >
                    <v-icon :icon="getSourceIcon(source)" size="x-small" start />
                    {{ source }}
                  </v-chip>
                </div>
                <div v-else class="text-center py-4">
                  <v-icon icon="mdi-database-off" size="large" class="text-medium-emphasis mb-2" />
                  <p class="text-body-2 text-medium-emphasis">No source information available</p>
                </div>
              </v-card-text>
            </v-card>
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
                prepend-icon="mdi-filter-variant"
                variant="outlined"
                size="small"
                @click="showEvidenceFilters = !showEvidenceFilters"
              >
                Filter
              </v-btn>
            </div>
          </div>

          <!-- Evidence Filters -->
          <v-expand-transition>
            <v-card v-if="showEvidenceFilters" class="mb-4" rounded="lg">
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

          <!-- Evidence Loading State -->
          <v-card v-if="loadingEvidence" class="text-center py-12" rounded="lg">
            <v-progress-circular indeterminate color="primary" size="48" />
            <p class="text-body-1 mt-4 text-medium-emphasis">Loading evidence data...</p>
          </v-card>

          <!-- Evidence Content -->
          <div v-else-if="filteredEvidence?.length" class="evidence-section">
            <v-expansion-panels variant="accordion" class="mb-4">
              <v-expansion-panel
                v-for="(item, index) in filteredEvidence"
                :key="index"
                class="evidence-panel"
              >
                <v-expansion-panel-title class="py-4">
                  <div class="d-flex align-center justify-space-between w-100">
                    <div class="d-flex align-center">
                      <v-avatar :color="getSourceColor(item.source_name)" size="32" class="mr-3">
                        <v-icon
                          :icon="getSourceIcon(item.source_name)"
                          size="small"
                          color="white"
                        />
                      </v-avatar>
                      <div>
                        <div class="text-h6 font-weight-medium">{{ item.source_name }}</div>
                        <div class="text-body-2 text-medium-emphasis">{{ item.source_detail }}</div>
                      </div>
                    </div>
                    <div class="d-flex align-center ga-2">
                      <v-chip
                        v-if="item.evidence_data?.panels?.length"
                        size="small"
                        variant="tonal"
                        color="primary"
                      >
                        {{ item.evidence_data.panels.length }} panel{{
                          item.evidence_data.panels.length !== 1 ? 's' : ''
                        }}
                      </v-chip>
                      <v-chip
                        v-if="item.evidence_data?.phenotypes?.length"
                        size="small"
                        variant="tonal"
                        color="secondary"
                      >
                        {{ item.evidence_data.phenotypes.length }} phenotype{{
                          item.evidence_data.phenotypes.length !== 1 ? 's' : ''
                        }}
                      </v-chip>
                    </div>
                  </div>
                </v-expansion-panel-title>

                <v-expansion-panel-text class="py-4">
                  <v-row>
                    <!-- Gene Panels -->
                    <v-col v-if="item.evidence_data?.panels?.length" cols="12" md="6">
                      <h4 class="text-h6 mb-3 d-flex align-center">
                        <v-icon icon="mdi-view-dashboard" size="small" class="mr-2" />
                        Gene Panels
                      </h4>
                      <div class="d-flex flex-column ga-2">
                        <v-card
                          v-for="panel in item.evidence_data.panels.slice(0, 5)"
                          :key="panel.id"
                          variant="outlined"
                          density="compact"
                        >
                          <v-card-text class="py-2">
                            <div class="d-flex align-center justify-space-between">
                              <div>
                                <div class="text-body-2 font-weight-medium">{{ panel.name }}</div>
                                <div class="text-caption text-medium-emphasis">
                                  {{ panel.source }} • Version {{ panel.version }}
                                </div>
                              </div>
                              <v-chip
                                :color="panel.source === 'AU' ? 'success' : 'primary'"
                                size="x-small"
                                variant="flat"
                              >
                                {{ panel.source }}
                              </v-chip>
                            </div>
                          </v-card-text>
                        </v-card>
                        <v-btn
                          v-if="item.evidence_data.panels.length > 5"
                          variant="text"
                          size="small"
                          @click="showAllPanels(item)"
                        >
                          Show {{ item.evidence_data.panels.length - 5 }} more panels
                        </v-btn>
                      </div>
                    </v-col>

                    <!-- Phenotypes -->
                    <v-col v-if="item.evidence_data?.phenotypes?.length" cols="12" md="6">
                      <h4 class="text-h6 mb-3 d-flex align-center">
                        <v-icon icon="mdi-human" size="small" class="mr-2" />
                        Associated Phenotypes
                      </h4>
                      <div class="phenotypes-grid">
                        <v-chip
                          v-for="(phenotype, idx) in item.evidence_data.phenotypes.slice(0, 10)"
                          :key="idx"
                          size="small"
                          variant="outlined"
                          class="mb-2 mr-2"
                        >
                          {{ phenotype }}
                        </v-chip>
                        <v-menu v-if="item.evidence_data.phenotypes.length > 10" location="bottom">
                          <template #activator="{ props }">
                            <v-chip size="small" variant="outlined" v-bind="props" class="mb-2">
                              +{{ item.evidence_data.phenotypes.length - 10 }} more
                            </v-chip>
                          </template>
                          <v-card max-width="400">
                            <v-card-text>
                              <div class="d-flex flex-wrap ga-1">
                                <v-chip
                                  v-for="(phenotype, idx) in item.evidence_data.phenotypes.slice(
                                    10
                                  )"
                                  :key="idx"
                                  size="x-small"
                                  variant="outlined"
                                >
                                  {{ phenotype }}
                                </v-chip>
                              </div>
                            </v-card-text>
                          </v-card>
                        </v-menu>
                      </div>
                    </v-col>

                    <!-- Inheritance Modes -->
                    <v-col v-if="item.evidence_data?.modes_of_inheritance?.length" cols="12" md="6">
                      <h4 class="text-h6 mb-3 d-flex align-center">
                        <v-icon icon="mdi-family-tree" size="small" class="mr-2" />
                        Inheritance Modes
                      </h4>
                      <div class="d-flex flex-wrap ga-2">
                        <v-chip
                          v-for="(mode, idx) in item.evidence_data.modes_of_inheritance"
                          :key="idx"
                          size="small"
                          color="info"
                          variant="tonal"
                        >
                          {{ mode }}
                        </v-chip>
                      </div>
                    </v-col>

                    <!-- Supporting Evidence -->
                    <v-col v-if="item.evidence_data?.evidence?.length" cols="12" md="6">
                      <h4 class="text-h6 mb-3 d-flex align-center">
                        <v-icon icon="mdi-file-document-check" size="small" class="mr-2" />
                        Supporting Evidence
                      </h4>
                      <div class="d-flex flex-wrap ga-1">
                        <v-chip
                          v-for="(ev, idx) in [...new Set(item.evidence_data.evidence)].slice(0, 8)"
                          :key="idx"
                          size="small"
                          variant="tonal"
                          color="success"
                        >
                          {{ ev }}
                        </v-chip>
                        <v-chip
                          v-if="item.evidence_data.evidence.length > 8"
                          size="small"
                          variant="outlined"
                        >
                          +{{ item.evidence_data.evidence.length - 8 }}
                        </v-chip>
                      </div>
                    </v-col>
                  </v-row>

                  <!-- Metadata -->
                  <v-divider class="my-4" />
                  <div class="d-flex align-center justify-space-between">
                    <div class="text-caption text-medium-emphasis">
                      <v-icon icon="mdi-clock-outline" size="small" class="mr-1" />
                      Last updated: {{ formatDate(item.evidence_data?.last_updated) }}
                    </div>
                    <div class="d-flex ga-2">
                      <v-btn
                        size="small"
                        variant="text"
                        prepend-icon="mdi-open-in-new"
                        @click="viewExternalSource(item)"
                      >
                        View Source
                      </v-btn>
                      <v-btn
                        size="small"
                        variant="text"
                        prepend-icon="mdi-download"
                        @click="exportEvidence(item)"
                      >
                        Export
                      </v-btn>
                    </div>
                  </div>
                </v-expansion-panel-text>
              </v-expansion-panel>
            </v-expansion-panels>
          </div>

          <!-- No Evidence State -->
          <v-card v-else class="text-center py-12" rounded="lg">
            <v-icon icon="mdi-file-document-search" size="64" class="mb-4 text-medium-emphasis" />
            <h3 class="text-h6 mb-2">No Evidence Data</h3>
            <p class="text-body-2 text-medium-emphasis mb-4">
              {{
                selectedEvidenceSources.length > 0
                  ? 'No evidence matches your current filters'
                  : 'No evidence data available for this gene'
              }}
            </p>
            <v-btn
              v-if="selectedEvidenceSources.length > 0"
              color="primary"
              variant="outlined"
              @click="clearEvidenceFilters"
            >
              Clear Filters
            </v-btn>
          </v-card>
        </div>

        <!-- Related Genes Section -->
        <div v-if="relatedGenes?.length" class="mb-6">
          <h2 class="text-h4 font-weight-medium mb-4">Related Genes</h2>
          <v-row>
            <v-col
              v-for="relatedGene in relatedGenes.slice(0, 6)"
              :key="relatedGene.approved_symbol"
              cols="12"
              sm="6"
              md="4"
            >
              <v-card :to="`/genes/${relatedGene.approved_symbol}`" class="related-gene-card" hover>
                <v-card-text>
                  <div class="d-flex align-center justify-space-between">
                    <div>
                      <div class="text-h6 font-weight-medium">
                        {{ relatedGene.approved_symbol }}
                      </div>
                      <div class="text-body-2 text-medium-emphasis">{{ relatedGene.hgnc_id }}</div>
                    </div>
                    <v-chip
                      v-if="relatedGene.evidence_score"
                      :color="getScoreColor(relatedGene.evidence_score)"
                      size="small"
                      variant="tonal"
                    >
                      {{ relatedGene.evidence_score.toFixed(1) }}
                    </v-chip>
                  </div>
                </v-card-text>
              </v-card>
            </v-col>
          </v-row>
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

const route = useRoute()

// Data
const gene = ref(null)
const evidence = ref(null)
const relatedGenes = ref([])
const loading = ref(true)
const loadingEvidence = ref(true)
const showEvidenceFilters = ref(false)
const selectedEvidenceSources = ref([])
const evidenceSortOrder = ref('newest')

// Filter options
const availableEvidenceSources = [
  { title: 'PanelApp', value: 'PanelApp' },
  { title: 'HPO', value: 'HPO' },
  { title: 'PubTator', value: 'PubTator' },
  { title: 'Literature', value: 'Literature' }
]

const evidenceSortOptions = [
  { title: 'Newest First', value: 'newest' },
  { title: 'Oldest First', value: 'oldest' },
  { title: 'Source Name', value: 'source' },
  { title: 'Most Panels', value: 'panels' }
]

// Computed properties
const breadcrumbs = computed(() => [
  { title: 'Home', to: '/' },
  { title: 'Gene Browser', to: '/genes' },
  { title: gene.value?.approved_symbol || 'Gene', disabled: true }
])

const externalLinks = computed(() => {
  if (!gene.value) return []

  return [
    {
      name: 'HGNC',
      icon: 'mdi-open-in-new',
      url: `https://www.genenames.org/data/gene-symbol-report/#!/hgnc_id/${gene.value.hgnc_id.replace('HGNC:', '')}`
    },
    {
      name: 'NCBI Gene',
      icon: 'mdi-open-in-new',
      url: `https://www.ncbi.nlm.nih.gov/gene/?term=${gene.value.approved_symbol}[sym]`
    },
    {
      name: 'UniProt',
      icon: 'mdi-open-in-new',
      url: `https://www.uniprot.org/uniprot/?query=gene:${gene.value.approved_symbol}`
    },
    {
      name: 'OMIM',
      icon: 'mdi-open-in-new',
      url: `https://www.omim.org/search/?index=entry&start=1&search=${gene.value.approved_symbol}`
    }
  ]
})

const filteredEvidence = computed(() => {
  if (!evidence.value?.evidence) return []

  let filtered = evidence.value.evidence

  if (selectedEvidenceSources.value.length > 0) {
    filtered = filtered.filter(item => selectedEvidenceSources.value.includes(item.source_name))
  }

  // Sort evidence
  switch (evidenceSortOrder.value) {
    case 'oldest':
      filtered = filtered.sort(
        (a, b) =>
          new Date(a.evidence_data?.last_updated || 0) -
          new Date(b.evidence_data?.last_updated || 0)
      )
      break
    case 'source':
      filtered = filtered.sort((a, b) => a.source_name.localeCompare(b.source_name))
      break
    case 'panels':
      filtered = filtered.sort(
        (a, b) => (b.evidence_data?.panels?.length || 0) - (a.evidence_data?.panels?.length || 0)
      )
      break
    default: // newest
      filtered = filtered.sort(
        (a, b) =>
          new Date(b.evidence_data?.last_updated || 0) -
          new Date(a.evidence_data?.last_updated || 0)
      )
  }

  return filtered
})

// Methods
const getSourceColor = source => {
  const colors = {
    PanelApp: 'primary',
    HPO: 'secondary',
    PubTator: 'info',
    Literature: 'success',
    Diagnostic: 'warning'
  }
  return colors[source] || 'grey'
}

const getSourceIcon = source => {
  const icons = {
    PanelApp: 'mdi-view-dashboard',
    HPO: 'mdi-human',
    PubTator: 'mdi-file-document',
    Literature: 'mdi-book-open',
    Diagnostic: 'mdi-test-tube'
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

const getScoreDescription = score => {
  if (score >= 95) return 'Very strong evidence for disease association'
  if (score >= 80) return 'Strong evidence supporting disease association'
  if (score >= 70) return 'Moderate evidence for disease association'
  if (score >= 50) return 'Limited evidence for disease association'
  if (score >= 30) return 'Minimal evidence for disease association'
  return 'Disputed or conflicting evidence'
}

const formatDate = dateString => {
  if (!dateString) return 'Unknown'
  return new Date(dateString).toLocaleDateString('en-US', {
    year: 'numeric',
    month: 'long',
    day: 'numeric'
  })
}

const clearEvidenceFilters = () => {
  selectedEvidenceSources.value = []
  evidenceSortOrder.value = 'newest'
}

const refreshEvidence = async () => {
  loadingEvidence.value = true
  try {
    evidence.value = await geneApi.getGeneEvidence(route.params.symbol)
  } catch (error) {
    console.error('Error refreshing evidence:', error)
  } finally {
    loadingEvidence.value = false
  }
}

const addToFavorites = () => {
  console.log('Add to favorites:', gene.value.approved_symbol)
}

const shareGene = () => {
  if (navigator.share) {
    navigator.share({
      title: `${gene.value.approved_symbol} - Kidney Genetics Database`,
      url: window.location.href
    })
  } else {
    navigator.clipboard.writeText(window.location.href)
  }
}

const exportGene = () => {
  console.log('Export gene:', gene.value.approved_symbol)
}

const showAllPanels = item => {
  console.log('Show all panels for:', item)
}

const viewExternalSource = item => {
  console.log('View external source:', item)
}

const exportEvidence = item => {
  console.log('Export evidence:', item)
}

// Lifecycle
onMounted(async () => {
  const symbol = route.params.symbol

  try {
    gene.value = await geneApi.getGene(symbol)
  } catch (error) {
    console.error('Error loading gene:', error)
  } finally {
    loading.value = false
  }

  try {
    evidence.value = await geneApi.getGeneEvidence(symbol)
  } catch (error) {
    console.error('Error loading evidence:', error)
  } finally {
    loadingEvidence.value = false
  }

  // Load related genes (mock for now)
  try {
    // This would be a real API call
    relatedGenes.value = []
  } catch (error) {
    console.error('Error loading related genes:', error)
  }
})
</script>

<style scoped>
.info-card,
.score-card,
.sources-card {
  transition: all 0.3s cubic-bezier(0.4, 0, 0.2, 1);
}

.info-card:hover,
.score-card:hover,
.sources-card:hover {
  transform: translateY(-2px);
}

.score-circle {
  filter: drop-shadow(0 4px 8px rgba(0, 0, 0, 0.1));
}

.evidence-panel {
  border: 1px solid rgb(var(--v-theme-surface-variant));
  margin-bottom: 8px;
  border-radius: 12px;
  overflow: hidden;
}

.evidence-panel:hover {
  border-color: rgb(var(--v-theme-primary));
}

.phenotypes-grid {
  max-height: 200px;
  overflow-y: auto;
}

.related-gene-card {
  transition: all 0.3s cubic-bezier(0.4, 0, 0.2, 1);
}

.related-gene-card:hover {
  transform: translateY(-2px);
  box-shadow: 0 8px 25px rgba(0, 0, 0, 0.1);
}

.font-mono {
  font-family: 'JetBrains Mono', 'Roboto Mono', monospace;
  font-size: 0.9em;
}

.transparent {
  background: transparent !important;
}

:deep(.v-expansion-panel-title) {
  padding: 16px 24px;
}

:deep(.v-expansion-panel-text__wrapper) {
  padding: 0 24px 16px;
}

/* Dark mode adjustments */
.v-theme--dark .evidence-panel {
  background: rgb(var(--v-theme-surface-bright));
}

.v-theme--dark .score-circle {
  filter: drop-shadow(0 4px 8px rgba(255, 255, 255, 0.1));
}
</style>
