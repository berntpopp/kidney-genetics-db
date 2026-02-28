<template>
  <div class="pubtator-evidence">
    <!-- Publication highlights with enhanced details -->
    <div v-if="topPublications?.length" class="mb-4">
      <div class="text-subtitle-2 font-weight-medium mb-3">Recent Publications</div>

      <v-list density="compact" class="transparent">
        <v-list-item v-for="mention in topPublications" :key="mention.pmid" class="px-0 mb-3">
          <template #prepend>
            <FileText class="size-4 text-teal-600 dark:text-teal-400" />
          </template>

          <div>
            <!-- Publication title -->
            <div class="text-body-2 font-weight-medium mb-1">
              {{ mention.title || `PMID: ${mention.pmid}` }}
            </div>

            <!-- Context snippet -->
            <div v-if="mention.context" class="text-caption text-medium-emphasis mb-1">
              "...{{ mention.context }}..."
            </div>

            <!-- PMID link -->
            <v-chip
              size="x-small"
              variant="text"
              color="teal"
              :href="`https://pubmed.ncbi.nlm.nih.gov/${mention.pmid}`"
              target="_blank"
              append-icon="mdi-open-in-new"
            >
              PMID: {{ mention.pmid }}
            </v-chip>
          </div>
        </v-list-item>
      </v-list>

      <!-- Show more publications -->
      <v-btn
        v-if="hasMorePublications"
        variant="text"
        size="small"
        class="mt-2"
        @click="showAllPublications = !showAllPublications"
      >
        {{ showAllPublications ? 'Show Less' : `View ${remainingCount} More Publications` }}
        <component :is="showAllPublications ? ChevronUp : ChevronDown" class="size-4 ml-1" />
      </v-btn>
    </div>

    <!-- All publications (expanded view) -->
    <v-expand-transition>
      <div v-if="showAllPublications && allPublications?.length > 5" class="mb-4">
        <v-divider class="mb-3" />
        <div class="text-caption text-medium-emphasis mb-2">Additional Publications</div>

        <div class="pmid-grid">
          <v-chip
            v-for="pmid in additionalPMIDs"
            :key="pmid"
            size="x-small"
            variant="outlined"
            :href="`https://pubmed.ncbi.nlm.nih.gov/${pmid}`"
            target="_blank"
          >
            {{ pmid }}
          </v-chip>
        </div>
      </div>
    </v-expand-transition>

    <!-- Statistics -->
    <div class="mt-4 pa-3 bg-surface-light rounded">
      <v-row dense>
        <v-col cols="4">
          <div class="text-center">
            <div class="text-h5 font-weight-bold text-teal">
              {{ publicationCount }}
            </div>
            <div class="text-caption text-medium-emphasis">Publications</div>
          </div>
        </v-col>
        <v-col cols="4">
          <div class="text-center">
            <div class="text-h5 font-weight-bold text-teal">
              {{ mentionCount }}
            </div>
            <div class="text-caption text-medium-emphasis">Mentions</div>
          </div>
        </v-col>
        <v-col cols="4">
          <div class="text-center">
            <div class="text-h5 font-weight-bold text-teal">
              {{ evidenceScore }}
            </div>
            <div class="text-caption text-medium-emphasis">Score</div>
          </div>
        </v-col>
      </v-row>
    </div>

    <!-- Search query info -->
    <div v-if="searchQuery" class="mt-3 text-caption text-medium-emphasis">
      <Search class="size-3 inline-block align-middle" />
      Search: {{ searchQuery }}
    </div>
  </div>
</template>

<script setup>
import { ref, computed } from 'vue'
import { FileText, ChevronUp, ChevronDown, Search } from 'lucide-vue-next'

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

<style scoped>
.pubtator-evidence {
  max-width: 100%;
}

.pmid-grid {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
  max-height: 150px;
  overflow-y: auto;
  padding: 8px;
  background: rgba(var(--v-theme-surface-variant), 0.3);
  border-radius: 4px;
}

.bg-surface-light {
  background: rgba(var(--v-theme-surface-variant), 0.3);
}
</style>
