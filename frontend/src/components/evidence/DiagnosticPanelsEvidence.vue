<template>
  <div class="max-w-full">
    <!-- Providers with Panels -->
    <div v-if="Object.keys(providerPanels).length > 0" class="mb-4">
      <div class="text-sm font-medium mb-2 flex items-center">
        <Building2 class="size-4 mr-1" />
        Providers ({{ uniqueProviders }})
      </div>

      <Accordion v-if="uniqueProviders > 1" type="multiple" class="mb-2">
        <AccordionItem
          v-for="(panelList, provider) in providerPanels"
          :key="provider"
          :value="String(provider)"
          class="mb-1"
        >
          <AccordionTrigger class="text-sm py-2">
            <div class="flex items-center">
              <Building class="size-4 mr-2" />
              <strong>{{ formatProviderName(provider) }}</strong>
              <Badge variant="outline" class="ml-2 text-xs">
                {{ panelList.length }} panel{{ panelList.length > 1 ? 's' : '' }}
              </Badge>
            </div>
          </AccordionTrigger>
          <AccordionContent>
            <div class="flex flex-wrap gap-1 pt-1">
              <Badge
                v-for="(panel, index) in panelList"
                :key="index"
                variant="outline"
                :style="{
                  borderColor: '#0ea5e9',
                  color: '#0ea5e9',
                  backgroundColor: '#0ea5e920',
                }"
              >
                {{ panel }}
              </Badge>
            </div>
          </AccordionContent>
        </AccordionItem>
      </Accordion>

      <!-- Single provider - show directly -->
      <div v-else-if="uniqueProviders === 1">
        <div v-for="(panelList, provider) in providerPanels" :key="provider">
          <div class="text-sm font-medium mb-2 flex items-center">
            <Building class="size-4 mr-1" />
            {{ formatProviderName(provider) }}
          </div>
          <div class="flex flex-wrap gap-1">
            <Badge
              v-for="(panel, index) in panelList"
              :key="index"
              variant="outline"
            >
              {{ panel }}
            </Badge>
          </div>
        </div>
      </div>
    </div>

    <!-- Gene Information -->
    <div v-if="evidenceData.metadata" class="mb-4">
      <div class="text-sm font-medium mb-2 flex items-center">
        <Dna class="size-4 mr-1" />
        Gene Information
      </div>
      <div class="space-y-1">
        <div v-if="evidenceData.metadata.approved_symbol" class="flex items-center gap-2 py-1">
          <span class="text-xs text-muted-foreground">Symbol:</span>
          <span class="text-sm">{{ evidenceData.metadata.approved_symbol }}</span>
        </div>
        <div v-if="evidenceData.metadata.hgnc_id" class="flex items-center gap-2 py-1">
          <span class="text-xs text-muted-foreground">HGNC ID:</span>
          <a
            :href="`https://www.genenames.org/data/gene-symbol-report/#!/hgnc_id/${evidenceData.metadata.hgnc_id}`"
            target="_blank"
            class="text-sm text-primary hover:underline inline-flex items-center"
          >
            {{ evidenceData.metadata.hgnc_id }}
            <ExternalLink class="size-3 ml-1" />
          </a>
        </div>
      </div>
    </div>

    <!-- Statistics -->
    <div v-if="Object.keys(providerPanels).length > 0" class="mt-4 p-3 bg-muted/30 rounded-md">
      <div class="grid grid-cols-2 gap-4">
        <div class="text-center">
          <div class="text-lg font-bold text-primary">{{ totalPanels }}</div>
          <div class="text-xs text-muted-foreground">Total Panels</div>
        </div>
        <div class="text-center">
          <div class="text-lg font-bold text-primary">{{ uniqueProviders }}</div>
          <div class="text-xs text-muted-foreground">Providers</div>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { computed } from 'vue'
import { Building2, Building, Dna, ExternalLink } from 'lucide-vue-next'
import { Badge } from '@/components/ui/badge'
import {
  Accordion,
  AccordionItem,
  AccordionTrigger,
  AccordionContent,
} from '@/components/ui/accordion'

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
