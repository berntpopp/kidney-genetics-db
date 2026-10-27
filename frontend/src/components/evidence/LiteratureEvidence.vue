<template>
  <EvidenceList title="Publications" :items="publications" :item-key="p => p.pmid">
    <template #default="{ item: p }">
      <OntologyTerm :id="`PMID:${p.pmid}`" :name="p.title" />
      <p v-if="byline(p)" class="mt-0.5 text-xs text-muted-foreground">{{ byline(p) }}</p>
    </template>
  </EvidenceList>
</template>

<script setup>
import { computed } from 'vue'
import { OntologyTerm } from '@/components/shared'
import EvidenceList from './EvidenceList.vue'

const props = defineProps({
  evidenceData: { type: Object, required: true },
  sourceName: { type: String, default: 'Literature' }
})

// Newest first; publication_details carries titles, the publications array only PMIDs
const publications = computed(() => {
  const details = props.evidenceData?.publication_details ?? {}
  const pmids = props.evidenceData?.publications ?? Object.keys(details)
  return pmids
    .map(id => ({ ...(details[id] ?? {}), pmid: String(details[id]?.pmid ?? id) }))
    .sort((a, b) =>
      String(b.publication_date ?? '').localeCompare(String(a.publication_date ?? ''))
    )
})

const authors = list => {
  if (!Array.isArray(list) || !list.length) return ''
  return list.length > 1 ? `${list[0]} et al.` : list[0]
}

const byline = p => {
  const year = p.publication_date ? new Date(p.publication_date).getFullYear() : NaN
  const journal = p.journal && p.journal !== 'Unknown Journal' ? p.journal : ''
  return [authors(p.authors), journal, Number.isNaN(year) ? '' : year].filter(Boolean).join(' · ')
}
</script>
