/**
 * Composable for standardized error handling across components.
 * Replaces repeated try/catch + error state patterns.
 */

import { ref } from 'vue'

interface ErrorState {
  message: string
  code?: number
  details?: unknown
}

export function useErrorHandler() {
  const error = ref<ErrorState | null>(null)
  const isError = ref(false)

  function handleError(err: unknown, fallbackMessage = 'An error occurred') {
    const apiErr = err as { response?: { status?: number; data?: { detail?: string } } }
    error.value = {
      message: apiErr.response?.data?.detail ?? fallbackMessage,
      code: apiErr.response?.status,
      details: err
    }
    isError.value = true
    window.logService?.error(fallbackMessage, err)
  }

  function clearError() {
    error.value = null
    isError.value = false
  }

  return { error, isError, handleError, clearError }
}
