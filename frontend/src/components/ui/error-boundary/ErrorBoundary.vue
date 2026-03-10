<script setup lang="ts">
import { ref, onErrorCaptured } from 'vue'

const props = withDefaults(
  defineProps<{
    /** Message shown when an error is caught */
    fallbackMessage?: string
    /** Optional callback when user clicks "Try again" */
    onReset?: () => void
  }>(),
  {
    fallbackMessage: 'Something went wrong while rendering this section.'
  }
)

const hasError = ref(false)
const errorMessage = ref('')

onErrorCaptured((err: Error, instance, info) => {
  hasError.value = true
  errorMessage.value = err.message || 'Unknown error'

  // Log via logService (feeds into logStore → LogViewer + backend reporting)
  window.logService?.error('ErrorBoundary caught render error', {
    error: err.message,
    stack: err.stack,
    info,
    component: instance?.$options?.name || instance?.$options?.__name || 'unknown'
  })

  // Stop propagation — this boundary handles the error
  return false
})

function handleReset() {
  hasError.value = false
  errorMessage.value = ''
  if (props.onReset) {
    props.onReset()
  }
}
</script>

<template>
  <slot v-if="!hasError" />
  <div
    v-else
    class="flex items-center justify-center rounded-lg border border-destructive/30 bg-destructive/5 p-6"
    role="alert"
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
      <p class="text-sm font-medium text-foreground">{{ fallbackMessage }}</p>
      <p v-if="errorMessage" class="max-w-md text-xs text-muted-foreground">
        {{ errorMessage }}
      </p>
      <button
        class="inline-flex items-center gap-1.5 rounded-md bg-primary px-3 py-1.5 text-sm text-primary-foreground hover:bg-primary/90"
        @click="handleReset"
      >
        <svg
          class="h-4 w-4"
          xmlns="http://www.w3.org/2000/svg"
          fill="none"
          viewBox="0 0 24 24"
          stroke-width="1.5"
          stroke="currentColor"
        >
          <path
            stroke-linecap="round"
            stroke-linejoin="round"
            d="M16.023 9.348h4.992v-.001M2.985 19.644v-4.992m0 0h4.992m-4.993 0l3.181 3.183a8.25 8.25 0 0013.803-3.7M4.031 9.865a8.25 8.25 0 0113.803-3.7l3.181 3.182"
          />
        </svg>
        Try again
      </button>
    </div>
  </div>
</template>
