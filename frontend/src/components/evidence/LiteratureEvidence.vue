<template>
  <div class="literature-evidence">
    <!-- Publication List with Rich Details -->
    <div v-if="publications?.length" class="mb-4">
      <div class="text-subtitle-2 font-weight-medium mb-3 d-flex align-center">
        <v-icon icon="mdi-bookshelf" size="small" class="mr-2" color="primary" />
        Curated Literature Evidence
      </div>

      <!-- Top Publications with Details -->
      <v-list density="compact" class="transparent">
        <v-list-item
          v-for="(pub, index) in displayedPublications"
          :key="pub.pmid || index"
          class="px-0 mb-3 publication-item"
        >
          <template #prepend>
            <v-avatar size="32" color="primary" variant="tonal">
              <span class="text-caption font-weight-bold">{{ index + 1 }}</span>
            </v-avatar>
          </template>

          <div class="publication-content">
            <!-- Publication Title -->
            <div class="text-body-2 font-weight-medium mb-1">
              {{ pub.title || `Publication ${pub.pmid || index + 1}` }}
            </div>

            <!-- Authors and Journal -->
            <div v-if="pub.authors || pub.journal" class="text-caption text-medium-emphasis mb-1">
              <span v-if="pub.authors">
                {{ formatAuthors(pub.authors) }}
              </span>
              <span v-if="pub.authors && pub.journal"> • </span>
              <span v-if="pub.journal" class="font-italic">
                {{ pub.journal }}
              </span>
              <span v-if="pub.publication_date"> ({{ formatYear(pub.publication_date) }})</span>
            </div>

            <!-- Action Chips -->
            <div class="d-flex ga-2 flex-wrap mt-2">
              <!-- PMID Link -->
              <v-chip
                v-if="pub.pmid"
                size="x-small"
                variant="tonal"
                color="primary"
                :href="`https://pubmed.ncbi.nlm.nih.gov/${pub.pmid}`"
                target="_blank"
                prepend-icon="mdi-identifier"
                append-icon="mdi-open-in-new"
              >
                PMID: {{ pub.pmid }}
              </v-chip>

              <!-- DOI Link -->
              <v-chip
                v-if="pub.doi"
                size="x-small"
                variant="tonal"
                color="secondary"
                :href="`https://doi.org/${pub.doi}`"
                target="_blank"
                prepend-icon="mdi-link"
                append-icon="mdi-open-in-new"
              >
                DOI
              </v-chip>

              <!-- Direct URL -->
              <v-chip
                v-if="pub.url && !pub.pmid && !pub.doi"
                size="x-small"
                variant="tonal"
                color="info"
                :href="pub.url"
                target="_blank"
                prepend-icon="mdi-web"
                append-icon="mdi-open-in-new"
              >
                View
              </v-chip>
            </div>
          </div>
        </v-list-item>
      </v-list>

      <!-- Show More/Less Button -->
      <v-btn
        v-if="hasMorePublications"
        variant="text"
        size="small"
        color="primary"
        class="mt-2"
        @click="showAllPublications = !showAllPublications"
      >
        {{ showAllPublications ? 'Show Less' : `View ${remainingCount} More` }}
        <v-icon :icon="showAllPublications ? 'mdi-chevron-up' : 'mdi-chevron-down'" end />
      </v-btn>
    </div>

    <!-- Publication IDs Grid (Compact View) -->
    <v-expand-transition>
      <div v-if="showAllPublications && additionalPublications.length" class="mb-4">
        <v-divider class="mb-3" />
        <div class="text-caption text-medium-emphasis mb-2">Additional Publications</div>

        <div class="publication-grid">
          <v-chip
            v-for="pub in additionalPublications"
            :key="pub.pmid || pub"
            size="x-small"
            variant="outlined"
            color="primary"
            :href="getPublicationUrl(pub)"
            target="_blank"
          >
            {{ getPublicationLabel(pub) }}
          </v-chip>
        </div>
      </div>
    </v-expand-transition>

    <!-- No Data State -->
    <div v-if="!publications?.length" class="text-center py-8">
      <v-icon icon="mdi-book-open-variant" size="48" class="mb-3 text-medium-emphasis" />
      <p class="text-body-2 text-medium-emphasis">No literature evidence available</p>
    </div>
  </div>
