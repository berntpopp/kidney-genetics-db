<script setup lang="ts">
defineProps<{
  /** Minimum height for the skeleton placeholder */
  minHeight?: string
}>()
</script>

<template>
  <div
    class="flex items-center justify-center rounded-lg border border-border bg-muted/30"
    :style="{ minHeight: minHeight ?? '200px' }"
  >
    <div class="flex flex-col items-center gap-2 text-muted-foreground">
      <svg
        class="h-6 w-6 animate-spin"
        xmlns="http://www.w3.org/2000/svg"
        fill="none"
        viewBox="0 0 24 24"
      >
        <circle class="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" stroke-width="4" />
        <path
          class="opacity-75"
          fill="currentColor"
          d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4z"
        />
      </svg>
      <span class="text-sm">Loading component...</span>
    </div>
  </div>
</template>
