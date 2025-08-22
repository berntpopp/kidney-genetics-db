<template>
  <v-expansion-panel class="evidence-panel">
    <v-expansion-panel-title class="py-3">
      <div class="d-flex align-center justify-space-between w-100">
        <div class="d-flex align-center">
          <v-avatar :color="sourceColor" size="32" class="mr-3">
            <v-icon :icon="sourceIcon" size="small" color="white" />
          </v-avatar>
          <div>
            <div class="text-subtitle-1 font-weight-medium">{{ evidence.source_name }}</div>
            <div class="text-caption text-medium-emphasis">{{ evidenceSummary }}</div>
          </div>
        </div>
        <div class="d-flex align-center ga-2">
          <!-- Score chip following style guide - x-small for secondary info -->
          <v-chip
            v-if="evidence.normalized_score"
            size="x-small"
            variant="tonal"
            :color="getScoreColor(evidence.normalized_score)"
          >
            Score: {{ formatScore(evidence.normalized_score) }}
          </v-chip>
          <!-- Count badges -->
          <v-chip v-if="primaryCount" size="x-small" variant="outlined">
            {{ primaryCount }}
          </v-chip>
        </div>
      </div>
    </v-expansion-panel-title>

    <v-expansion-panel-text>
      <div class="pa-3">
        <!-- Dynamic component based on source type -->
        <component
          :is="evidenceComponent"
          :evidence-data="evidence.evidence_data"
          :source-name="evidence.source_name"
        />

        <!-- Metadata footer -->
        <div class="d-flex justify-space-between align-center mt-4 pt-3 border-t">
          <div class="text-caption text-medium-emphasis">
            Last updated: {{ formatDate(evidence.evidence_date) }}
          </div>
          <v-btn
            size="x-small"
            variant="text"
            :href="getSourceUrl(evidence.source_name)"
            target="_blank"
            append-icon="mdi-open-in-new"
          >
            View Source
          </v-btn>
        </div>
      </div>
    </v-expansion-panel-text>
  </v-expansion-panel>
</template>

<script setup>
import { computed } from 'vue'
import GenCCEvidence from './GenCCEvidence.vue'
import HPOEvidence from './HPOEvidence.vue'
import PubTatorEvidence from './PubTatorEvidence.vue'
import ClinGenEvidence from './ClinGenEvidence.vue'
import PanelAppEvidence from './PanelAppEvidence.vue'
import DiagnosticPanelsEvidence from './DiagnosticPanelsEvidence.vue'

const props = defineProps({
  evidence: {
    type: Object,
    required: true
  }
})

// Map source names to their specific components
const evidenceComponents = {
  GenCC: GenCCEvidence,
  HPO: HPOEvidence,
  PubTator: PubTatorEvidence,
  ClinGen: ClinGenEvidence,
  PanelApp: PanelAppEvidence,
  'Diagnostic Panels': DiagnosticPanelsEvidence
}

const evidenceComponent = computed(() => {
  return evidenceComponents[props.evidence.source_name] || 'div'
})

// Enhanced summary that includes classifications/key info
const evidenceSummary = computed(() => {
  const data = props.evidence.evidence_data
  const source = props.evidence.source_name

  // Custom summaries per source following new backend format
  if (source === 'GenCC' && data?.classifications?.length) {
    const topClassifications = data.classifications.slice(0, 2).join(', ')
    return `${props.evidence.source_detail} - ${topClassifications}`
  }

  if (source === 'ClinGen' && data?.classifications?.length) {
    const classification = data.classifications[0]
    const disease = data.diseases?.[0]
    if (disease) {
      const shortDisease = disease.length > 30 ? disease.substring(0, 30) + '...' : disease
      return `${classification} for ${shortDisease}`
    }
    return classification
  }

  if (source === 'Diagnostic Panels') {
    // New structure with providers
    if (data?.providers) {
      const providerCount = Object.keys(data.providers).length
      const panelCount = Object.values(data.providers).reduce(
        (sum, panels) => sum + panels.length,
        0
      )
      const confidence = data.confidence ? ` (${data.confidence} confidence)` : ''
      return `${providerCount} provider${providerCount > 1 ? 's' : ''}, ${panelCount} panel${panelCount > 1 ? 's' : ''}${confidence}`
    }
    // Fallback for old structure
    else if (data?.panels?.length) {
      const panelCount = data.panels.length
      const confidence = data.confidence ? ` (${data.confidence} confidence)` : ''
      return `${panelCount} diagnostic panel${panelCount > 1 ? 's' : ''}${confidence}`
    }
  }

  return props.evidence.source_detail
})

// Primary count display
const primaryCount = computed(() => {
  const data = props.evidence.evidence_data

  if (props.evidence.source_name === 'HPO') {
    return `${data?.hpo_terms?.length || 0} terms`
  }
  if (props.evidence.source_name === 'PubTator') {
    return `${data?.publication_count || 0} papers`
  }
  if (props.evidence.source_name === 'PanelApp') {
    return `${data?.panel_count || 0} panels`
  }
  if (props.evidence.source_name === 'Diagnostic Panels') {
    // New structure with providers
    if (data?.providers) {
      const providerCount = Object.keys(data.providers).length
      return `${providerCount} providers`
    }
    // Fallback for old structure
    return `${data?.panels?.length || 0} panels`
  }

  return null
})

// Source styling
const sourceColor = computed(() => {
  const colors = {
    GenCC: 'purple',
    HPO: 'blue',
    PubTator: 'teal',
    ClinGen: 'green',
    PanelApp: 'orange',
    'Diagnostic Panels': 'indigo'
  }
  return colors[props.evidence.source_name] || 'grey'
})

const sourceIcon = computed(() => {
  const icons = {
    GenCC: 'mdi-dna',
    HPO: 'mdi-human',
    PubTator: 'mdi-text-search',
    ClinGen: 'mdi-certificate',
    PanelApp: 'mdi-view-dashboard',
    'Diagnostic Panels': 'mdi-test-tube'
  }
  return icons[props.evidence.source_name] || 'mdi-database'
})

// Helper functions
const formatScore = score => {
  return (score * 100).toFixed(1)
}

const getScoreColor = score => {
  // Following style guide evidence score colors
  const percentage = score * 100
  if (percentage >= 95) return 'success'
  if (percentage >= 80) return 'success'
  if (percentage >= 70) return 'success'
  if (percentage >= 50) return 'warning'
  if (percentage >= 30) return 'orange'
  return 'error'
}

const formatDate = dateString => {
  if (!dateString) return 'Unknown'
  const date = new Date(dateString)
  return date.toLocaleDateString('en-US', {
    year: 'numeric',
    month: 'short',
    day: 'numeric'
  })
}

const getSourceUrl = sourceName => {
  const urls = {
    GenCC: 'https://thegencc.org/',
    HPO: 'https://hpo.jax.org/',
    PubTator: 'https://www.ncbi.nlm.nih.gov/research/pubtator/',
    ClinGen: 'https://clinicalgenome.org/',
    PanelApp: 'https://panelapp.genomicsengland.co.uk/',
    'Diagnostic Panels': '#' // No single source URL for aggregated panels
  }
  return urls[sourceName] || '#'
}
</script>

<style scoped>
.evidence-panel {
  border: 1px solid rgba(var(--v-border-color), var(--v-border-opacity));
  transition: all 0.3s cubic-bezier(0.4, 0, 0.2, 1);
}

.evidence-panel:hover {
  box-shadow: 0 2px 8px rgba(0, 0, 0, 0.1);
}

.border-t {
  border-top: 1px solid rgba(var(--v-border-color), var(--v-border-opacity));
}
</style>
