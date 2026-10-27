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
import { hpoTerms } from './evidenceMeta'

const props = defineProps({
  evidenceData: { type: Object, required: true },
  sourceName: { type: String, default: 'HPO' }
})

const terms = computed(() => hpoTerms(props.evidenceData))
</script>
