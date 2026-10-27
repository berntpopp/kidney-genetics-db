<script setup lang="ts">
import type { HTMLAttributes } from 'vue'
import { computed, ref, useTemplateRef } from 'vue'
import { useEventListener, useResizeObserver } from '@vueuse/core'
import { cn } from '@/lib/utils'

const props = defineProps<{
  class?: HTMLAttributes['class']
}>()

// Fade the edge that has more columns behind it, so a table cut off at 390px shows it scrolls
const container = useTemplateRef('container')
const table = useTemplateRef('table')
const more = ref({ left: false, right: false })
const update = () => {
  const el = container.value
  if (!el) return
  more.value = {
    left: el.scrollLeft > 1,
    right: el.scrollLeft + el.clientWidth < el.scrollWidth - 1
  }
}
// the table widens when rows load without the container resizing, so watch both
useResizeObserver([container, table], update)
useEventListener(container, 'scroll', update, { passive: true })

const fade = computed(() => {
  const { left, right } = more.value
  if (!left && !right) return undefined
  const edge = (on: boolean) => (on ? 'transparent' : 'black')
  const mask = `linear-gradient(to right, ${edge(left)}, black 2rem, black calc(100% - 2rem), ${edge(right)})`
  return { maskImage: mask, WebkitMaskImage: mask }
})
</script>

<template>
  <div
    ref="container"
    data-slot="table-container"
    class="relative w-full overflow-auto"
    :style="fade"
  >
    <table ref="table" data-slot="table" :class="cn('w-full caption-bottom text-sm', props.class)">
      <slot />
    </table>
  </div>
</template>
