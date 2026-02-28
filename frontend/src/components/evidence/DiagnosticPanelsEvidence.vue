<template>
  <div class="diagnostic-panels-evidence">
    <!-- Providers with Panels -->
    <div v-if="Object.keys(providerPanels).length > 0" class="mb-4">
      <div class="text-subtitle-2 font-weight-medium mb-2">
        <Building2 class="size-4 mr-1 inline-block align-middle" />
        Providers ({{ uniqueProviders }})
      </div>

      <v-expansion-panels v-if="uniqueProviders > 1" variant="accordion" class="mb-2">
        <v-expansion-panel
          v-for="(panelList, provider) in providerPanels"
          :key="provider"
          class="mb-1"
        >
          <v-expansion-panel-title class="text-body-2">
            <div class="d-flex align-center">
              <Building class="size-4 mr-2" />
              <strong>{{ formatProviderName(provider) }}</strong>
              <v-chip size="x-small" variant="outlined" class="ml-2">
                {{ panelList.length }} panel{{ panelList.length > 1 ? 's' : '' }}
              </v-chip>
            </div>
          </v-expansion-panel-title>
          <v-expansion-panel-text>
            <div class="panels-grid">
              <v-chip
                v-for="(panel, index) in panelList"
                :key="index"
                size="small"
                variant="tonal"
                color="primary"
                class="ma-1"
              >
                {{ panel }}
              </v-chip>
            </div>
          </v-expansion-panel-text>
        </v-expansion-panel>
      </v-expansion-panels>

      <!-- Single provider - show directly -->
      <div v-else-if="uniqueProviders === 1">
        <div v-for="(panelList, provider) in providerPanels" :key="provider">
          <div class="text-body-2 font-weight-medium mb-2">
            <Building class="size-4 mr-1 inline-block align-middle" />
            {{ formatProviderName(provider) }}
          </div>
          <div class="panels-grid">
            <v-chip
              v-for="(panel, index) in panelList"
              :key="index"
              size="small"
              variant="outlined"
              class="ma-1"
            >
              {{ panel }}
            </v-chip>
          </div>
        </div>
      </div>
    </div>

    <!-- Gene Information -->
    <div v-if="evidenceData.metadata" class="mb-4">
      <div class="text-subtitle-2 font-weight-medium mb-2">
        <Dna class="size-4 mr-1 inline-block align-middle" />
        Gene Information
      </div>
      <v-list density="compact" class="bg-transparent">
        <v-list-item v-if="evidenceData.metadata.approved_symbol">
          <template #prepend>
            <span class="text-caption text-medium-emphasis mr-2">Symbol:</span>
          </template>
          <v-list-item-title class="text-body-2">
            {{ evidenceData.metadata.approved_symbol }}
          </v-list-item-title>
        </v-list-item>
        <v-list-item v-if="evidenceData.metadata.hgnc_id">
          <template #prepend>
            <span class="text-caption text-medium-emphasis mr-2">HGNC ID:</span>
          </template>
          <v-list-item-title class="text-body-2">
            <a
              :href="`https://www.genenames.org/data/gene-symbol-report/#!/hgnc_id/${evidenceData.metadata.hgnc_id}`"
              target="_blank"
              class="text-primary text-decoration-none"
            >
              {{ evidenceData.metadata.hgnc_id }}
              <ExternalLink class="size-3 ml-1 inline-block align-middle" />
            </a>
          </v-list-item-title>
        </v-list-item>
      </v-list>
    </div>

    <!-- Statistics -->
    <v-row v-if="Object.keys(providerPanels).length > 0" class="mt-4">
      <v-col cols="6">
        <div class="text-center">
          <div class="text-h6 font-weight-bold text-primary">{{ totalPanels }}</div>
          <div class="text-caption text-medium-emphasis">Total Panels</div>
        </div>
      </v-col>
      <v-col cols="6">
        <div class="text-center">
          <div class="text-h6 font-weight-bold text-primary">{{ uniqueProviders }}</div>
          <div class="text-caption text-medium-emphasis">Providers</div>
        </div>
      </v-col>
    </v-row>
  </div>
</template>

<script setup>
import { computed } from 'vue'
import { Building2, Building, Dna, ExternalLink } from 'lucide-vue-next'

const props = defineProps({
  evidenceData: {
    type: Object,
    required: true
  },
  sourceName: {
    type: String,
    required: true
  }
})

// Extract providers directly from the new structure
const providerPanels = computed(() => {
  // New structure: provider_panels is a direct mapping of provider -> panels array
  if (props.evidenceData?.provider_panels) {
    const providers = {}

    // Process each provider and their panels
    for (const [provider, panels] of Object.entries(props.evidenceData.provider_panels)) {
      // Panels are already strings in our structure
      providers[provider] = Array.isArray(panels) ? panels : []
    }

    return providers
  }

  // Fallback for legacy structure if it exists
  if (props.evidenceData?.providers && Array.isArray(props.evidenceData.providers)) {
    // Old structure had separate providers and panels arrays
    const providers = {}
    for (const provider of props.evidenceData.providers) {
      providers[provider] = props.evidenceData.panels || []
    }
    return providers
  }

  return {}
})

const uniqueProviders = computed(() => {
  return Object.keys(providerPanels.value).length
})

const totalPanels = computed(() => {
  // Count unique panels across all providers
  const uniquePanels = new Set()
  for (const panels of Object.values(providerPanels.value)) {
    panels.forEach(panel => uniquePanels.add(panel))
  }
  return uniquePanels.size
})

// Helper functions
const formatProviderName = provider => {
  if (!provider) return ''
  // Replace underscores with spaces and capitalize each word
  return provider
    .split('_')
    .map(word => word.charAt(0).toUpperCase() + word.slice(1).toLowerCase())
    .join(' ')
}
</script>

<style scoped>
.diagnostic-panels-evidence {
  padding: 0;
}

.panels-grid {
  display: flex;
  flex-wrap: wrap;
  gap: 4px;
}

.v-list {
  padding: 0;
}

.v-list-item {
  min-height: 32px;
  padding: 4px 0;
}
</style>
