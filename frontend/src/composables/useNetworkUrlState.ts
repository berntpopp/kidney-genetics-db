/**
 * Network URL State Management Composable
 *
 * Provides URL-based state persistence for network analysis.
 * Handles encoding/decoding, debouncing, and browser history integration.
 *
 * @module composables/useNetworkUrlState
 */

import { ref, computed, onUnmounted } from 'vue'
import { toast } from 'vue-sonner'
import type { Ref, ComputedRef } from 'vue'
import { useRouter, useRoute } from 'vue-router'
import type { Router, RouteLocationNormalized } from 'vue-router'
import {
  encodeNetworkState,
  decodeNetworkState,
  validateNetworkState
} from '@/utils/networkStateCodec'
import type { NetworkState, QueryParams } from '@/utils/networkStateCodec'
import { debounce } from '@/utils/debounce'
import type { DebouncedFunction } from '@/utils/debounce'

/** Options for useNetworkUrlState */
interface NetworkUrlStateOptions {
  debounceMs?: number
  version?: number
}

/** Return type for useNetworkUrlState */
export interface NetworkUrlStateReturn {
  isEncoding: Ref<boolean>
  isDecoding: Ref<boolean>
  isUrlState: ComputedRef<boolean>
  lastError: Ref<string | null>
  syncStateToUrl: DebouncedFunction<(state: NetworkState) => void>
  syncStateToUrlImmediate: (state: NetworkState) => void
  restoreStateFromUrl: () => NetworkState | null
  clearUrlState: () => void
  generateShareableUrl: (state: NetworkState) => string
  copyShareableUrl: (state: NetworkState) => Promise<boolean>
}

/**
 * Composable for managing network state in URL
 *
 * @param options - Configuration options
 * @param options.debounceMs - Debounce delay for URL updates (default: 800ms)
 * @param options.version - Schema version (1=uncompressed, 2=compressed, default: 2)
 * @returns State management methods and reactive properties
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
export function useNetworkUrlState(options: NetworkUrlStateOptions = {}): NetworkUrlStateReturn {
  const router: Router = useRouter()
  const route: RouteLocationNormalized = useRoute()

  const debounceMs = options.debounceMs ?? 800
  const version = options.version ?? 2

  // Reactive state
  const isEncoding = ref<boolean>(false)
  const isDecoding = ref<boolean>(false)
  const lastError = ref<string | null>(null)

  /**
   * Check if current URL contains network state
   */
  const isUrlState = computed<boolean>(() => {
    return !!(route.query['v'] && (route.query['c'] ?? route.query['genes']))
  })

  /**
   * Restore network state from URL query parameters
   *
   * @returns Decoded state or null if no valid state
   */
  function restoreStateFromUrl(): NetworkState | null {
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

      // Decode state from URL — convert LocationQuery to QueryParams (string values only)
      const queryParams: QueryParams = {}
      for (const [key, val] of Object.entries(route.query)) {
        if (typeof val === 'string') {
          queryParams[key] = val
        }
      }
      const state = decodeNetworkState(queryParams)

      // Validate state
      const validation = validateNetworkState(state)

      if (!validation.isValid) {
        throw new Error(`Invalid state: missing ${validation.missingFields.join(', ')}`)
      }

      if (window.logService) {
        window.logService.info('[useNetworkUrlState] State restored from URL', {
          version: route.query['v'],
          geneCount: state.geneIds?.length ?? 0
        })
      }

      return state
    } catch (error: unknown) {
      const msg = error instanceof Error ? error.message : String(error)
      lastError.value = msg

      if (window.logService) {
        window.logService.error('[useNetworkUrlState] Failed to restore state from URL:', error)
      }

      // Show user-friendly error
      toast.error(`Failed to restore network state from URL: ${msg}`, {
        duration: Infinity
      })

      return null
    } finally {
      isDecoding.value = false
    }
  }

  /**
   * Encode state and update URL (debounced)
   * Does not add to browser history if state unchanged
   *
   * @param state - Network analysis state
   */
  const syncStateToUrl: DebouncedFunction<(state: NetworkState) => void> = debounce(
    (state: NetworkState) => {
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
          .catch((err: unknown) => {
            // NavigationDuplicated is expected and harmless
            const routerErr = err as { name?: string }
            if (routerErr.name !== 'NavigationDuplicated') {
              throw err
            }
          })

        if (window.logService) {
          window.logService.debug('[useNetworkUrlState] URL synced', {
            version: queryParams['v'],
            compressed: !!queryParams['c'],
            geneCount: state.filteredGenes?.length ?? 0
          })
        }
      } catch (error: unknown) {
        const msg = error instanceof Error ? error.message : String(error)
        lastError.value = msg

        if (window.logService) {
          window.logService.error('[useNetworkUrlState] Failed to sync state to URL:', error)
        }

        // Silent failure for encoding - don't interrupt user workflow
        // Error is logged and available in lastError for debugging
      } finally {
        isEncoding.value = false
      }
    },
    debounceMs
  )

  /**
   * Manually trigger URL sync (bypasses debounce)
   *
   * @param state - Network analysis state
   */
  function syncStateToUrlImmediate(state: NetworkState): void {
    syncStateToUrl.cancel() // Cancel pending debounced call
    syncStateToUrl.flush(state) // Execute immediately
  }

  /**
   * Clear network state from URL
   */
  function clearUrlState(): void {
    router
      .replace({
        query: {}
      })
      .catch((err: unknown) => {
        const routerErr = err as { name?: string }
        if (routerErr.name !== 'NavigationDuplicated') {
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
   * @param state - Network analysis state
   * @returns Full URL with encoded state
   */
  function generateShareableUrl(state: NetworkState): string {
    try {
      const queryParams = encodeNetworkState(state, version)
      const query = new URLSearchParams(queryParams).toString()
      const baseUrl = window.location.origin + window.location.pathname

      return `${baseUrl}?${query}`
    } catch (error: unknown) {
      if (window.logService) {
        window.logService.error('[useNetworkUrlState] Failed to generate shareable URL:', error)
      }
      throw error
    }
  }

  /**
   * Copy shareable URL to clipboard
   *
   * @param state - Network analysis state
   * @returns True if copied successfully
   */
  async function copyShareableUrl(state: NetworkState): Promise<boolean> {
    try {
      const url = generateShareableUrl(state)

      await navigator.clipboard.writeText(url)

      if (window.logService) {
        window.logService.info('[useNetworkUrlState] Shareable URL copied to clipboard', {
          urlLength: url.length,
          geneCount: state.filteredGenes?.length ?? 0
        })
      }

      toast.success('Shareable URL copied to clipboard!', { duration: 5000 })

      return true
    } catch (error: unknown) {
      if (window.logService) {
        window.logService.error('[useNetworkUrlState] Failed to copy URL to clipboard:', error)
      }

      toast.error('Failed to copy URL to clipboard', { duration: Infinity })

      return false
    }
  }

  // Cleanup debounced function on unmount to prevent memory leaks
  onUnmounted(() => {
    if (syncStateToUrl && syncStateToUrl.cancel) {
      syncStateToUrl.cancel()
    }
  })

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
