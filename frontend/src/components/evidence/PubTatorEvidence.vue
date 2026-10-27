<template>
  <EvidenceList title="Top-scoring mentions" :items="mentions" :item-key="m => m.pmid">
    <template #default="{ item: m }">
      <OntologyTerm :id="`PMID:${m.pmid}`" :name="m.title" />
      <p class="mt-0.5 text-xs text-muted-foreground">
        {{ byline(m) }}
      </p>
    </template>
  </EvidenceList>
</template>

<script setup>
import { computed } from 'vue'
import { OntologyTerm } from '@/components/shared'
import EvidenceList from './EvidenceList.vue'

const props = defineProps({
  evidenceData: { type: Object, required: true },
  sourceName: { type: String, default: 'PubTator' }
})

// Retained mention sample only; total_mentions is not a cumulative total (issue 281)
const mentions = computed(() => {
  const d = props.evidenceData ?? {}
  const unique = new Map()
  for (const m of d.top_mentions ?? d.mentions ?? []) if (!unique.has(m.pmid)) unique.set(m.pmid, m)
  return [...unique.values()]
})

const byline = m => {
  const year = m.date ? new Date(m.date).getFullYear() : NaN
  return [m.text ? `“${m.text}”` : '', m.journal, Number.isNaN(year) ? '' : year]
    .filter(Boolean)
    .join(' · ')
}
</script>
