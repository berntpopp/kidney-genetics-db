<script setup lang="ts">
/**
 * The one form-level message for the account forms: errors are announced (role="alert"),
 * success is polite (role="status"). Danger/success tokens keep the text >= 4.5:1.
 */
import { CircleAlert, CircleCheck } from 'lucide-vue-next'

defineProps<{ tone?: 'error' | 'success' }>()
</script>

<template>
  <div
    :role="tone === 'success' ? 'status' : 'alert'"
    data-slot="form-alert"
    :class="[
      'flex items-start gap-2 rounded-md border p-3 text-sm',
      tone === 'success'
        ? 'border-success/30 bg-success-subtle text-success'
        : 'border-danger/30 bg-danger-subtle text-danger'
    ]"
  >
    <CircleCheck v-if="tone === 'success'" class="mt-0.5 size-4 shrink-0" aria-hidden="true" />
    <CircleAlert v-else class="mt-0.5 size-4 shrink-0" aria-hidden="true" />
    <div class="min-w-0 [&_a]:font-medium [&_a]:underline [&_a]:underline-offset-4">
      <slot />
    </div>
  </div>
</template>
