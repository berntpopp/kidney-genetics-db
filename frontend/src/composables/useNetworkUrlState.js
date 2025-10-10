/**
 * Network URL State Management Composable
 *
 * Provides URL-based state persistence for network analysis.
 * Handles encoding/decoding, debouncing, and browser history integration.
 *
 * @module composables/useNetworkUrlState
 */

import { ref, computed } from 'vue'
import { useRouter, useRoute } from 'vue-router'
import {
  encodeNetworkState,
  decodeNetworkState,
  validateNetworkState
} from '@/utils/networkStateCodec'
import { debounce } from '@/utils/debounce'

/**
 * Composable for managing network state in URL
 *
 * @param {Object} options - Configuration options
 * @param {number} options.debounceMs - Debounce delay for URL updates (default: 800ms)
 * @param {number} options.version - Schema version (1=uncompressed, 2=compressed, default: 2)
 * @returns {Object} State management methods and reactive properties
 *
 * @example
 * const { syncStateToUrl, restoreStateFromUrl, isUrlState } = useNetworkUrlState()
 *
 * // Restore state on mount
 * onMounted(async () => {
 *   if (isUrlState.value) {
 *     const state = restoreStateFromUrl()
 *     if (state) {
 *       await applyRestoredState(state)
 *     }
 *   }
 * })
 *
 * // Sync state changes to URL
 * watch(networkState, () => {
 *   syncStateToUrl(networkState.value)
 * })
 */
export function useNetworkUrlState(options = {}) {
  const router = useRouter()
  const route = useRoute()

  const debounceMs = options.debounceMs ?? 800
  const version = options.version ?? 2

  // Reactive state
  const isEncoding = ref(false)
  const isDecoding = ref(false)
  const lastError = ref(null)

  /**
   * Check if current URL contains network state
   */
  const isUrlState = computed(() => {
    return !!(route.query.v && (route.query.c || route.query.genes))
  })

  /**
   * Restore network state from URL query parameters
   *
   * @returns {Object|null} Decoded state or null if no valid state
   */
  function restoreStateFromUrl() {
    isDecoding.value = true
    lastError.value = null

    try {
      // Check if URL has state parameters
      if (!isUrlState.value) {
        if (window.logService) {
          window.logService.debug('[useNetworkUrlState] No URL state found')
        }
        return null
      }

      // Decode state from URL
      const state = decodeNetworkState(route.query)

      // Validate state
      const validation = validateNetworkState(state)

      if (!validation.isValid) {
        throw new Error(`Invalid state: missing ${validation.missingFields.join(', ')}`)
      }

      if (window.logService) {
        window.logService.info('[useNetworkUrlState] State restored from URL', {
          version: route.query.v,
          geneCount: state.geneIds?.length || 0
        })
      }

      return state
    } catch (error) {
      lastError.value = error.message

      if (window.logService) {
        window.logService.error('[useNetworkUrlState] Failed to restore state from URL:', error)
      }

      // Show user-friendly error
      if (window.snackbar) {
        window.snackbar.error(`Failed to restore network state from URL: ${error.message}`, {
          timeout: 5000
        })
      }

      return null
    } finally {
      isDecoding.value = false
    }
  }

  /**
   * Encode state and update URL (debounced)
   * Does not add to browser history if state unchanged
   *
   * @param {Object} state - Network analysis state
   */
  const syncStateToUrl = debounce(state => {
    isEncoding.value = true
    lastError.value = null

    try {
      // Validate state before encoding
      const validation = validateNetworkState(state)
      if (!validation.isValid) {
        if (window.logService) {
          window.logService.debug('[useNetworkUrlState] Skipping URL sync - incomplete state', {
            missingFields: validation.missingFields
          })
        }
        return
      }

      // Encode state to query parameters
      const queryParams = encodeNetworkState(state, version)

      // Check if query params actually changed
      const currentQuery = route.query
      const paramsChanged = Object.keys(queryParams).some(
        key => queryParams[key] !== currentQuery[key]
      )

      if (!paramsChanged) {
        if (window.logService) {
          window.logService.debug('[useNetworkUrlState] Skipping URL sync - no changes')
        }
        return
      }

      // Update URL without adding to history (replace mode)
      router
        .replace({
          query: queryParams
        })
        .catch(err => {
          // NavigationDuplicated is expected and harmless
          if (err.name !== 'NavigationDuplicated') {
            throw err
          }
        })

      if (window.logService) {
        window.logService.debug('[useNetworkUrlState] URL synced', {
          version: queryParams.v,
          compressed: !!queryParams.c,
          geneCount: state.filteredGenes?.length || 0
        })
      }
    } catch (error) {
      lastError.value = error.message

      if (window.logService) {
        window.logService.error('[useNetworkUrlState] Failed to sync state to URL:', error)
      }

      // Silent failure for encoding - don't interrupt user workflow
      // Error is logged and available in lastError for debugging
    } finally {
      isEncoding.value = false
    }
  }, debounceMs)

  /**
   * Manually trigger URL sync (bypasses debounce)
   *
   * @param {Object} state - Network analysis state
   */
  function syncStateToUrlImmediate(state) {
    syncStateToUrl.cancel() // Cancel pending debounced call
    syncStateToUrl.flush(state) // Execute immediately
  }

  /**
   * Clear network state from URL
   */
  function clearUrlState() {
    router
      .replace({
        query: {}
      })
      .catch(err => {
        if (err.name !== 'NavigationDuplicated') {
          throw err
        }
      })

    if (window.logService) {
      window.logService.debug('[useNetworkUrlState] URL state cleared')
    }
  }

  /**
   * Generate shareable URL for current state
   *
   * @param {Object} state - Network analysis state
   * @returns {string} Full URL with encoded state
   */
  function generateShareableUrl(state) {
    try {
      const queryParams = encodeNetworkState(state, version)
      const query = new URLSearchParams(queryParams).toString()
      const baseUrl = window.location.origin + window.location.pathname

      return `${baseUrl}?${query}`
    } catch (error) {
      if (window.logService) {
        window.logService.error('[useNetworkUrlState] Failed to generate shareable URL:', error)
      }
      throw error
    }
  }

  /**
   * Copy shareable URL to clipboard
   *
   * @param {Object} state - Network analysis state
   * @returns {Promise<boolean>} True if copied successfully
   */
  async function copyShareableUrl(state) {
    try {
      const url = generateShareableUrl(state)

      await navigator.clipboard.writeText(url)

      if (window.logService) {
        window.logService.info('[useNetworkUrlState] Shareable URL copied to clipboard', {
          urlLength: url.length,
          geneCount: state.filteredGenes?.length || 0
        })
      }

      if (window.snackbar) {
        window.snackbar.success('Shareable URL copied to clipboard!')
      }

      return true
    } catch (error) {
      if (window.logService) {
        window.logService.error('[useNetworkUrlState] Failed to copy URL to clipboard:', error)
      }

      if (window.snackbar) {
        window.snackbar.error('Failed to copy URL to clipboard')
      }

      return false
    }
  }

  return {
    // Reactive state
    isEncoding,
    isDecoding,
    isUrlState,
    lastError,

    // Methods
    syncStateToUrl,
    syncStateToUrlImmediate,
    restoreStateFromUrl,
    clearUrlState,
    generateShareableUrl,
    copyShareableUrl
  }
}

export default useNetworkUrlState
