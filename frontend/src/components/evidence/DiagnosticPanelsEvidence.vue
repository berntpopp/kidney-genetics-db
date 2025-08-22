<template>
  <div class="diagnostic-panels-evidence">
    <!-- Panels Section -->
    <div v-if="panels && panels.length > 0" class="mb-4">
      <div class="text-subtitle-2 font-weight-medium mb-2">
        <v-icon icon="mdi-view-list" size="small" class="mr-1" />
        Diagnostic Panels ({{ panels.length }})
      </div>
      <div class="panels-grid">
        <v-chip
          v-for="(panel, index) in panels"
          :key="index"
          size="small"
          variant="outlined"
          class="ma-1"
        >
          {{ panel }}
        </v-chip>
      </div>
    </div>

    <!-- Confidence Level -->
    <div v-if="evidenceData.confidence" class="mb-4">
      <div class="text-subtitle-2 font-weight-medium mb-2">
        <v-icon icon="mdi-shield-check" size="small" class="mr-1" />
        Confidence Level
      </div>
      <v-chip
        :color="getConfidenceColor(evidenceData.confidence)"
        variant="tonal"
        size="small"
      >
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
          <template v-slot:prepend>
            <span class="text-caption text-medium-emphasis mr-2">Symbol:</span>
          </template>
          <v-list-item-title class="text-body-2">
            {{ evidenceData.metadata.approved_symbol }}
          </v-list-item-title>
        </v-list-item>
        <v-list-item v-if="evidenceData.metadata.hgnc_id">
          <template v-slot:prepend>
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

    <!-- Panel Providers Summary -->
    <div v-if="panelProviders.length > 0" class="mb-4">
      <div class="text-subtitle-2 font-weight-medium mb-2">
        <v-icon icon="mdi-domain" size="small" class="mr-1" />
        Panel Providers
      </div>
      <div class="text-body-2 text-medium-emphasis">
        {{ panelProviders.join(', ') }}
      </div>
    </div>

    <!-- Statistics -->
    <v-row v-if="panels && panels.length > 0" class="mt-4">
      <v-col cols="4">
        <div class="text-center">
          <div class="text-h6 font-weight-bold text-primary">{{ panels.length }}</div>
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
          <div class="text-h6 font-weight-bold" :class="getConfidenceColor(evidenceData.confidence) + '--text'">
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

// Extract panels array
const panels = computed(() => {
  return props.evidenceData?.panels || []
})

// Extract unique panel providers from panel names
const panelProviders = computed(() => {
  const providers = new Set()
  
  // Common provider patterns in panel names
  const providerPatterns = [
    'Mayo', 'Blueprint', 'Invitae', 'CEGAT', 'Centogene', 
    'MGZ', 'MVZ', 'Natera', 'Prevention Genetics', 'Genomics England'
  ]
  
  panels.value.forEach(panel => {
    providerPatterns.forEach(provider => {
      if (panel.toLowerCase().includes(provider.toLowerCase())) {
        providers.add(provider)
      }
    })
  })
  
  return Array.from(providers)
})

const uniqueProviders = computed(() => {
  return panelProviders.value.length || 'Multiple'
})

// Helper functions
const getConfidenceColor = (confidence) => {
  const colors = {
    high: 'success',
    medium: 'warning',
    low: 'error'
  }
  return colors[confidence?.toLowerCase()] || 'grey'
}

const capitalizeFirst = (str) => {
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