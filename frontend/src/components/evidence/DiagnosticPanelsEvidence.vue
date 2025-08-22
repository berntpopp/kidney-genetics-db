<template>
  <div class="diagnostic-panels-evidence">
    <!-- Providers with Panels -->
    <div v-if="Object.keys(providerPanels).length > 0" class="mb-4">
      <div class="text-subtitle-2 font-weight-medium mb-2">
        <v-icon icon="mdi-domain" size="small" class="mr-1" />
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
              <v-icon icon="mdi-hospital-building" size="small" class="mr-2" />
              <strong>{{ provider }}</strong>
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
            <v-icon icon="mdi-hospital-building" size="small" class="mr-1" />
            {{ provider }}
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

    <!-- Confidence Level -->
    <div v-if="evidenceData.confidence" class="mb-4">
      <div class="text-subtitle-2 font-weight-medium mb-2">
        <v-icon icon="mdi-shield-check" size="small" class="mr-1" />
        Confidence Level
      </div>
      <v-chip :color="getConfidenceColor(evidenceData.confidence)" variant="tonal" size="small">
        {{ capitalizeFirst(evidenceData.confidence) }}
      </v-chip>
    </div>

    <!-- Gene Information -->
    <div v-if="evidenceData.metadata" class="mb-4">
      <div class="text-subtitle-2 font-weight-medium mb-2">
        <v-icon icon="mdi-dna" size="small" class="mr-1" />
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
              <v-icon icon="mdi-open-in-new" size="x-small" class="ml-1" />
            </a>
          </v-list-item-title>
        </v-list-item>
      </v-list>
    </div>

    <!-- Statistics -->
    <v-row v-if="Object.keys(providerPanels).length > 0" class="mt-4">
      <v-col cols="4">
        <div class="text-center">
          <div class="text-h6 font-weight-bold text-primary">{{ totalPanels }}</div>
          <div class="text-caption text-medium-emphasis">Total Panels</div>
        </div>
      </v-col>
      <v-col cols="4">
        <div class="text-center">
          <div class="text-h6 font-weight-bold text-primary">{{ uniqueProviders }}</div>
          <div class="text-caption text-medium-emphasis">Providers</div>
        </div>
      </v-col>
      <v-col cols="4">
        <div class="text-center">
          <div
            class="text-h6 font-weight-bold"
            :class="getConfidenceColor(evidenceData.confidence) + '--text'"
          >
            {{ capitalizeFirst(evidenceData.confidence || 'Unknown') }}
          </div>
          <div class="text-caption text-medium-emphasis">Confidence</div>
        </div>
      </v-col>
    </v-row>
  </div>
</template>

<script setup>
import { computed } from 'vue'

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
  // New structure has providers as a direct object
  if (props.evidenceData?.providers) {
    const providers = {}

    // Process each provider and their panels
    for (const [provider, panels] of Object.entries(props.evidenceData.providers)) {
      providers[provider] = panels.map(panel =>
        typeof panel === 'string' ? panel : panel.name || ''
      )
    }

    return providers
  }

  // Fallback for old structure (if any)
  return {}
})

const uniqueProviders = computed(() => {
  return Object.keys(providerPanels.value).length
})

const totalPanels = computed(() => {
  let total = 0
  for (const panels of Object.values(providerPanels.value)) {
    total += panels.length
  }
  return total
})

// Helper functions
const getConfidenceColor = confidence => {
  const colors = {
    high: 'success',
    medium: 'warning',
    low: 'error'
  }
  return colors[confidence?.toLowerCase()] || 'grey'
}

const capitalizeFirst = str => {
  if (!str) return ''
  return str.charAt(0).toUpperCase() + str.slice(1)
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
