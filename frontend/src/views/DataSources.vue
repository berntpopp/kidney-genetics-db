<template>
  <v-container>
    <!-- Page Header -->
    <v-row>
      <v-col cols="12">
        <div class="d-flex align-center mb-6">
          <v-icon color="primary" size="large" class="mr-3">mdi-database-sync</v-icon>
          <div>
            <h1 class="text-h4 font-weight-bold">Data Sources</h1>
            <p class="text-body-2 text-medium-emphasis ma-0">
              Live status and statistics from integrated data sources
            </p>
          </div>
        </div>
      </v-col>
    </v-row>

    <!-- Loading State -->
    <v-row v-if="loading">
      <v-col cols="12">
        <v-card>
          <v-card-text class="text-center py-12">
            <v-progress-circular indeterminate color="primary" size="64" class="mb-4" />
            <div class="text-h6">Loading data sources...</div>
          </v-card-text>
        </v-card>
      </v-col>
    </v-row>

    <!-- Data Sources Cards -->
    <v-row v-else>
      <v-col v-for="source in dataSources" :key="source.name" cols="12" md="6" lg="4">
        <v-card
          class="source-card h-100"
          :elevation="hoveredCard === source.name ? 4 : 1"
          @mouseenter="hoveredCard = source.name"
          @mouseleave="hoveredCard = null"
        >
          <!-- Header with gradient -->
          <div
            class="source-header pa-4"
            :style="`background: linear-gradient(135deg, ${getSourceGradient(source.name)});`"
          >
            <div class="d-flex align-center justify-space-between">
              <div class="d-flex align-center">
                <v-icon color="white" size="large" class="mr-3">
                  {{ getSourceIcon(source.name) }}
                </v-icon>
                <div>
                  <h3 class="text-h6 font-weight-bold text-white">{{ source.name }}</h3>
                  <div class="text-caption text-white-darken-1">{{ source.type || 'API' }}</div>
                </div>
              </div>
              <v-chip :color="getStatusChipColor(source.status)" size="small" variant="flat">
                {{ getStatusLabel(source.status) }}
              </v-chip>
            </div>
          </div>

          <!-- Content -->
          <v-card-text class="pa-4">
            <p class="text-body-2 text-medium-emphasis mb-4">
              {{ source.description || getSourceDescription(source.name) }}
            </p>

            <!-- Statistics -->
            <div class="d-flex justify-space-between align-center mb-3">
              <div class="text-center">
                <div class="text-h6 font-weight-bold text-success">
                  {{ source.stats?.gene_count || 0 }}
                </div>
                <div class="text-caption text-medium-emphasis">Genes</div>
              </div>
              <div class="text-center">
                <v-tooltip :text="getMetadataTooltip(source, 'primary')" location="bottom">
                  <template #activator="{ props }">
                    <div v-bind="props">
                      <div class="text-h6 font-weight-bold text-primary">
                        {{ getMetadataCount(source, 'primary') }}
                      </div>
                      <div class="text-caption text-medium-emphasis">
                        {{ getMetadataLabel(source, 'primary') }}
                      </div>
                    </div>
                  </template>
                </v-tooltip>
              </div>
              <div v-if="getMetadataCount(source, 'secondary') > 0" class="text-center">
                <v-tooltip :text="getMetadataTooltip(source, 'secondary')" location="bottom">
                  <template #activator="{ props }">
                    <div v-bind="props">
                      <div class="text-h6 font-weight-bold text-info">
                        {{ getMetadataCount(source, 'secondary') }}
                      </div>
                      <div class="text-caption text-medium-emphasis">
                        {{ getMetadataLabel(source, 'secondary') }}
                      </div>
                    </div>
                  </template>
                </v-tooltip>
              </div>
            </div>

            <!-- Last Update -->
            <v-divider class="my-3" />
            <div class="d-flex align-center justify-space-between">
              <span class="text-caption text-medium-emphasis">Last Updated</span>
              <span class="text-caption font-weight-medium">
                {{ formatDate(source.stats?.last_updated) }}
              </span>
            </div>
          </v-card-text>
        </v-card>
      </v-col>
    </v-row>

    <!-- Summary Statistics -->
    <v-row class="mt-6">
      <v-col cols="12">
        <v-card>
          <v-card-title class="d-flex align-center">
            <v-icon color="primary" class="mr-2">mdi-chart-box</v-icon>
            Database Summary
          </v-card-title>
          <v-card-text>
            <v-row>
              <v-col cols="6" sm="3">
                <v-tooltip :text="apiResponse?.explanations?.active_sources" location="bottom">
                  <template #activator="{ props }">
                    <div class="text-center" v-bind="props">
                      <div class="text-h4 font-weight-bold text-primary">
                        {{ summaryStats.total_active }}
                      </div>
                      <div class="text-body-2 text-medium-emphasis">
                        Active Sources
                        <v-icon size="x-small" class="ml-1">mdi-help-circle-outline</v-icon>
                      </div>
                    </div>
                  </template>
                </v-tooltip>
              </v-col>
              <v-col cols="6" sm="3">
                <v-tooltip :text="apiResponse?.explanations?.unique_genes" location="bottom">
                  <template #activator="{ props }">
                    <div class="text-center" v-bind="props">
                      <div class="text-h4 font-weight-bold text-success">
                        {{ summaryStats.unique_genes.toLocaleString() }}
                      </div>
                      <div class="text-body-2 text-medium-emphasis">
                        Unique Genes
                        <v-icon size="x-small" class="ml-1">mdi-help-circle-outline</v-icon>
                      </div>
                    </div>
                  </template>
                </v-tooltip>
              </v-col>
              <v-col cols="6" sm="3">
                <v-tooltip :text="apiResponse?.explanations?.source_coverage" location="bottom">
                  <template #activator="{ props }">
                    <div class="text-center" v-bind="props">
                      <div class="text-h4 font-weight-bold text-info">
                        {{ calculateCoverage() }}%
                      </div>
                      <div class="text-body-2 text-medium-emphasis">
                        Source Coverage
                        <v-icon size="x-small" class="ml-1">mdi-help-circle-outline</v-icon>
                      </div>
                    </div>
                  </template>
                </v-tooltip>
              </v-col>
              <v-col cols="6" sm="3">
                <v-tooltip :text="apiResponse?.explanations?.last_updated" location="bottom">
                  <template #activator="{ props }">
                    <div class="text-center" v-bind="props">
                      <div class="text-h4 font-weight-bold text-secondary">
                        {{ formatDate(summaryStats.last_update) }}
                      </div>
                      <div class="text-body-2 text-medium-emphasis">
                        Last Updated
                        <v-icon size="x-small" class="ml-1">mdi-help-circle-outline</v-icon>
                      </div>
                    </div>
                  </template>
                </v-tooltip>
              </v-col>
            </v-row>
          </v-card-text>
        </v-card>
      </v-col>
    </v-row>
  </v-container>
