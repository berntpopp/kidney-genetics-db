<script setup lang="ts">
import type { HTMLAttributes } from 'vue'
import { cn } from '@/lib/utils'

const props = defineProps<{
  class?: HTMLAttributes['class']
}>()
</script>

<template>
  <thead
    data-slot="table-header"
    :class="
      cn(
        'bg-muted/40 [&_tr]:border-b [&_tr]:border-black/[0.06] dark:[&_tr]:border-white/[0.08]',
        props.class
      )
    "
  >
    <slot />
  </thead>
</template>
