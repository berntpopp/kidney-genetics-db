<template>
  <v-container>
    <!-- Page Header -->
    <v-row>
      <v-col cols="12">
        <!-- Breadcrumbs -->
        <v-breadcrumbs :items="breadcrumbs" density="compact" class="pa-0 mb-2">
          <template #divider>
            <ChevronRight class="size-4" />
          </template>
        </v-breadcrumbs>

        <!-- Header -->
        <div class="d-flex align-center mb-6">
          <LayoutDashboard class="size-6 text-primary mr-3" />
          <div>
            <h1 class="text-h4 font-weight-bold">Data Visualization Dashboard</h1>
            <p class="text-body-2 text-medium-emphasis ma-0">
              Comprehensive analysis of gene-disease associations across multiple genomic data
              sources
            </p>
          </div>
        </div>
      </v-col>
    </v-row>

    <!-- Global Filters -->
    <v-row class="mb-4">
      <v-col cols="12">
        <v-select
          v-model="selectedTiers"
          :items="tierOptions"
          label="Evidence Tier Filter"
          density="compact"
          variant="outlined"
          multiple
          chips
          closable-chips
          clearable
          hint="Select one or more evidence tiers to filter visualizations (multi-select with OR logic)"
          persistent-hint
        >
          <template #item="{ props: itemProps, item }">
            <v-list-item v-bind="itemProps" :subtitle="item.raw.description"></v-list-item>
          </template>
          <template #chip="{ item, props }">
            <v-chip v-bind="props" :color="getTierColor(item.value)" size="small" closable>
              {{ item.title }}
            </v-chip>
          </template>
        </v-select>
      </v-col>
    </v-row>

    <!-- Visualization Tabs -->
    <v-row>
      <v-col cols="12">
        <v-card rounded="lg">
          <v-tabs v-model="activeTab" color="primary" align-tabs="start" show-arrows>
            <v-tab value="overlaps">
              <ChartScatter class="size-5 me-2" />
              Gene Source Overlaps
            </v-tab>
            <v-tab value="distributions">
              <ChartBar class="size-5 me-2" />
              Source Distributions
            </v-tab>
            <v-tab value="composition">
              <Circle class="size-5 me-2" />
              Evidence Composition
            </v-tab>
          </v-tabs>

          <v-tabs-window v-model="activeTab">
            <v-tabs-window-item value="overlaps">
              <div class="pa-4">
                <UpSetChart :selected-tiers="selectedTiers" />
              </div>
            </v-tabs-window-item>

            <v-tabs-window-item value="distributions">
              <div class="pa-4">
                <SourceDistributionsChart
                  v-if="activeTab === 'distributions'"
                  :selected-tiers="selectedTiers"
                />
              </div>
            </v-tabs-window-item>

            <v-tabs-window-item value="composition">
              <div class="pa-4">
                <EvidenceCompositionChart
                  v-if="activeTab === 'composition'"
                  :selected-tiers="selectedTiers"
                />
              </div>
            </v-tabs-window-item>
          </v-tabs-window>
        </v-card>
      </v-col>
    </v-row>
  </v-container>
</template>

<script setup>
import { ChevronRight, LayoutDashboard, ChartScatter, ChartBar, Circle } from 'lucide-vue-next'
import { ref, watch, onMounted, computed } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import {
  UpSetChart,
  SourceDistributionsChart,
  EvidenceCompositionChart
} from '@/components/visualizations'
import { TIER_CONFIG } from '@/utils/evidenceTiers'
import { PUBLIC_BREADCRUMBS } from '@/utils/publicBreadcrumbs'

// Meta
defineOptions({
  name: 'Dashboard'
})

// Router
const route = useRoute()
const router = useRouter()

// Breadcrumbs
const breadcrumbs = PUBLIC_BREADCRUMBS.dashboard

// Reactive data
const activeTab = ref('overlaps')
const selectedTiers = ref([])

// Valid tab values
const validTabs = ['overlaps', 'distributions', 'composition']

// Evidence tier options from config (matching GeneTable)
const tierOptions = computed(() => {
  return Object.entries(TIER_CONFIG).map(([key, config]) => ({
    title: config.label,
    value: key,
    description: config.description
  }))
})

// Get tier color from config (matching GeneTable)
const getTierColor = tierKey => {
  return TIER_CONFIG[tierKey]?.color || 'grey'
}

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
