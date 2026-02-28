<template>
  <div class="max-w-full">
    <!-- Enhanced HPO display with phenotype names -->
    <div v-if="phenotypeDetails?.length" class="mb-4">
      <div class="text-sm font-medium mb-3">Phenotype Terms</div>

      <!-- Display top phenotypes with names -->
      <div class="max-h-[400px] overflow-y-auto">
        <div class="flex flex-wrap gap-2">
          <Badge
            v-for="term in displayTerms"
            :key="term.id"
            variant="outline"
            as="a"
            :href="`https://hpo.jax.org/browse/term/${term.id}`"
            target="_blank"
            class="cursor-pointer"
            :style="{ borderColor: '#3b82f6', color: '#3b82f6' }"
          >
            <span class="font-mono mr-1">{{ term.id }}</span>
            <span>{{ term.name }}</span>
            <ExternalLink :size="10" class="ml-1" />
          </Badge>
        </div>
      </div>

      <!-- Show more button if there are additional terms -->
      <Button
        v-if="hasMoreTerms"
        variant="ghost"
        size="sm"
        class="mt-2"
        @click="showAllTerms = !showAllTerms"
      >
        {{ showAllTerms ? 'Show Less' : `Show ${remainingTerms} More Terms` }}
        <component :is="showAllTerms ? ChevronUp : ChevronDown" class="size-4 ml-1" />
      </Button>
    </div>

    <!-- Full term list (IDs only) for reference -->
    <div v-if="allTermIds?.length > phenotypeDetails?.length" class="mt-4">
      <Separator class="mb-3" />
      <div class="text-xs text-muted-foreground mb-2">
        Total: {{ allTermIds.length }} phenotype associations
      </div>

      <!-- Compact display of all term IDs via Collapsible -->
      <Collapsible>
        <CollapsibleTrigger as-child>
          <Button variant="outline" size="sm" class="w-full justify-between text-xs">
            View All Term IDs
            <ChevronDown class="size-4 ml-1" />
          </Button>
        </CollapsibleTrigger>
        <CollapsibleContent>
          <div
            class="grid grid-cols-[repeat(auto-fill,minmax(120px,1fr))] gap-2 max-h-[200px] overflow-y-auto p-2 mt-2 rounded bg-muted/50"
          >
            <code
              v-for="termId in allTermIds"
              :key="termId"
              class="font-mono text-[11px] px-1 py-0.5 bg-background rounded whitespace-nowrap"
            >
              {{ termId }}
            </code>
          </div>
        </CollapsibleContent>
      </Collapsible>
    </div>

    <!-- Evidence metadata -->
    <div class="mt-4 p-3 bg-muted/30 rounded">
      <div class="grid grid-cols-2 gap-4">
        <div>
          <div class="text-xs text-muted-foreground">Evidence Score</div>
          <div class="text-sm font-medium">
            {{ evidenceData.evidence_score || 'N/A' }}
          </div>
        </div>
        <div>
          <div class="text-xs text-muted-foreground">Last Updated</div>
          <div class="text-sm">
            {{ formatDate(evidenceData.last_updated) }}
          </div>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, computed } from 'vue'
import { ChevronUp, ChevronDown, ExternalLink } from 'lucide-vue-next'
import { Badge } from '@/components/ui/badge'
import { Button } from '@/components/ui/button'
import { Separator } from '@/components/ui/separator'
import { Collapsible, CollapsibleTrigger, CollapsibleContent } from '@/components/ui/collapsible'

const props = defineProps({
  evidenceData: {
    type: Object,
    required: true
  },
  sourceName: {
    type: String,
    default: 'HPO'
  }
})

const showAllTerms = ref(false)

// Get phenotype details with names (from enhanced backend)
const phenotypeDetails = computed(() => {
  return props.evidenceData?.hpo_term_details || []
})

// Get all term IDs
const allTermIds = computed(() => {
  return props.evidenceData?.hpo_terms || []
})

// Display logic - show first 5 or all if expanded
const displayTerms = computed(() => {
  if (showAllTerms.value) {
    return phenotypeDetails.value
  }
  return phenotypeDetails.value.slice(0, 5)
})

const hasMoreTerms = computed(() => {
  return phenotypeDetails.value.length > 5
})

const remainingTerms = computed(() => {
  return phenotypeDetails.value.length - 5
})

const formatDate = dateString => {
  if (!dateString) return 'Unknown'
  const date = new Date(dateString)
  return date.toLocaleDateString('en-US', {
    year: 'numeric',
    month: 'short',
    day: 'numeric'
  })
}
</script>
