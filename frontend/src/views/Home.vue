<template>
  <div>
    <!-- Hero Section -->
    <v-container fluid class="pa-0">
      <div class="hero-section text-center py-12 px-4">
        <v-container>
          <!-- Logo with integrated text (horizontal layout - text right of kidney) -->
          <div class="d-flex align-center justify-center mb-6">
            <KGDBLogo
              :size="logoSize"
              variant="with-text"
              text-layout="horizontal"
              :animated="true"
              :breathing="true"
              :interactive="true"
              @click="router.push('/')"
            />
          </div>

          <p class="text-h6 text-md-h5 text-medium-emphasis mx-auto" style="max-width: 600px">
            Evidence-based kidney disease gene curation with multi-source integration
          </p>
        </v-container>
      </div>
    </v-container>

    <v-container class="mt-n8">
      <!-- Statistics Cards with Gradients -->
      <v-row>
        <v-col v-for="(stat, index) in stats" :key="stat.title" cols="12" sm="6" md="4">
          <v-card
            :elevation="hoveredCard === index ? 4 : 1"
            :class="['stat-card', { 'stat-card-clickable': stat.route }]"
            @mouseenter="hoveredCard = index"
            @mouseleave="hoveredCard = null"
            @click="stat.route ? router.push(stat.route) : null"
          >
            <div
              class="stat-gradient pa-4"
              :style="`background: linear-gradient(135deg, ${getGradientColors(stat.color)});`"
            >
              <v-icon :icon="stat.icon" size="x-large" color="white" class="mb-2" />
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

      <!-- Key Benefits -->
      <v-row class="mt-8">
        <v-col cols="12">
          <h2 class="text-h4 font-weight-medium text-center mb-6">Why Use This Database?</h2>
        </v-col>

        <v-col v-for="benefit in keyBenefits" :key="benefit.title" cols="12" md="4">
          <div class="text-center pa-4">
            <v-avatar :color="benefit.color" size="64" class="mb-4">
              <v-icon :icon="benefit.icon" color="white" size="large" />
            </v-avatar>
            <h3 class="text-h6 mb-2">{{ benefit.title }}</h3>
            <p class="text-body-2 text-medium-emphasis">{{ benefit.description }}</p>
          </div>
        </v-col>
      </v-row>
    </v-container>
  </div>
</template>

<script setup>
import { ref, computed, onMounted } from 'vue'
import { useDisplay } from 'vuetify'
import { useRouter } from 'vue-router'
import { datasourceApi } from '../api/datasources'
import { KGDBLogo } from '@/components/branding'

const router = useRouter()
const { xs, sm } = useDisplay()
const hoveredCard = ref(null)

// Responsive logo sizing
const logoSize = computed(() => {
  if (xs.value) return 60 // Mobile - smaller to fit viewport
  if (sm.value) return 100 // Tablet
  return 180 // Desktop
})

const stats = ref([
  {
    title: 'Genes with Evidence',
    value: 0,
    color: 'primary',
    icon: 'mdi-dna',
    route: '/genes'
  },
  {
    title: 'Active Sources',
    value: 0,
    color: 'success',
    icon: 'mdi-database-check',
    route: '/data-sources'
  },
  {
    title: 'Last Update',
    value: 'Loading...',
    color: 'info',
    icon: 'mdi-clock-check',
    route: null
  }
])

const keyBenefits = [
  {
    title: 'Evidence-Based',
    description:
      'Curated gene-disease associations with rigorous evidence scoring and quality assessment',
    icon: 'mdi-shield-check',
    color: 'success'
  },
  {
    title: 'Multi-Source',
    description: 'Integrated data from PanelApp, HPO, literature mining, and clinical sources',
    icon: 'mdi-database-sync',
    color: 'primary'
  },
  {
    title: 'Research-Grade',
    description: 'Professional-quality curation workflow with complete audit trails and versioning',
    icon: 'mdi-microscope',
    color: 'secondary'
  }
]

const getGradientColors = color => {
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

const formatDate = dateStr => {
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

onMounted(async () => {
  try {
    // Fetch data source information (includes all stats now)
    const sourceResponse = await datasourceApi.getDataSources()

    // Update Total Genes using the actual unique count from API
    stats.value[0].value = (sourceResponse.total_unique_genes || 0).toLocaleString()

    // Update Active Sources
    stats.value[1].value = sourceResponse.total_active

    // Format last update - use last_data_update from API
    if (sourceResponse.last_data_update) {
      stats.value[2].value = formatDate(sourceResponse.last_data_update)
    } else if (sourceResponse.last_pipeline_run) {
      stats.value[2].value = formatDate(sourceResponse.last_pipeline_run)
    } else {
      // Fallback to most recent source update
      const mostRecent = sourceResponse.sources
        .filter(s => s.stats?.last_updated)
        .map(s => new Date(s.stats.last_updated))
        .sort((a, b) => b - a)[0]

      stats.value[2].value = mostRecent ? formatDate(mostRecent) : 'Never'
    }
  } catch (error) {
    window.logService.error('Error fetching stats:', error)
    stats.value[2].value = 'Error'
  }
})
</script>

<style scoped>
.hero-section {
  background: linear-gradient(
    135deg,
    rgb(var(--v-theme-primary-lighten-3)) 0%,
    rgb(var(--v-theme-surface)) 100%
  );
}

.v-theme--dark .hero-section {
  background: linear-gradient(
    135deg,
    rgba(var(--v-theme-primary), 0.1) 0%,
    rgb(var(--v-theme-background)) 100%
  );
}

.stat-card {
  transition: all 0.3s cubic-bezier(0.4, 0, 0.2, 1);
  overflow: hidden;
}

/* Clickable cards get pointer cursor and subtle hover effects */
.stat-card-clickable {
  cursor: pointer;
}

.stat-card-clickable:hover {
  transform: translateY(-4px) scale(1.02);
}

.stat-card-clickable:active {
  transform: translateY(-2px) scale(1.01);
  transition-duration: 0.1s;
}

.stat-gradient {
  text-align: center;
  border-radius: inherit;
  transition: all 0.3s cubic-bezier(0.4, 0, 0.2, 1);
}

.stat-card-clickable:hover .stat-gradient {
  filter: brightness(1.05);
}

.text-white-darken-1 {
  opacity: 0.95;
}

/* Focus states for keyboard navigation - Following Style Guide */
.stat-card-clickable:focus-visible {
  outline: 2px solid rgb(var(--v-theme-primary));
  outline-offset: 2px;
}

/* Motion preferences - Following Style Guide */
@media (prefers-reduced-motion: reduce) {
  .stat-card,
  .stat-gradient {
    transition-duration: 0.01ms !important;
  }

  .stat-card-clickable:hover {
    transform: none;
  }
}

/* Smooth scroll for anchor links */
html {
  scroll-behavior: smooth;
}
</style>
