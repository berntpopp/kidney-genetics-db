<template>
  <AccordionItem :value="evidence.source_name" class="border rounded-lg mb-2">
    <AccordionTrigger class="px-4 py-3 hover:no-underline">
      <div class="flex items-center justify-between w-full mr-4">
        <div class="flex items-center gap-3">
          <Avatar class="h-8 w-8" :style="{ backgroundColor: sourceColorHex + '20' }">
            <AvatarFallback>
              <component :is="sourceIconComponent" :size="16" :style="{ color: sourceColorHex }" />
            </AvatarFallback>
          </Avatar>
          <div>
            <span class="text-sm font-medium">{{ evidence.source_name }}</span>
            <span class="text-xs text-muted-foreground ml-2">{{ evidenceSummary }}</span>
          </div>
        </div>
        <div class="flex items-center gap-2">
          <Badge
            v-if="evidence.normalized_score"
            variant="outline"
            :style="{
              backgroundColor: getScoreColorHex(evidence.normalized_score) + '20',
              color: getScoreColorHex(evidence.normalized_score)
            }"
          >
            Score: {{ formatScore(evidence.normalized_score) }}
          </Badge>
          <Badge v-if="primaryCount" variant="secondary" class="text-xs">
            {{ primaryCount }}
          </Badge>
        </div>
      </div>
    </AccordionTrigger>
    <AccordionContent class="px-4 pb-4">
      <!-- Dynamic component based on source type -->
      <component
        :is="evidenceComponent"
        :evidence-data="evidence.evidence_data"
        :source-name="evidence.source_name"
      />

      <!-- Metadata footer -->
      <div
        class="border-t pt-3 mt-4 flex items-center justify-between text-xs text-muted-foreground"
      >
        <span>Last updated: {{ formatDate(evidence.evidence_date) }}</span>
        <Button
          variant="ghost"
          size="sm"
          as="a"
          :href="getSourceUrl(evidence.source_name)"
          target="_blank"
        >
          View Source
          <ExternalLink :size="12" class="ml-1" />
        </Button>
      </div>
    </AccordionContent>
  </AccordionItem>
</template>

<script setup>
import { computed } from 'vue'
import { ExternalLink } from 'lucide-vue-next'
import { resolveMdiIcon } from '@/utils/icons'
import { AccordionItem, AccordionTrigger, AccordionContent } from '@/components/ui/accordion'
import { Avatar, AvatarFallback } from '@/components/ui/avatar'
import { Badge } from '@/components/ui/badge'
import { Button } from '@/components/ui/button'
import GenCCEvidence from './GenCCEvidence.vue'
import HPOEvidence from './HPOEvidence.vue'
import PubTatorEvidence from './PubTatorEvidence.vue'
import ClinGenEvidence from './ClinGenEvidence.vue'
import PanelAppEvidence from './PanelAppEvidence.vue'
import DiagnosticPanelsEvidence from './DiagnosticPanelsEvidence.vue'
import LiteratureEvidence from './LiteratureEvidence.vue'

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
  DiagnosticPanels: DiagnosticPanelsEvidence,
  Literature: LiteratureEvidence
}

const evidenceComponent = computed(() => {
  return evidenceComponents[props.evidence.source_name] || 'div'
})

// Enhanced summary that includes classifications/key info
const evidenceSummary = computed(() => {
  const data = props.evidence.evidence_data
  const source = props.evidence.source_name

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

  if (source === 'DiagnosticPanels') {
    if (data?.provider_panels) {
      const providerCount = Object.keys(data.provider_panels).length
      const uniquePanels = new Set()
      Object.values(data.provider_panels).forEach(panels => {
        panels.forEach(panel => uniquePanels.add(panel))
      })
      const panelCount = uniquePanels.size
      return `${providerCount} provider${providerCount > 1 ? 's' : ''}, ${panelCount} panel${panelCount > 1 ? 's' : ''}`
    } else if (data?.provider_count || data?.panel_count) {
      const providerCount = data.provider_count || 0
      const panelCount = data.panel_count || 0
      return `${providerCount} provider${providerCount > 1 ? 's' : ''}, ${panelCount} panel${panelCount > 1 ? 's' : ''}`
    }
  }

  if (source === 'Literature') {
    const pubCount = data?.publication_count || 0
    if (pubCount === 1) {
      return 'Curated literature evidence from 1 publication'
    }
    return `Curated literature evidence from ${pubCount} publications`
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
  if (props.evidence.source_name === 'DiagnosticPanels') {
    if (data?.provider_panels) {
      const providerCount = Object.keys(data.provider_panels).length
      return `${providerCount} providers`
    }
    return `${data?.panels?.length || 0} panels`
  }
  if (props.evidence.source_name === 'Literature') {
    const pubCount = data?.publication_count || 0
    return `${pubCount} paper${pubCount !== 1 ? 's' : ''}`
  }

  return null
})

// Source styling - hex colors for inline styles
const sourceColors = {
  GenCC: '#8b5cf6',
  HPO: '#3b82f6',
  PubTator: '#14b8a6',
  ClinGen: '#22c55e',
  PanelApp: '#f97316',
  DiagnosticPanels: '#6366f1',
  Literature: '#0ea5e9'
}

const sourceColorHex = computed(() => {
  return sourceColors[props.evidence.source_name] || '#6b7280'
})

const sourceIcon = computed(() => {
  const icons = {
    GenCC: 'mdi-dna',
    HPO: 'mdi-human',
    PubTator: 'mdi-text-search',
    ClinGen: 'mdi-certificate',
    PanelApp: 'mdi-view-dashboard',
    DiagnosticPanels: 'mdi-test-tube',
    Literature: 'mdi-book-open-variant'
  }
  return icons[props.evidence.source_name] || 'mdi-database'
})

const sourceIconComponent = computed(() => {
  return resolveMdiIcon(sourceIcon.value)
})

// Helper functions
const formatScore = score => {
  return (score * 100).toFixed(1)
}

const getScoreColorHex = score => {
  const percentage = score * 100
  if (percentage >= 50) return '#22c55e'
  if (percentage >= 30) return '#f59e0b'
  return '#ef4444'
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
    DiagnosticPanels: '#',
    Literature: 'https://pubmed.ncbi.nlm.nih.gov/'
  }
  return urls[sourceName] || '#'
}
</script>
