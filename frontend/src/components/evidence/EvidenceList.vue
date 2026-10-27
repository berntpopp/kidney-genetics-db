<script setup lang="ts" generic="T">
/**
 * One titled list inside an EvidenceCard body: same heading, spacing and "Show all" wording
 * as OntologyTermList, so every source expands its items the same way.
 */
import { computed, ref } from 'vue'
import { Button } from '@/components/ui/button'

const props = withDefaults(
  defineProps<{
    title: string
    items: T[]
    /** Show at most this many until "Show all" is pressed */
    max?: number
    itemKey?: (_item: T, _index: number) => string | number
  }>(),
  { max: 5, itemKey: undefined }
)

const expanded = ref(false)
const visible = computed(() => (expanded.value ? props.items : props.items.slice(0, props.max)))
const hidden = computed(() => props.items.length - visible.value.length)
</script>

<template>
  <section v-if="items.length" data-slot="evidence-list">
    <h4 class="mb-2 text-sm font-medium text-foreground">{{ title }}</h4>
    <ul class="space-y-2 text-sm">
      <li v-for="(item, i) in visible" :key="itemKey ? itemKey(item, i) : i">
        <slot :item="item" :index="i" />
      </li>
    </ul>
    <Button
      v-if="items.length > max"
      variant="link"
      size="sm"
      class="mt-1 h-auto px-0"
      :aria-expanded="expanded"
      @click="expanded = !expanded"
    >
      {{ expanded ? 'Show fewer' : `Show all ${items.length} (${hidden} more)` }}
    </Button>
  </section>
</template>
