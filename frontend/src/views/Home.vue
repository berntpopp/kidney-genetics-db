<template>
  <div>
    <!-- Hero Section -->
    <v-container fluid class="pa-0">
      <div class="hero-section text-center py-12 px-4">
        <v-container>
          <KidneyGeneticsLogo 
            :size="120" 
            variant="full"
            :animated="true"
            class="mb-6"
          />
          <h1 class="text-h2 text-md-h1 font-weight-bold mb-4">
            Kidney Genetics Database
          </h1>
          <p class="text-h6 text-md-h5 text-medium-emphasis mx-auto" style="max-width: 800px;">
            A comprehensive platform for exploring kidney disease-related genes
            with evidence-based curation and multi-source integration
          </p>
          <div class="mt-8">
            <v-btn 
              color="primary" 
              size="large" 
              to="/genes"
              prepend-icon="mdi-dna"
              class="mr-3"
            >
              Browse Genes
            </v-btn>
            <v-btn 
              variant="outlined" 
              size="large"
              href="#data-sources"
              prepend-icon="mdi-database"
            >
              View Sources
            </v-btn>
          </div>
        </v-container>
      </div>
    </v-container>

    <v-container class="mt-n8">
      <!-- Statistics Cards with Gradients -->
      <v-row>
        <v-col v-for="(stat, index) in stats" :key="stat.title" cols="12" sm="6" md="3">
          <v-card 
            :elevation="hoveredCard === index ? 4 : 1"
            @mouseenter="hoveredCard = index"
            @mouseleave="hoveredCard = null"
            class="stat-card"
          >
            <div 
              class="stat-gradient pa-4"
              :style="`background: linear-gradient(135deg, ${getGradientColors(stat.color)});`"
            >
              <v-icon 
                :icon="stat.icon" 
                size="x-large" 
                color="white"
                class="mb-2"
              />
              <div class="text-h3 font-weight-bold text-white">
                {{ stat.value }}
              </div>
              <div class="text-body-2 text-white-darken-1">
                {{ stat.title }}
              </div>
            </div>
          </v-card>
        </v-col>
      </v-row>

      <!-- Quick Actions with Better Design -->
      <v-row class="mt-8">
        <v-col cols="12">
          <div class="d-flex align-center mb-4">
            <v-icon icon="mdi-lightning-bolt" size="small" class="mr-2" color="primary" />
            <h2 class="text-h4 font-weight-medium">Quick Actions</h2>
          </div>
        </v-col>
        
        <v-col v-for="action in quickActions" :key="action.title" cols="12" md="4">
          <v-card 
            :elevation="hoveredAction === action.title ? 4 : 1"
            @mouseenter="hoveredAction = action.title"
            @mouseleave="hoveredAction = null"
            class="action-card h-100"
            :class="{ 'action-card--hovered': hoveredAction === action.title }"
          >
            <v-card-item>
              <template v-slot:prepend>
                <v-avatar :color="action.color" size="48">
                  <v-icon :icon="action.icon" color="white" />
                </v-avatar>
              </template>
              <v-card-title class="text-h6">{{ action.title }}</v-card-title>
            </v-card-item>
            <v-card-text class="pb-4">
              {{ action.description }}
            </v-card-text>
            <v-card-actions class="pa-4 pt-0">
              <v-btn 
                :color="action.color" 
                :to="action.to"
                variant="flat"
                block
              >
                {{ action.buttonText }}
                <v-icon icon="mdi-arrow-right" end />
              </v-btn>
            </v-card-actions>
          </v-card>
        </v-col>
      </v-row>

      <!-- Data Sources with Enhanced Visual Design -->
      <v-row class="mt-8" id="data-sources">
        <v-col cols="12">
          <div class="d-flex align-center justify-space-between mb-4">
            <div class="d-flex align-center">
              <v-icon icon="mdi-database" size="small" class="mr-2" color="primary" />
              <h2 class="text-h4 font-weight-medium">Data Sources</h2>
            </div>
            <v-chip 
              v-if="dataSources.length > 0"
              color="primary"
              variant="tonal"
              size="small"
            >
              {{ dataSources.filter(s => s.status === 'active').length }} Active
            </v-chip>
          </div>
        </v-col>
        
        <v-col cols="12">
          <v-card>
            <v-list lines="two" class="pa-0">
              <template v-for="(source, index) in dataSources" :key="source.name">
                <v-list-item 
                  class="py-4"
                  :class="{ 'bg-surface-light': index % 2 === 0 }"
                >
                  <template #prepend>
                    <v-avatar
                      :color="getSourceStatusColor(source.status)"
                      size="40"
                      class="mr-3"
                    >
                      <v-icon 
                        :icon="getSourceStatusIcon(source.status)"
                        color="white"
                        size="small"
                      />
                    </v-avatar>
                  </template>
                  
                  <v-list-item-title class="text-h6 mb-1">
                    {{ source.name }}
                    <v-chip 
                      v-if="source.status === 'active'" 
                      size="small" 
                      color="success"
                      variant="tonal"
                      class="ml-2"
                    >
                      <v-icon icon="mdi-dna" size="x-small" start />
                      {{ source.gene_count }} genes
                    </v-chip>
                    <v-chip 
                      v-else-if="source.status === 'error'" 
                      size="small" 
                      color="error"
                      variant="tonal"
                      class="ml-2"
                    >
                      Error
                    </v-chip>
                    <v-chip 
                      v-else-if="source.status === 'pending'" 
                      size="small" 
                      color="warning"
                      variant="tonal"
                      class="ml-2"
                    >
                      Coming Soon
                    </v-chip>
                  </v-list-item-title>
                  
                  <v-list-item-subtitle>
                    <div>{{ source.description }}</div>
                    <div class="mt-1">
                      <v-chip
                        v-if="source.metadata?.panel_count"
                        size="x-small"
                        variant="text"
                        prepend-icon="mdi-view-dashboard"
                        class="mr-2"
                      >
                        {{ source.metadata.panel_count }} panels
                      </v-chip>
                      <v-chip
                        v-if="source.metadata?.total_publications"
                        size="x-small"
                        variant="text"
                        prepend-icon="mdi-file-document"
                      >
                        {{ source.metadata.total_publications.toLocaleString() }} publications
                      </v-chip>
                      <v-chip
                        v-if="source.last_updated"
                        size="x-small"
                        variant="text"
                        prepend-icon="mdi-clock-outline"
                        class="ml-2"
                      >
                        Updated {{ formatDate(source.last_updated) }}
                      </v-chip>
                    </div>
                  </v-list-item-subtitle>
                </v-list-item>
                <v-divider v-if="index < dataSources.length - 1" />
              </template>
            </v-list>
          </v-card>
        </v-col>
      </v-row>

      <!-- Recent Activity Section -->
      <v-row class="mt-8 mb-8">
        <v-col cols="12">
          <div class="d-flex align-center mb-4">
            <v-icon icon="mdi-update" size="small" class="mr-2" color="primary" />
            <h2 class="text-h4 font-weight-medium">Recent Activity</h2>
          </div>
        </v-col>
        
        <v-col cols="12">
          <v-card>
            <v-card-text>
              <v-timeline side="end" density="compact">
                <v-timeline-item
                  v-for="(activity, i) in recentActivities"
                  :key="i"
                  :dot-color="activity.color"
                  :icon="activity.icon"
                  size="small"
                >
                  <div class="text-body-2">
                    <strong>{{ activity.title }}</strong>
                    <div class="text-caption text-medium-emphasis">
                      {{ activity.time }}
                    </div>
                  </div>
                </v-timeline-item>
              </v-timeline>
            </v-card-text>
          </v-card>
        </v-col>
      </v-row>
    </v-container>
  </div>
