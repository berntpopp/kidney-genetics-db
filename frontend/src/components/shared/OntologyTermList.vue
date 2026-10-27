<script setup lang="ts">
/** Identifiers sorted by name (unnamed last), deduplicated by ID, optionally capped with "Show all". */
import { computed, ref } from 'vue'
import { Button } from '@/components/ui/button'
import { parseOntologyId, type OntologySource } from '@/utils/ontology'
import OntologyTerm from './OntologyTerm.vue'

export interface OntologyTermItem {
  id: string | number
  name?: string | null
}

const props = defineProps<{
  terms: OntologyTermItem[]
  source?: OntologySource
  /** Show at most this many until "Show all" is pressed */
  max?: number
}>()

const expanded = ref(false)

const sorted = computed(() => {
  const byId = new Map<string, OntologyTermItem>()
  for (const term of props.terms) {
    const key = parseOntologyId(term.id, props.source)?.id ?? String(term.id).trim()
    // keep the entry that has a name
    if (!byId.has(key) || (!byId.get(key)!.name && term.name)) byId.set(key, term)
  }
  return [...byId.entries()]
    .sort(([idA, a], [idB, b]) => {
      if (!a.name !== !b.name) return a.name ? -1 : 1
      return (a.name ?? '').localeCompare(b.name ?? '') || idA.localeCompare(idB)
    })
    .map(([key, term]) => ({ key, ...term }))
})

const visible = computed(() =>
  props.max && !expanded.value ? sorted.value.slice(0, props.max) : sorted.value
)
const hidden = computed(() => sorted.value.length - visible.value.length)
</script>

<template>
  <div data-slot="ontology-term-list">
    <ul class="flex flex-wrap gap-x-4 gap-y-1 text-sm">
      <li v-for="term in visible" :key="term.key">
        <OntologyTerm :id="term.id" :name="term.name" :source="source" />
      </li>
    </ul>
    <Button
      v-if="max && sorted.length > max"
      variant="link"
      size="sm"
      class="mt-1 h-auto px-0"
      :aria-expanded="expanded"
      @click="expanded = !expanded"
    >
      {{ expanded ? 'Show fewer' : `Show all ${sorted.length} (${hidden} more)` }}
    </Button>
  </div>
</template>
