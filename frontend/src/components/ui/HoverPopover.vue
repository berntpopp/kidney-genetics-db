<script setup lang="ts">
/**
 * HoverPopover: Shows content on hover (desktop mouse) AND click/tap (mobile).
 * Replaces Tooltip for interactive content that must be accessible on touch devices.
 * Uses pointerType detection: mouse = hover, touch/pen = click only.
 */
import { ref } from 'vue'
import { Popover, PopoverContent, PopoverTrigger } from '@/components/ui/popover'

withDefaults(
  defineProps<{
    side?: 'top' | 'right' | 'bottom' | 'left'
    contentClass?: string
  }>(),
  {
    side: 'top',
    contentClass: 'w-auto p-2'
  }
)

const open = ref(false)

const onPointerEnter = (e: PointerEvent) => {
  if (e.pointerType === 'mouse') {
    open.value = true
  }
}
const onPointerLeave = (e: PointerEvent) => {
  if (e.pointerType === 'mouse') {
    open.value = false
  }
}
const onOpenChange = (v: boolean) => {
  open.value = v
}
</script>

<template>
  <Popover :open="open" @update:open="onOpenChange">
    <PopoverTrigger as-child>
      <span class="inline-flex" @pointerenter="onPointerEnter" @pointerleave="onPointerLeave">
        <slot />
      </span>
    </PopoverTrigger>
    <PopoverContent
      :side="side"
      :class="contentClass"
      @pointerenter="onPointerEnter"
      @pointerleave="onPointerLeave"
    >
      <slot name="content" />
    </PopoverContent>
  </Popover>
</template>
