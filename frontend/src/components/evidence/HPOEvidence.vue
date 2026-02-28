<template>
  <div class="hpo-evidence">
    <!-- Enhanced HPO display with phenotype names -->
    <div v-if="phenotypeDetails?.length" class="mb-4">
      <div class="text-subtitle-2 font-weight-medium mb-3">Phenotype Terms</div>

      <!-- Display top phenotypes with names -->
      <div class="phenotype-list">
        <v-chip-group column>
          <div v-for="term in displayTerms" :key="term.id" class="mb-2">
            <v-chip
              size="small"
              variant="outlined"
              color="blue"
              :href="`https://hpo.jax.org/browse/term/${term.id}`"
              target="_blank"
              append-icon="mdi-open-in-new"
            >
              <span class="font-mono mr-2">{{ term.id }}</span>
              <span>{{ term.name }}</span>
            </v-chip>
          </div>
        </v-chip-group>
      </div>

      <!-- Show more button if there are additional terms -->
      <v-btn
        v-if="hasMoreTerms"
        variant="text"
        size="small"
        class="mt-2"
        @click="showAllTerms = !showAllTerms"
      >
        {{ showAllTerms ? 'Show Less' : `Show ${remainingTerms} More Terms` }}
        <component :is="showAllTerms ? ChevronUp : ChevronDown" class="size-4 ml-1" />
      </v-btn>
    </div>

    <!-- Full term list (IDs only) for reference -->
    <div v-if="allTermIds?.length > phenotypeDetails?.length" class="mt-4">
      <v-divider class="mb-3" />
      <div class="text-caption text-medium-emphasis mb-2">
        Total: {{ allTermIds.length }} phenotype associations
      </div>

      <!-- Compact display of all term IDs -->
      <v-expansion-panels variant="inset" density="compact">
        <v-expansion-panel>
          <v-expansion-panel-title class="text-caption">
            View All Term IDs
          </v-expansion-panel-title>
          <v-expansion-panel-text>
            <div class="term-grid pa-2">
              <code v-for="termId in allTermIds" :key="termId" class="term-id">
                {{ termId }}
              </code>
            </div>
          </v-expansion-panel-text>
        </v-expansion-panel>
      </v-expansion-panels>
    </div>

    <!-- Evidence metadata -->
    <div class="mt-4 pa-3 bg-surface-light rounded">
      <v-row dense>
        <v-col cols="6">
          <div class="text-caption text-medium-emphasis">Evidence Score</div>
          <div class="text-body-2 font-weight-medium">
            {{ evidenceData.evidence_score || 'N/A' }}
          </div>
        </v-col>
        <v-col cols="6">
          <div class="text-caption text-medium-emphasis">Last Updated</div>
          <div class="text-body-2">
            {{ formatDate(evidenceData.last_updated) }}
          </div>
        </v-col>
      </v-row>
    </div>
  </div>
</template>

<script setup>
import { ref, computed } from 'vue'
import { ChevronUp, ChevronDown } from 'lucide-vue-next'

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

<style scoped>
.hpo-evidence {
  max-width: 100%;
}

.phenotype-list {
  max-height: 400px;
  overflow-y: auto;
}

.term-grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(120px, 1fr));
  gap: 8px;
  max-height: 200px;
  overflow-y: auto;
  background: rgba(var(--v-theme-surface-variant), 0.5);
  border-radius: 4px;
}

.term-id {
  font-family: 'Roboto Mono', monospace;
  font-size: 11px;
  padding: 2px 4px;
  background: rgb(var(--v-theme-surface));
  border-radius: 2px;
  white-space: nowrap;
}

.bg-surface-light {
  background: rgba(var(--v-theme-surface-variant), 0.3);
}
</style>
