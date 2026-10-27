<template>
  <EvidenceList
    title="Validity assessments"
    :items="validities"
    :item-key="(v, i) => v.submission_id ?? i"
  >
    <template #default="{ item: v }">
      <div class="flex flex-wrap items-center gap-x-2 gap-y-1">
        <Chip :classification="v.classification" />
        <OntologyTerm v-if="v.mondo_id" :id="v.mondo_id" :name="v.disease_name" />
        <span v-else class="text-foreground">{{ v.disease_name }}</span>
      </div>
      <p class="mt-0.5 text-xs text-muted-foreground">
        {{ details(v) }}
        <template v-if="isUrl(v.submission_id)">
          ·
          <a
            :href="v.submission_id"
            target="_blank"
            rel="noopener noreferrer"
            class="rounded-sm text-primary underline-offset-4 hover:underline focus-visible:ring-2 focus-visible:ring-ring focus-visible:outline-none"
            >Curation report<span class="sr-only"> (opens in a new tab)</span></a
          >
        </template>
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
  sourceName: { type: String, default: 'ClinGen' }
})

const validities = computed(() =>
  [...(props.evidenceData?.validities ?? [])].sort(
    (a, b) =>
      (getClassificationConfig(b.classification).strength ?? 0) -
      (getClassificationConfig(a.classification).strength ?? 0)
  )
)

const isUrl = value => /^https:\/\//.test(String(value ?? ''))

const details = v => {
  const date = v.release_date ? new Date(v.release_date) : null
  return [
    v.expert_panel,
    formatInheritance(v.mode_of_inheritance),
    date && !Number.isNaN(date.getTime())
      ? `Released ${date.toLocaleDateString('en-US', { year: 'numeric', month: 'short', day: 'numeric' })}`
      : ''
  ]
    .filter(Boolean)
    .join(' · ')
}
</script>