</template>

<script setup>
import { ref, onMounted } from 'vue'
import { geneApi } from '../api/genes'
import { datasourceApi } from '../api/datasources'
import KidneyGeneticsLogo from '@/components/KidneyGeneticsLogo.vue'

const hoveredCard = ref(null)
const hoveredAction = ref(null)

const stats = ref([
  { 
    title: 'Total Genes', 
    value: 0, 
    color: 'primary',
    icon: 'mdi-dna'
  },
  { 
    title: 'Active Sources', 
    value: 0, 
    color: 'success',
    icon: 'mdi-database-check'
  },
  { 
    title: 'Gene Panels', 
    value: 0, 
    color: 'info',
    icon: 'mdi-view-dashboard'
  },
  { 
    title: 'Last Update', 
    value: 'Loading...', 
    color: 'secondary',
    icon: 'mdi-clock-check'
  }
])

const quickActions = [
  {
    title: 'Browse Genes',
    description: 'Explore the complete list of kidney disease-related genes with comprehensive evidence',
    icon: 'mdi-dna',
    color: 'primary',
    to: '/genes',
    buttonText: 'View All Genes'
  },
  {
    title: 'Search Database',
    description: 'Find specific genes by symbol, HGNC ID, or filter by evidence score and sources',
    icon: 'mdi-magnify',
    color: 'success',
    to: '/genes',
    buttonText: 'Start Searching'
  },
  {
    title: 'Learn More',
    description: 'Discover the methodology, data sources, and team behind this comprehensive database',
    icon: 'mdi-information',
    color: 'secondary',
    to: '/about',
    buttonText: 'About Project'
  }
]

