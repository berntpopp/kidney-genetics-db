<template>
  <EvidenceList
    title="Submissions"
    :items="sortedSubmissions"
    :item-key="(s, i) => `${s.submitter}-${s.disease_name}-${i}`"
  >
    <template #default="{ item: s }">
      <div class="flex flex-wrap items-center gap-x-2 gap-y-1">
        <Chip :classification="s.classification" />
        <OntologyTerm v-if="diseaseId(s)" :id="diseaseId(s)" :name="s.disease_name" />
        <span v-else class="text-foreground">{{ s.disease_name }}</span>
      </div>
      <p class="mt-0.5 text-xs text-muted-foreground">
        {{
          [s.submitter, formatInheritance(s.mode_of_inheritance), formatDate(s.submission_date)]
            .filter(Boolean)
            .join(' · ')
        }}
      </p>
    </template>
  </EvidenceList>
</template>

<script setup>
import { computed } from 'vue'
import { Chip, OntologyTerm } from '@/components/shared'
import { getClassificationConfig } from '@/utils/evidenceTiers'
import EvidenceList from './EvidenceList.vue'
import { formatInheritance } from './evidenceMeta'

const props = defineProps({
  evidenceData: { type: Object, required: true },
  sourceName: { type: String, default: 'GenCC' }
})

// Strongest first; Disputed/Refuted/unknown after every strength
const sortedSubmissions = computed(() =>
  [...(props.evidenceData?.submissions ?? [])].sort(
    (a, b) =>
      (getClassificationConfig(b.classification).strength ?? 0) -
        (getClassificationConfig(a.classification).strength ?? 0) ||
      String(a.disease_name).localeCompare(String(b.disease_name))
  )
)

const diseaseId = s => s.disease_curie ?? s.raw_data?.disease_curie ?? null

const formatDate = value => {
  const date = new Date(String(value ?? '').replace(' ', 'T'))
  return Number.isNaN(date.getTime())
    ? ''
    : date.toLocaleDateString('en-US', { year: 'numeric', month: 'short', day: 'numeric' })
}
</script>
