<template>
  <div class="max-w-full">
    <!-- Publication List with Rich Details -->
    <div v-if="publications?.length" class="mb-4">
      <div class="text-sm font-medium mb-3 flex items-center">
        <Library class="size-4 mr-2 text-primary" />
        Curated Literature Evidence
      </div>

      <!-- Top Publications with Details -->
      <div class="space-y-3">
        <div
          v-for="(pub, index) in displayedPublications"
          :key="pub.pmid || index"
          class="flex items-start gap-3 p-2 rounded-lg hover:bg-muted/50 transition-colors"
        >
          <Avatar class="h-8 w-8 shrink-0" :style="{ backgroundColor: '#0ea5e920' }">
            <AvatarFallback class="text-xs font-bold text-primary">
              {{ index + 1 }}
            </AvatarFallback>
          </Avatar>

          <div class="flex-1 min-w-0">
            <!-- Publication Title -->
            <div class="text-sm font-medium mb-1">
              {{ pub.title || `Publication ${pub.pmid || index + 1}` }}
            </div>

            <!-- Authors and Journal -->
            <div v-if="pub.authors || pub.journal" class="text-xs text-muted-foreground mb-1">
              <span v-if="pub.authors">
                {{ formatAuthors(pub.authors) }}
              </span>
              <span v-if="pub.authors && pub.journal"> &bull; </span>
              <span v-if="pub.journal" class="italic">
                {{ pub.journal }}
              </span>
              <span v-if="pub.publication_date"> ({{ formatYear(pub.publication_date) }})</span>
            </div>

            <!-- Action Badges -->
            <div class="flex flex-wrap gap-2 mt-2">
              <!-- PMID Link -->
              <Badge
                v-if="pub.pmid"
                variant="outline"
                :style="{
                  borderColor: '#0ea5e9',
                  color: '#0ea5e9',
                  backgroundColor: '#0ea5e915'
                }"
                as="a"
                :href="`https://pubmed.ncbi.nlm.nih.gov/${pub.pmid}`"
                target="_blank"
                class="text-xs cursor-pointer hover:opacity-80"
              >
                <IdCard class="size-3" />
                PMID: {{ pub.pmid }}
                <ExternalLink class="size-3" />
              </Badge>

              <!-- DOI Link -->
              <Badge
                v-if="pub.doi"
                variant="outline"
                :style="{
                  borderColor: '#6b7280',
                  color: '#6b7280',
                  backgroundColor: '#6b728015'
                }"
                as="a"
                :href="`https://doi.org/${pub.doi}`"
                target="_blank"
                class="text-xs cursor-pointer hover:opacity-80"
              >
                <Link class="size-3" />
                DOI
                <ExternalLink class="size-3" />
              </Badge>

              <!-- Direct URL -->
              <Badge
                v-if="pub.url && !pub.pmid && !pub.doi"
                variant="outline"
                :style="{
                  borderColor: '#3b82f6',
                  color: '#3b82f6',
                  backgroundColor: '#3b82f615'
                }"
                as="a"
                :href="pub.url"
                target="_blank"
                class="text-xs cursor-pointer hover:opacity-80"
              >
                <Globe class="size-3" />
                View
                <ExternalLink class="size-3" />
              </Badge>
            </div>
          </div>
        </div>
      </div>

      <!-- Show More/Less Button -->
      <Button
        v-if="hasMorePublications"
        variant="ghost"
        size="sm"
        class="mt-2 text-primary"
        @click="showAllPublications = !showAllPublications"
      >
        {{ showAllPublications ? 'Show Less' : `View ${remainingCount} More` }}
        <component :is="showAllPublications ? ChevronUp : ChevronDown" class="size-4 ml-1" />
      </Button>
    </div>

    <!-- Publication IDs Grid (Compact View) -->
    <div v-if="showAllPublications && additionalPublications.length" class="mb-4">
      <Separator class="mb-3" />
      <div class="text-xs text-muted-foreground mb-2">Additional Publications</div>

      <div class="flex flex-wrap gap-2 max-h-[200px] overflow-y-auto p-3 bg-muted/30 rounded-lg">
        <Badge
          v-for="pub in additionalPublications"
          :key="pub.pmid || pub"
          variant="outline"
          :style="{
            borderColor: '#0ea5e9',
            color: '#0ea5e9'
          }"
          as="a"
          :href="getPublicationUrl(pub)"
          target="_blank"
          class="text-xs cursor-pointer hover:opacity-80"
        >
          {{ getPublicationLabel(pub) }}
        </Badge>
      </div>
    </div>

    <!-- No Data State -->
    <div v-if="!publications?.length" class="text-center py-8">
      <BookOpen class="size-12 mb-3 mx-auto text-muted-foreground" />
      <p class="text-sm text-muted-foreground">No literature evidence available</p>
    </div>
  </div>
</template>

<script setup>
import { ref, computed } from 'vue'
import {
  Library,
  ChevronUp,
  ChevronDown,
  BookOpen,
  ExternalLink,
  IdCard,
  Link,
  Globe
} from 'lucide-vue-next'
import { Badge } from '@/components/ui/badge'
import { Button } from '@/components/ui/button'
import { Avatar, AvatarFallback } from '@/components/ui/avatar'
import { Separator } from '@/components/ui/separator'

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
// const publicationCount = computed(() => {
//   return props.evidenceData?.publication_count || publications.value.length || 0
// })

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