const dataSources = ref([])

const recentActivities = ref([
  {
    title: 'Database initialized',
    time: 'System startup',
    icon: 'mdi-rocket-launch',
    color: 'success'
  },
  {
    title: 'PanelApp data loaded',
    time: 'Data source connected',
    icon: 'mdi-database-plus',
    color: 'primary'
  },
  {
    title: 'HPO data loaded',
    time: 'Data source connected',
    icon: 'mdi-database-plus',
    color: 'primary'
  }
])

const getGradientColors = (color) => {
  const gradients = {
    primary: '#0EA5E9, #0284C7',
    success: '#10B981, #059669',
    info: '#3B82F6, #2563EB',
    secondary: '#8B5CF6, #7C3AED',
    warning: '#F59E0B, #D97706',
    error: '#EF4444, #DC2626'
  }
  return gradients[color] || gradients.primary
}

const formatDate = (dateStr) => {
  if (!dateStr) return 'Never'
  const date = new Date(dateStr)
  const today = new Date()
  const diffDays = Math.floor((today - date) / (1000 * 60 * 60 * 24))
  
  if (diffDays === 0) return 'today'
  if (diffDays === 1) return 'yesterday'
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
    active: 'mdi-check',
    error: 'mdi-alert',
    pending: 'mdi-clock',
    inactive: 'mdi-circle-outline'
  }
  return icons[status] || 'mdi-help-circle'
}

onMounted(async () => {
  try {
    // Fetch gene stats
    const geneResponse = await geneApi.getGenes({ perPage: 1 })
    stats.value[0].value = geneResponse.total.toLocaleString()
    
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

    // Update recent activities with real data
    if (sourceResponse.last_pipeline_run) {
      recentActivities.value.unshift({
        title: 'Pipeline executed',
        time: formatDate(sourceResponse.last_pipeline_run),
        icon: 'mdi-cog-sync',
        color: 'info'
      })
    }
  } catch (error) {
    console.error('Error fetching stats:', error)
    stats.value[3].value = 'Error'
  }
})
</script>

<style scoped>
.hero-section {
  background: linear-gradient(135deg, 
    rgb(var(--v-theme-primary-lighten-3)) 0%, 
    rgb(var(--v-theme-surface)) 100%);
}

.v-theme--dark .hero-section {
  background: linear-gradient(135deg, 
    rgba(var(--v-theme-primary), 0.1) 0%, 
    rgb(var(--v-theme-background)) 100%);
}

.stat-card {
  transition: all 0.3s cubic-bezier(0.4, 0, 0.2, 1);
  overflow: hidden;
}

.stat-gradient {
  text-align: center;
  border-radius: inherit;
}

.action-card {
  transition: all 0.3s cubic-bezier(0.4, 0, 0.2, 1);
  display: flex;
  flex-direction: column;
}

.action-card--hovered {
  transform: translateY(-4px);
}

.text-white-darken-1 {
  opacity: 0.95;
}

/* Smooth scroll for anchor links */
html {
  scroll-behavior: smooth;
}
</style>