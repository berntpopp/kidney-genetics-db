<template>
  <div class="max-w-full">
    <!-- Publication highlights with enhanced details -->
    <div v-if="topPublications?.length" class="mb-4">
      <div class="text-sm font-medium mb-3">Recent Publications</div>

      <div class="space-y-3">
        <div v-for="mention in topPublications" :key="mention.pmid" class="flex items-start gap-3">
          <FileText class="size-4 mt-0.5 shrink-0 text-teal-600 dark:text-teal-400" />

          <div class="min-w-0">
            <!-- Publication title -->
            <div class="text-sm font-medium mb-1">
              {{ mention.title || `PMID: ${mention.pmid}` }}
            </div>

            <!-- Context snippet -->
            <div v-if="mention.context" class="text-xs text-muted-foreground mb-1">
              "...{{ mention.context }}..."
            </div>

            <!-- PMID link -->
            <Badge
              variant="outline"
              as="a"
              :href="`https://pubmed.ncbi.nlm.nih.gov/${mention.pmid}`"
              target="_blank"
              class="cursor-pointer"
              :style="{ borderColor: '#14b8a6', color: '#14b8a6' }"
            >
              PMID: {{ mention.pmid }}
              <ExternalLink :size="10" class="ml-1" />
            </Badge>
          </div>
        </div>
      </div>

      <!-- Show more publications -->
      <Button
        v-if="hasMorePublications"
        variant="ghost"
        size="sm"
        class="mt-2"
        @click="showAllPublications = !showAllPublications"
      >
        {{ showAllPublications ? 'Show Less' : `View ${remainingCount} More Publications` }}
        <component :is="showAllPublications ? ChevronUp : ChevronDown" class="size-4 ml-1" />
      </Button>
    </div>

    <!-- All publications (expanded view) -->
    <div v-if="showAllPublications && allPublications?.length > 5" class="mb-4">
      <Separator class="mb-3" />
      <div class="text-xs text-muted-foreground mb-2">Additional Publications</div>

      <div class="flex flex-wrap gap-2 max-h-[150px] overflow-y-auto p-2 bg-muted/30 rounded">
        <Badge
          v-for="pmid in additionalPMIDs"
          :key="pmid"
          variant="outline"
          as="a"
          :href="`https://pubmed.ncbi.nlm.nih.gov/${pmid}`"
          target="_blank"
          class="cursor-pointer"
        >
          {{ pmid }}
        </Badge>
      </div>
    </div>

    <!-- Statistics -->
    <div class="mt-4 p-3 bg-muted/30 rounded">
      <div class="grid grid-cols-3 gap-4">
        <div class="text-center">
          <div class="text-2xl font-bold" :style="{ color: '#14b8a6' }">
            {{ publicationCount }}
          </div>
          <div class="text-xs text-muted-foreground">Publications</div>
        </div>
        <div class="text-center">
          <div class="text-2xl font-bold" :style="{ color: '#14b8a6' }">
            {{ mentionCount }}
          </div>
          <div class="text-xs text-muted-foreground">Mentions</div>
        </div>
        <div class="text-center">
          <div class="text-2xl font-bold" :style="{ color: '#14b8a6' }">
            {{ evidenceScore }}
          </div>
          <div class="text-xs text-muted-foreground">Score</div>
        </div>
      </div>
    </div>

    <!-- Search query info -->
    <div v-if="searchQuery" class="mt-3 text-xs text-muted-foreground">
      <Search class="size-3 inline-block align-middle" />
      Search: {{ searchQuery }}
    </div>
  </div>
</template>

<script setup>
import { ref, computed } from 'vue'
import { FileText, ChevronUp, ChevronDown, Search, ExternalLink } from 'lucide-vue-next'
import { Badge } from '@/components/ui/badge'
import { Button } from '@/components/ui/button'
import { Separator } from '@/components/ui/separator'

const props = defineProps({
  evidenceData: {
    type: Object,
    required: true
  },
  sourceName: {
    type: String,
    default: 'PubTator'
  }
})

const showAllPublications = ref(false)

// Get top publications with details
const topPublications = computed(() => {
  // Use top_mentions if available (from enhanced backend)
  return props.evidenceData?.top_mentions || props.evidenceData?.mentions?.slice(0, 5) || []
})

// All publications
const allPublications = computed(() => {
  return props.evidenceData?.mentions || []
})

// All PMIDs
const allPMIDs = computed(() => {
  return props.evidenceData?.pmids || []
})

// Additional PMIDs not shown in top publications
const additionalPMIDs = computed(() => {
  const topPMIDs = topPublications.value.map(m => m.pmid)
  return allPMIDs.value.filter(pmid => !topPMIDs.includes(pmid))
})

const hasMorePublications = computed(() => {
  return allPublications.value.length > 5 || additionalPMIDs.value.length > 0
})

const remainingCount = computed(() => {
  return Math.max(allPublications.value.length - 5, additionalPMIDs.value.length)
})

// Statistics
const publicationCount = computed(() => {
  return props.evidenceData?.publication_count || 0
})

const mentionCount = computed(() => {
  return props.evidenceData?.total_mentions || 0
})

const evidenceScore = computed(() => {
  const score = props.evidenceData?.evidence_score
  return score !== undefined ? score.toFixed(1) : 'N/A'
})

const searchQuery = computed(() => {
  return props.evidenceData?.search_query || ''
})
</script>