</template>

<script setup>
import { ref, computed } from 'vue'

const props = defineProps({
  evidenceData: {
    type: Object,
    required: true
  },
  sourceName: {
    type: String,
    default: 'Literature'
  }
})

const showAllPublications = ref(false)

// Publication data parsing
const publications = computed(() => {
  // Handle both direct publications array and publication_details object
  if (props.evidenceData?.publication_details) {
    // Convert publication_details object to array
    return Object.entries(props.evidenceData.publication_details).map(([id, details]) => ({
      ...details,
      pmid: details.pmid || id
    }))
  }

  // Fallback to publications array if available
  return (
    props.evidenceData?.publications?.map(pub => {
      if (typeof pub === 'string') {
        return { pmid: pub }
      }
      return pub
    }) || []
  )
})

// Display logic
const displayedPublications = computed(() => {
  const pubs = publications.value
  if (showAllPublications.value) {
    return pubs
  }
  return pubs.slice(0, 3) // Show top 3 by default
})

const additionalPublications = computed(() => {
  return publications.value.slice(3)
})

const hasMorePublications = computed(() => {
  return publications.value.length > 3
})

const remainingCount = computed(() => {
  return publications.value.length - 3
})

// Statistics
const publicationCount = computed(() => {
  return props.evidenceData?.publication_count || publications.value.length || 0
})

// Helper functions
const formatAuthors = authors => {
  if (!authors) return ''

  // Handle array of authors
  if (Array.isArray(authors)) {
    if (authors.length === 0) return ''
    if (authors.length === 1) return authors[0]
    if (authors.length === 2) return authors.join(' & ')
    return `${authors[0]} et al.`
  }

  // Handle string of authors
  if (typeof authors === 'string') {
    const authorList = authors.split(',').map(a => a.trim())
    if (authorList.length === 1) return authors
    if (authorList.length === 2) return authorList.join(' & ')
    return `${authorList[0]} et al.`
  }

  return ''
}

const formatYear = dateString => {
  if (!dateString) return ''
  const year = new Date(dateString).getFullYear()
  return isNaN(year) ? '' : year
}

const getPublicationUrl = pub => {
  if (typeof pub === 'string') {
    // Assume it's a PMID
    return `https://pubmed.ncbi.nlm.nih.gov/${pub}`
  }

  if (pub.pmid) {
    return `https://pubmed.ncbi.nlm.nih.gov/${pub.pmid}`
  }

  if (pub.doi) {
    return `https://doi.org/${pub.doi}`
  }

  return pub.url || '#'
}

const getPublicationLabel = pub => {
  if (typeof pub === 'string') {
    return pub
  }

  if (pub.pmid) {
    return `PMID: ${pub.pmid}`
  }

  if (pub.title) {
    return pub.title.length > 30 ? pub.title.substring(0, 30) + '...' : pub.title
  }

  return 'Publication'
}
</script>

<style scoped>
.literature-evidence {
  max-width: 100%;
}

.publication-item {
  transition: all 0.2s ease;
  border-radius: 8px;
  padding: 8px !important;
}

.publication-item:hover {
  background: rgba(var(--v-theme-primary), 0.04);
}

.publication-content {
  flex: 1;
}

.publication-grid {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
  max-height: 200px;
  overflow-y: auto;
  padding: 12px;
  background: rgba(var(--v-theme-surface-variant), 0.3);
  border-radius: 8px;
}

/* Scrollbar styling */
.publication-grid::-webkit-scrollbar {
  width: 4px;
}

.publication-grid::-webkit-scrollbar-track {
  background: transparent;
}

.publication-grid::-webkit-scrollbar-thumb {
  background: rgba(var(--v-theme-primary), 0.3);
  border-radius: 2px;
}

.font-italic {
  font-style: italic;
}

/* Dark mode adjustments */
.v-theme--dark .publication-item:hover {
  background: rgba(var(--v-theme-primary), 0.08);
}

.v-theme--dark .publication-grid {
  background: rgba(var(--v-theme-surface-variant), 0.2);
}
</style>