</template>

<script setup>
import { ref, computed, onMounted } from 'vue'
import { datasourceApi } from '@/api/datasources'

const loading = ref(true)
const hoveredCard = ref(null)
const dataSources = ref([])
const apiResponse = ref(null)

// Source descriptions mapping
const sourceDescriptions = {
  PanelApp: 'Expert-curated gene panels from UK Genomics England and Australian Genomics',
  HPO: 'Human Phenotype Ontology providing standardized phenotype-gene associations',
  PubTator: 'Literature mining from PubMed Central with automated text analysis',
  ClinGen: 'Clinical Genome Resource providing authoritative disease-gene relationships',
  GenCC: 'Harmonized gene-disease relationships from 40+ submitters worldwide',
  DiagnosticPanels: 'Commercial diagnostic panels from leading genetic testing laboratories'
}

// Summary stats computed from API data
const summaryStats = computed(() => {
  if (!apiResponse.value) {
    return {
      total_active: 0,
      unique_genes: 0,
      last_update: null
    }
  }

  const response = apiResponse.value

  return {
    total_active: response.total_active || 0,
    unique_genes: response.total_unique_genes || 0,
    last_update: response.last_data_update || null
  }
})

// Style guide color mappings
const getSourceGradient = sourceName => {
  const gradients = {
    PanelApp: '#0EA5E9, #0284C7', // Primary blue
    HPO: '#8B5CF6, #7C3AED', // Secondary purple
    PubTator: '#3B82F6, #2563EB', // Info blue
    ClinGen: '#F59E0B, #D97706', // Warning amber
    GenCC: '#10B981, #059669', // Success green
    DiagnosticPanels: '#EF4444, #DC2626' // Error red
  }
  return gradients[sourceName] || gradients['PanelApp']
}

const getSourceIcon = sourceName => {
  const icons = {
    PanelApp: 'mdi-view-dashboard',
    HPO: 'mdi-human',
    PubTator: 'mdi-file-document',
    ClinGen: 'mdi-test-tube',
    GenCC: 'mdi-dna',
    DiagnosticPanels: 'mdi-hospital-box'
  }
  return icons[sourceName] || 'mdi-database'
}

const getSourceDescription = sourceName => {
  return sourceDescriptions[sourceName] || 'Integrated data source for genetic information'
}

const getStatusChipColor = status => {
  switch (status) {
    case 'active':
      return 'success'
    case 'error':
      return 'error'
    case 'pending':
      return 'warning'
    default:
      return 'grey'
  }
}

