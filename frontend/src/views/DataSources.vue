<template>
  <v-container>
    <v-row>
      <v-col cols="12">
        <h1 class="text-h4 mb-4">Data Sources</h1>
      </v-col>
    </v-row>

    <v-row>
      <v-col cols="12">
        <v-card>
          <v-card-title>
            <v-icon left>mdi-database</v-icon>
            Active Data Sources
          </v-card-title>
          <v-card-text>
            <v-list>
              <v-list-item v-for="source in dataSources" :key="source.name" class="mb-2">
                <template #prepend>
                  <v-icon :color="getStatusColor(source.status)">
                    {{ getSourceIcon(source.type) }}
                  </v-icon>
                </template>

                <v-list-item-title class="font-weight-bold">
                  {{ source.name }}
                </v-list-item-title>

                <v-list-item-subtitle>
                  {{ source.description }}
                  <v-chip v-if="source.url" size="x-small" class="ml-2" variant="outlined">
                    {{ source.url }}
                  </v-chip>
                </v-list-item-subtitle>

                <template #append>
                  <div class="text-right">
                    <v-chip :color="getStatusColor(source.status)" size="small" class="mr-2">
                      {{ source.status }}
                    </v-chip>
                    <div class="text-caption mt-1">Last update: {{ source.lastUpdate }}</div>
                    <div class="text-caption">
                      {{ source.stats.panels || source.stats.companies || 0 }} sources,
                      {{ source.stats.genes }} genes
                    </div>
                  </div>
                </template>
              </v-list-item>
            </v-list>
          </v-card-text>
        </v-card>
      </v-col>
    </v-row>

    <v-row class="mt-4">
      <v-col cols="12" md="6">
        <v-card>
          <v-card-title>
            <v-icon left>mdi-sync</v-icon>
            Update Pipeline
          </v-card-title>
          <v-card-text>
            <v-btn color="primary" :loading="updating" block @click="updateAllSources">
              <v-icon left>mdi-refresh</v-icon>
              Update All Sources
            </v-btn>
            <v-divider class="my-3"></v-divider>
            <div class="text-body-2 mb-2">Update Individual Sources:</div>
            <v-btn
              v-for="source in ['panelapp', 'hpo', 'pubtator']"
              :key="source"
              size="small"
              variant="outlined"
              class="mr-2 mb-2"
              :loading="updatingSource === source"
              @click="updateSource(source)"
            >
              {{ source }}
            </v-btn>
          </v-card-text>
        </v-card>
      </v-col>

      <v-col cols="12" md="6">
        <v-card>
          <v-card-title>
            <v-icon left>mdi-chart-line</v-icon>
            Statistics
          </v-card-title>
          <v-card-text>
            <v-list density="compact">
              <v-list-item>
                <v-list-item-title>Total Genes</v-list-item-title>
                <template #append>
                  <span class="font-weight-bold">{{ totalStats.genes }}</span>
                </template>
              </v-list-item>
              <v-list-item>
                <v-list-item-title>Evidence Records</v-list-item-title>
                <template #append>
                  <span class="font-weight-bold">{{ totalStats.evidence }}</span>
                </template>
              </v-list-item>
              <v-list-item>
                <v-list-item-title>Active Sources</v-list-item-title>
                <template #append>
                  <span class="font-weight-bold">{{ totalStats.sources }}</span>
                </template>
              </v-list-item>
              <v-list-item>
                <v-list-item-title>Last Pipeline Run</v-list-item-title>
                <template #append>
                  <span class="text-caption">{{ lastPipelineRun }}</span>
                </template>
              </v-list-item>
            </v-list>
          </v-card-text>
        </v-card>
      </v-col>
    </v-row>
  </v-container>
</template>

<script setup>
import { ref, computed, onMounted } from 'vue'
import { genesApi } from '@/api/genes'

const dataSources = ref([
  {
    name: 'PanelApp',
    type: 'API',
    status: 'Active',
    lastUpdate: '2024-01-16',
    description: 'Expert-curated gene panels from UK Genomics England and Australian Genomics',
    url: 'panelapp.genomicsengland.co.uk',
    stats: { panels: 19, genes: 318 }
  },
  {
    name: 'HPO',
    type: 'API/Files',
    status: 'Partial',
    lastUpdate: '2024-01-16',
    description: 'Human Phenotype Ontology - kidney phenotype associations',
    url: 'hpo.jax.org',
    stats: { panels: 0, genes: 4 }
  },
  {
    name: 'PubTator',
    type: 'API',
    status: 'Inactive',
    lastUpdate: 'N/A',
    description: 'Literature mining from PubMed Central',
    url: 'ncbi.nlm.nih.gov/research/pubtator',
    stats: { panels: 0, genes: 0 }
  }
])

const updating = ref(false)
const updatingSource = ref(null)
const lastPipelineRun = ref('2024-01-16 09:12:07')

const totalStats = computed(() => {
  const activeSourceCount = dataSources.value.filter(s => s.status !== 'Inactive').length
  const totalGenes = dataSources.value.reduce((sum, s) => sum + s.stats.genes, 0)
  const totalEvidence = dataSources.value.reduce((sum, s) => sum + s.stats.genes, 0) // Simplified

  return {
    genes: totalGenes,
    evidence: totalEvidence,
    sources: activeSourceCount
  }
})

const getStatusColor = status => {
  switch (status) {
    case 'Active':
      return 'success'
    case 'Partial':
      return 'warning'
    case 'Inactive':
      return 'error'
    default:
      return 'grey'
  }
}

const getSourceIcon = type => {
  switch (type) {
    case 'API':
      return 'mdi-api'
    case 'Manual':
      return 'mdi-file-document'
    case 'API/Files':
      return 'mdi-file-sync'
    default:
      return 'mdi-database'
  }
}

const updateAllSources = async () => {
  updating.value = true
  try {
    // In real implementation, would call API to trigger pipeline
    console.log('Updating all sources...')
    await new Promise(resolve => setTimeout(resolve, 2000))
  } finally {
    updating.value = false
  }
}

const updateSource = async source => {
  updatingSource.value = source
  try {
    // In real implementation, would call API to trigger specific source update
    console.log(`Updating ${source}...`)
    await new Promise(resolve => setTimeout(resolve, 1500))
  } finally {
    updatingSource.value = null
  }
}

onMounted(async () => {
  // Load actual stats from API
  try {
    const stats = await genesApi.getStats()
    if (stats) {
      // Update stats based on API response
      console.log('Loaded stats:', stats)
    }
  } catch (error) {
    console.error('Failed to load stats:', error)
  }
})
</script>
