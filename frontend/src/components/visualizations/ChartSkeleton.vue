<script setup lang="ts">
/** Chart loading skeleton in the final layout: stat row, then the chart box at its height. */
withDefaults(defineProps<{ stats?: number; height?: number }>(), { stats: 4, height: 400 })
</script>

<template>
  <div aria-hidden="true" class="space-y-4">
    <div v-if="stats" class="grid grid-cols-2 gap-4 sm:grid-cols-4">
      <div
        v-for="n in stats"
        :key="n"
        class="mx-auto h-11 w-20 rounded-md bg-muted motion-safe:animate-pulse"
      />
    </div>
    <div
      class="w-full rounded-md bg-muted motion-safe:animate-pulse"
      :style="{ height: `${height}px` }"
    />
  </div>
</template>