const getStatusLabel = status => {
  switch (status) {
    case 'active':
      return 'Active'
    case 'error':
      return 'Error'
    case 'pending':
      return 'Pending'
    default:
      return 'Unknown'
  }
}

const getMetadataCount = (source, type) => {
  if (!source.stats?.metadata) return 0
  const metadata = source.stats.metadata

  // Map source to its metrics
  if (type === 'primary') {
    switch (source.name) {
      case 'ClinGen':
        return metadata.expert_panels || 0
      case 'GenCC':
        return metadata.submissions || 0
      case 'HPO':
        return metadata.phenotype_terms || 0
      case 'PubTator':
        return metadata.publications || 0
      case 'PanelApp':
        return metadata.panels || 0
      case 'DiagnosticPanels':
        return metadata.providers || 0
      default:
        return 0
    }
  } else if (type === 'secondary') {
    switch (source.name) {
      case 'ClinGen':
        return metadata.classifications || 0
      case 'GenCC':
        return metadata.submitters || 0
      case 'PanelApp':
        return metadata.regions || 0
      case 'DiagnosticPanels':
        return metadata.panels || 0
      default:
        return 0
    }
  }
  return 0
}

const getMetadataLabel = (source, type) => {
  if (type === 'primary') {
    switch (source.name) {
      case 'ClinGen':
        return 'Expert Panels'
      case 'GenCC':
        return 'Submissions'
      case 'HPO':
        return 'Phenotypes'
      case 'PubTator':
        return 'Publications'
      case 'PanelApp':
        return 'Panels'
      case 'DiagnosticPanels':
        return 'Providers'
      default:
        return 'Records'
    }
  } else if (type === 'secondary') {
    switch (source.name) {
      case 'ClinGen':
        return 'Classifications'
      case 'GenCC':
        return 'Submitters'
      case 'PanelApp':
        return 'Regions'
      case 'DiagnosticPanels':
        return 'Panels'
      default:
        return ''
    }
  }
  return ''
}

const getMetadataTooltip = (source, type) => {
  // Map metric labels to explanation keys
  const tooltipMap = {
    'Expert Panels': apiResponse.value?.explanations?.expert_panels,
    Classifications: apiResponse.value?.explanations?.classifications,
    Submissions: apiResponse.value?.explanations?.submissions,
    Submitters: apiResponse.value?.explanations?.submitters,
    Phenotypes: apiResponse.value?.explanations?.phenotypes,
    Publications: apiResponse.value?.explanations?.publications,
    Panels: apiResponse.value?.explanations?.panels,
    Regions: apiResponse.value?.explanations?.regions,
    Providers: apiResponse.value?.explanations?.providers
  }

  const label = getMetadataLabel(source, type)
  return tooltipMap[label] || `Number of ${label.toLowerCase()} in this data source`
}

const calculateCoverage = () => {
  // Calculate percentage of genes covered by multiple sources
  // Average gene appears in ~2 sources based on data
  const uniqueGenes = summaryStats.value.unique_genes || 1
  const totalEvidence = apiResponse.value?.total_evidence_records || 0
  const avgSourcesPerGene = totalEvidence / uniqueGenes
  // Convert to percentage (max 6 sources = 100%)
  return Math.min(Math.round((avgSourcesPerGene / 6) * 100), 100)
}

const formatDate = dateStr => {
  if (!dateStr) return 'Never'
  const date = new Date(dateStr)
  if (isNaN(date.getTime())) return 'Never'

  const today = new Date()
  const diffDays = Math.floor((today - date) / (1000 * 60 * 60 * 24))

  if (diffDays === 0) return 'Today'
  if (diffDays === 1) return 'Yesterday'
  if (diffDays < 7) return `${diffDays} days ago`
  if (diffDays < 30) return `${Math.floor(diffDays / 7)} weeks ago`
  return date.toLocaleDateString()
}

onMounted(async () => {
  try {
    console.log('Loading data sources...')
    const response = await datasourceApi.getDataSources()
    console.log('Datasource API response:', response)

    apiResponse.value = response
    dataSources.value = response.sources || []
  } catch (error) {
    console.error('Failed to load data sources:', error)
    // Fallback empty state
    dataSources.value = []
    apiResponse.value = {
      total_active: 0,
      last_pipeline_run: null,
      sources: []
    }
  } finally {
    loading.value = false
  }
})
</script>

<style scoped>
.source-card {
  transition: all 0.3s cubic-bezier(0.4, 0, 0.2, 1);
  overflow: hidden;
}

.source-header {
  border-radius: inherit;
}

.text-white-darken-1 {
  opacity: 0.95;
}

/* Smooth hover transitions */
.source-card:hover {
  transform: translateY(-2px);
}

/* Card height consistency */
.h-100 {
  height: 100%;
}
</style>
