<script setup lang="ts">
/**
 * An identifier rendered name first, ID second (font-mono, muted), linked to its source,
 * with a tooltip giving the full name, ID and source. Without a name the ID is shown and
 * the tooltip says the name is unavailable (DESIGN.md Identifiers).
 */
import { computed } from 'vue'
import { Tooltip, TooltipContent, TooltipTrigger } from '@/components/ui/tooltip'
import { ONTOLOGY_SOURCES, parseOntologyId, type OntologySource } from '@/utils/ontology'

const props = defineProps<{
  id: string | number
  name?: string | null
  /** Source of a bare numeric ID (e.g. OMIM); prefixed IDs are detected */
  source?: OntologySource
  /** Overrides the computed link */
  href?: string
}>()

const parsed = computed(() => parseOntologyId(props.id, props.source))
const displayId = computed(() => parsed.value?.id ?? String(props.id))
const url = computed(() => props.href ?? parsed.value?.url ?? null)
const sourceName = computed(() => {
  const source = parsed.value?.source ?? props.source
  return source ? ONTOLOGY_SOURCES[source].name : null
})
const name = computed(() => props.name?.trim() || null)
const tip = computed(() =>
  [name.value ?? 'Name unavailable', displayId.value, sourceName.value].filter(Boolean).join(' · ')
)
</script>

<template>
  <Tooltip>
    <TooltipTrigger as-child>
      <component
        :is="url ? 'a' : 'span'"
        :href="url ?? undefined"
        :target="url ? '_blank' : undefined"
        :rel="url ? 'noopener noreferrer' : undefined"
        :tabindex="url ? undefined : 0"
        data-slot="ontology-term"
        class="inline rounded-sm focus-visible:ring-2 focus-visible:ring-ring focus-visible:outline-none"
        :class="url && 'underline-offset-4 hover:underline'"
      >
        <span v-if="name" class="text-foreground">{{ name }}</span>
        <span
          class="font-mono text-xs"
          :class="name ? 'ml-1 text-muted-foreground' : url ? 'text-primary' : 'text-foreground'"
          >{{ displayId }}</span
        >
      </component>
    </TooltipTrigger>
    <TooltipContent class="max-w-xs">{{ tip }}</TooltipContent>
  </Tooltip>
</template>
