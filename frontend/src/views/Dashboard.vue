<template>
  <v-container fluid class="dashboard-container">
    <!-- Page Header -->
    <v-row class="mb-6">
      <v-col cols="12">
        <div class="d-flex align-center mb-2">
          <v-icon class="me-3" size="large" color="primary">mdi-view-dashboard</v-icon>
          <h1 class="text-h4 font-weight-bold">Data Visualization Dashboard</h1>
        </div>
        <p class="text-body-1 text-medium-emphasis">
          Comprehensive analysis of gene-disease associations across multiple genomic data sources
        </p>
      </v-col>
    </v-row>

    <!-- Visualization Tabs -->
    <v-row>
      <v-col cols="12">
        <v-card>
          <v-tabs v-model="activeTab" color="primary" align-tabs="start" show-arrows>
            <v-tab value="overlaps">
              <v-icon class="me-2">mdi-chart-scatter-plot</v-icon>
              Gene Source Overlaps
            </v-tab>
            <v-tab value="distributions">
              <v-icon class="me-2">mdi-chart-bar</v-icon>
              Source Distributions
            </v-tab>
            <v-tab value="composition">
              <v-icon class="me-2">mdi-chart-donut</v-icon>
              Evidence Composition
            </v-tab>
          </v-tabs>

          <v-tabs-window v-model="activeTab">
            <v-tabs-window-item value="overlaps">
              <div class="pa-4">
                <UpSetChart />
              </div>
            </v-tabs-window-item>

            <v-tabs-window-item value="distributions">
              <div class="pa-4">
                <SourceDistributionsChart v-if="activeTab === 'distributions'" />
              </div>
            </v-tabs-window-item>

            <v-tabs-window-item value="composition">
              <div class="pa-4">
                <EvidenceCompositionChart v-if="activeTab === 'composition'" />
              </div>
            </v-tabs-window-item>
          </v-tabs-window>
        </v-card>
      </v-col>
    </v-row>
  </v-container>
</template>

<script setup>
import { ref, watch, onMounted } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import {
  UpSetChart,
  SourceDistributionsChart,
  EvidenceCompositionChart
} from '@/components/visualizations'

// Meta
defineOptions({
  name: 'Dashboard'
})

// Router
const route = useRoute()
const router = useRouter()

// Reactive data
const activeTab = ref('overlaps')

// Valid tab values
const validTabs = ['overlaps', 'distributions', 'composition']

// Initialize tab from URL
onMounted(() => {
  const urlTab = route.query.tab
  if (urlTab && validTabs.includes(urlTab)) {
    activeTab.value = urlTab
  }
})

// Watch for tab changes and update URL
watch(activeTab, newTab => {
  if (route.query.tab !== newTab) {
    router.push({
      path: route.path,
      query: { ...route.query, tab: newTab }
    })
  }
})

// Watch for URL changes and update tab
watch(
  () => route.query.tab,
  newTab => {
    if (newTab && validTabs.includes(newTab) && activeTab.value !== newTab) {
      activeTab.value = newTab
    }
  }
)
</script>

<style scoped>
.dashboard-container {
  min-height: calc(100vh - 64px - 80px); /* Account for header and footer */
  padding: 24px;
}

/* Responsive adjustments */
@media (max-width: 600px) {
  .dashboard-container {
    padding: 16px;
  }
}

/* Animation for visualization cards */
.v-card {
  transition:
    transform 0.2s ease,
    box-shadow 0.2s ease;
}

.v-card:hover {
  transform: translateY(-2px);
  box-shadow: 0 4px 20px rgba(0, 0, 0, 0.1);
}
</style>
