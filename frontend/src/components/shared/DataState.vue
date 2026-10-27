<script setup lang="ts">
/**
 * One loading / error / empty pattern (DESIGN.md Data state). Precedence: loading, then
 * error, then empty, then the default slot. A failed load never renders as empty.
 * Give the loading slot a skeleton in the final layout; the fallback reserves `minHeight`.
 */
import { computed } from 'vue'
import { CircleX, Inbox, RotateCw } from 'lucide-vue-next'
import { Button } from '@/components/ui/button'

const props = withDefaults(
  defineProps<{
    loading?: boolean
    /** Truthy means the load failed; a string or Error supplies the message */
    error?: string | Error | boolean | null
    empty?: boolean
    /** Why there is nothing to show, e.g. "No genes match these filters." */
    emptyMessage?: string
    /** What failed, e.g. "Could not load releases" */
    errorTitle?: string
    /** Height reserved by the fallback skeleton */
    minHeight?: string
  }>(),
  {
    error: null,
    emptyMessage: 'Nothing to show yet.',
    errorTitle: 'Could not load data',
    minHeight: '8rem'
  }
)

defineEmits<{ retry: [] }>()

const errorMessage = computed(() => {
  if (props.error instanceof Error) return props.error.message
  return typeof props.error === 'string' ? props.error : ''
})
</script>

<template>
  <div v-if="loading" aria-busy="true" data-slot="data-state" data-state="loading">
    <span class="sr-only" role="status">Loading…</span>
    <slot name="loading">
      <div class="space-y-3" :style="{ minHeight }" aria-hidden="true">
        <div class="h-4 w-2/3 rounded-md bg-muted motion-safe:animate-pulse" />
        <div class="h-4 w-full rounded-md bg-muted motion-safe:animate-pulse" />
        <div class="h-4 w-5/6 rounded-md bg-muted motion-safe:animate-pulse" />
      </div>
    </slot>
  </div>
  <div
    v-else-if="error"
    role="alert"
    data-slot="data-state"
    data-state="error"
    class="flex flex-col items-start gap-3 rounded-lg border border-danger/30 bg-danger-subtle p-4 sm:flex-row sm:items-center"
  >
    <slot name="error" :message="errorMessage">
      <CircleX class="size-5 shrink-0 text-danger" aria-hidden="true" />
      <div class="min-w-0 flex-1">
        <p class="text-sm font-medium text-danger">{{ errorTitle }}</p>
        <p v-if="errorMessage" class="text-sm break-words text-foreground">{{ errorMessage }}</p>
      </div>
      <Button variant="outline" size="sm" @click="$emit('retry')">
        <RotateCw aria-hidden="true" />
        Retry
      </Button>
    </slot>
  </div>
  <div
    v-else-if="empty"
    role="status"
    data-slot="data-state"
    data-state="empty"
    class="flex flex-col items-center gap-2 rounded-lg border border-dashed px-4 py-8 text-center"
  >
    <slot name="empty">
      <Inbox class="size-6 text-muted-foreground" aria-hidden="true" />
      <p class="text-sm text-muted-foreground">{{ emptyMessage }}</p>
    </slot>
  </div>
  <slot v-else />
</template>
