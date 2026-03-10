<script setup lang="ts">
import { computed } from 'vue'

const props = defineProps<{
  /** Error message to display */
  error?: Error
}>()

const emit = defineEmits<{
  retry: []
}>()

const message = computed(() => props.error?.message ?? 'Failed to load component')
</script>

<template>
  <div
    class="flex items-center justify-center rounded-lg border border-destructive/30 bg-destructive/5 p-6"
    style="min-height: 200px"
  >
    <div class="flex flex-col items-center gap-3 text-center">
      <div class="rounded-full bg-destructive/10 p-3">
        <svg
          class="h-6 w-6 text-destructive"
          xmlns="http://www.w3.org/2000/svg"
          fill="none"
          viewBox="0 0 24 24"
          stroke-width="1.5"
          stroke="currentColor"
        >
          <path
            stroke-linecap="round"
            stroke-linejoin="round"
            d="M12 9v3.75m-9.303 3.376c-.866 1.5.217 3.374 1.948 3.374h14.71c1.73 0 2.813-1.874 1.948-3.374L13.949 3.378c-.866-1.5-3.032-1.5-3.898 0L2.697 16.126zM12 15.75h.007v.008H12v-.008z"
          />
        </svg>
      </div>
      <p class="text-sm text-muted-foreground">{{ message }}</p>
      <button
        class="inline-flex items-center gap-1.5 rounded-md bg-primary px-3 py-1.5 text-sm text-primary-foreground hover:bg-primary/90"
        @click="emit('retry')"
      >
        Try again
      </button>
    </div>
  </div>
</template>
