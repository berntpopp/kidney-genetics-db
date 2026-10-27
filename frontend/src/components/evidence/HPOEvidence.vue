<template>
  <section v-if="terms.length">
    <h4 class="mb-2 text-sm font-medium text-foreground">Phenotype terms</h4>
    <OntologyTermList :terms="terms" source="HPO" :max="12" />
  </section>
  <p v-else class="text-sm text-muted-foreground">No phenotype terms recorded.</p>
</template>

<script setup>
import { computed } from 'vue'
import { OntologyTermList } from '@/components/shared'

const props = defineProps({
  evidenceData: { type: Object, required: true },
  sourceName: { type: String, default: 'HPO' },
  /** HPO term ID -> name from the gene's HPO annotation (evidence stores IDs only) */
  hpoNames: { type: Object, default: () => ({}) }
})

const terms = computed(() => {
  const details = Object.fromEntries(
    (props.evidenceData?.hpo_term_details ?? []).map(t => [t.id, t.name])
  )
  return (props.evidenceData?.hpo_terms ?? []).map(id => ({
    id,
    name: details[id] ?? props.hpoNames?.[id] ?? null
  }))
})
</script>
