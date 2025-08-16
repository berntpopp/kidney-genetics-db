<template>
  <v-container>
    <v-row>
      <v-col cols="12">
        <h1 class="text-h3 mb-4">Kidney Genetics Database</h1>
        <p class="text-subtitle-1 mb-6">
          A comprehensive platform for exploring kidney disease-related genes
        </p>
      </v-col>
    </v-row>

    <!-- Statistics Cards -->
    <v-row>
      <v-col v-for="stat in stats" :key="stat.title" cols="12" md="3">
        <v-card>
          <v-card-text class="text-center">
            <div class="text-h2 mb-2" :class="`text-${stat.color}`">
              {{ stat.value }}
            </div>
            <div class="text-subtitle-1">{{ stat.title }}</div>
          </v-card-text>
        </v-card>
      </v-col>
    </v-row>

    <!-- Quick Actions -->
    <v-row class="mt-6">
      <v-col cols="12">
        <h2 class="text-h5 mb-4">Quick Actions</h2>
      </v-col>
      <v-col cols="12" md="4">
        <v-card>
          <v-card-title>
            <v-icon start>mdi-dna</v-icon>
            Browse Genes
          </v-card-title>
          <v-card-text>
            Explore the complete list of kidney disease-related genes with evidence
          </v-card-text>
          <v-card-actions>
            <v-btn color="primary" to="/genes"> View Genes </v-btn>
          </v-card-actions>
        </v-card>
      </v-col>
      <v-col cols="12" md="4">
        <v-card>
          <v-card-title>
            <v-icon start>mdi-magnify</v-icon>
            Search Database
          </v-card-title>
          <v-card-text>
            Search for specific genes by symbol, HGNC ID, or evidence score
          </v-card-text>
          <v-card-actions>
            <v-btn color="primary" to="/genes"> Search Now </v-btn>
          </v-card-actions>
        </v-card>
      </v-col>
      <v-col cols="12" md="4">
        <v-card>
          <v-card-title>
            <v-icon start>mdi-information</v-icon>
            About Project
          </v-card-title>
          <v-card-text>
            Learn more about the kidney genetics database and data sources
          </v-card-text>
          <v-card-actions>
            <v-btn color="primary" to="/about"> Learn More </v-btn>
          </v-card-actions>
        </v-card>
      </v-col>
    </v-row>

    <!-- Data Sources -->
    <v-row class="mt-6">
      <v-col cols="12">
        <h2 class="text-h5 mb-4">Data Sources</h2>
        <v-list>
          <v-list-item v-for="source in dataSources" :key="source.name">
            <template #prepend>
              <v-icon :color="getSourceStatusColor(source.status)">
                {{ getSourceStatusIcon(source.status) }}
              </v-icon>
            </template>
            <v-list-item-title>
              {{ source.name }}
              <v-chip 
                v-if="source.status === 'active'" 
                size="x-small" 
                color="success" 
                class="ml-2"
              >
                {{ source.gene_count }} genes
              </v-chip>
              <v-chip 
                v-else-if="source.status === 'error'" 
                size="x-small" 
                color="error" 
                class="ml-2"
              >
                Error
              </v-chip>
              <v-chip 
                v-else-if="source.status === 'pending'" 
                size="x-small" 
                color="warning" 
                class="ml-2"
              >
                Not Implemented
              </v-chip>
            </v-list-item-title>
            <v-list-item-subtitle>
              {{ source.description }}
              <span v-if="source.metadata?.panel_count" class="text-caption">
                ({{ source.metadata.panel_count }} panels)
              </span>
              <span v-if="source.metadata?.total_publications" class="text-caption">
                ({{ source.metadata.total_publications.toLocaleString() }} publications)
              </span>
            </v-list-item-subtitle>
          </v-list-item>
        </v-list>
      </v-col>
    </v-row>
  </v-container>
</template>

<script setup>
import { ref, onMounted, computed } from 'vue'
import { geneApi } from '../api/genes'
import { datasourceApi } from '../api/datasources'

const stats = ref([
  { title: 'Total Genes', value: 0, color: 'primary' },
  { title: 'Active Sources', value: 0, color: 'secondary' },
  { title: 'Gene Panels', value: 0, color: 'info' },
  { title: 'Last Update', value: 'Loading...', color: 'success' }
])

const dataSources = ref([])

const formatDate = (dateStr) => {
  if (!dateStr) return 'Never'
  const date = new Date(dateStr)
  const today = new Date()
  const diffDays = Math.floor((today - date) / (1000 * 60 * 60 * 24))
  
  if (diffDays === 0) return 'Today'
  if (diffDays === 1) return 'Yesterday'
  if (diffDays < 7) return `${diffDays} days ago`
  if (diffDays < 30) return `${Math.floor(diffDays / 7)} weeks ago`
  return date.toLocaleDateString()
}

const getSourceStatusColor = (status) => {
  const colors = {
    active: 'success',
    error: 'error',
    pending: 'warning',
    inactive: 'grey'
  }
  return colors[status] || 'grey'
}

const getSourceStatusIcon = (status) => {
  const icons = {
    active: 'mdi-check-circle',
    error: 'mdi-alert-circle',
    pending: 'mdi-clock-outline',
    inactive: 'mdi-circle-outline'
  }
  return icons[status] || 'mdi-help-circle'
}

onMounted(async () => {
  try {
    // Fetch gene stats
    const geneResponse = await geneApi.getGenes({ perPage: 1 })
    stats.value[0].value = geneResponse.total
    
    // Fetch data source information
    const sourceResponse = await datasourceApi.getDataSources()
    
    // Update stats
    stats.value[1].value = sourceResponse.total_active
    
    // Map data sources to display format
    dataSources.value = sourceResponse.sources.map(source => ({
      name: source.display_name,
      description: source.description,
      status: source.status,
      gene_count: source.stats?.gene_count || 0,
      last_updated: source.stats?.last_updated,
      metadata: source.stats?.metadata
    }))
    
    // Calculate total panels from PanelApp metadata
    const panelApp = sourceResponse.sources.find(s => s.name === 'PanelApp')
    if (panelApp?.stats?.metadata?.panel_count) {
      stats.value[2].value = panelApp.stats.metadata.panel_count
    }
    
    // Format last update
    if (sourceResponse.last_pipeline_run) {
      stats.value[3].value = formatDate(sourceResponse.last_pipeline_run)
    } else {
      // Use most recent source update
      const mostRecent = sourceResponse.sources
        .filter(s => s.stats?.last_updated)
        .map(s => new Date(s.stats.last_updated))
        .sort((a, b) => b - a)[0]
      
      stats.value[3].value = mostRecent ? formatDate(mostRecent) : 'Never'
    }
  } catch (error) {
    console.error('Error fetching stats:', error)
    stats.value[3].value = 'Error'
  }
})
</script>
