/**
 * Network Search Composable
 *
 * Provides reactive search functionality for network graph nodes.
 * Supports wildcard pattern matching (*, ?) for gene symbols.
 *
 * @module composables/useNetworkSearch
 */

import { ref, computed } from 'vue'
import type { Ref, ComputedRef } from 'vue'
import type cytoscape from 'cytoscape'
import { matchesWildcard, validatePattern } from '../utils/wildcardMatcher'

/** Return type for useNetworkSearch */
export interface NetworkSearchReturn {
  searchPattern: Ref<string>
  matchedNodeIds: Ref<Set<string>>
  isSearching: Ref<boolean>
  searchError: Ref<string | null>
  matchCount: ComputedRef<number>
  hasMatches: ComputedRef<boolean>
  hasPattern: ComputedRef<boolean>
  searchNodes: (cyInstance: cytoscape.Core | null, pattern: string) => cytoscape.NodeSingular[]
  clearSearch: () => void
  isNodeMatched: (nodeId: string) => boolean
  getSearchStats: () => SearchStats
}

/** Search statistics */
interface SearchStats {
  pattern: string
  matchCount: number
  hasMatches: boolean
  hasPattern: boolean
  isSearching: boolean
  error: string | null
}

/**
 * Composable for network search functionality
 *
 * @returns Search state and methods
 *
 * @example
 * const { searchPattern, matchCount, searchNodes, clearSearch } = useNetworkSearch()
 * const matches = searchNodes(cyInstance, "COL*")
 */
export function useNetworkSearch(): NetworkSearchReturn {
  // Reactive state
  const searchPattern = ref<string>('')
  const matchedNodeIds = ref<Set<string>>(new Set())
  const isSearching = ref<boolean>(false)
  const searchError = ref<string | null>(null)

  // Computed properties
  const matchCount = computed<number>(() => matchedNodeIds.value.size)
  const hasMatches = computed<boolean>(() => matchCount.value > 0)
  const hasPattern = computed<boolean>(() => searchPattern.value.trim().length > 0)

  /**
   * Search nodes by gene symbol with wildcard support
   *
   * @param cyInstance - Cytoscape instance
   * @param pattern - Search pattern (e.g., "COL*", "PKD?")
   * @returns Array of matched Cytoscape node elements
   *
   * @example
   * const matches = searchNodes(cyInstance, "COL*")
   * // Returns array of nodes matching pattern
   */
  function searchNodes(
    cyInstance: cytoscape.Core | null,
    pattern: string
  ): cytoscape.NodeSingular[] {
    isSearching.value = true
    searchError.value = null

    // Clear previous matches
    matchedNodeIds.value.clear()

    // Validate inputs
    if (!cyInstance) {
      searchError.value = 'Network instance not available'
      isSearching.value = false
      return []
    }

    if (!pattern || !pattern.trim()) {
      isSearching.value = false
      return []
    }

    const trimmedPattern = pattern.trim()

    // Validate pattern
    const validation = validatePattern(trimmedPattern)
    if (!validation.isValid) {
      searchError.value = validation.error
      isSearching.value = false
      return []
    }

    // Search all nodes
    const matches: cytoscape.NodeSingular[] = []
    let searchCount = 0

    try {
      cyInstance.nodes().forEach(node => {
        searchCount++
        // Get gene symbol from node data (prefer label, fallback to gene_id)
        const geneSymbol = (node.data('label') as string) || (node.data('gene_id') as string) || ''

        if (geneSymbol && matchesWildcard(geneSymbol, trimmedPattern)) {
          matches.push(node)
          matchedNodeIds.value.add(node.id())
        }
      })

      searchPattern.value = trimmedPattern

      // Log search results
      if (window.logService) {
        window.logService.info('[NetworkSearch] Search completed', {
          pattern: trimmedPattern,
          totalNodes: searchCount,
          matchCount: matches.length,
          matchPercentage: ((matches.length / searchCount) * 100).toFixed(1) + '%'
        })
      }
    } catch (error: unknown) {
      const msg = error instanceof Error ? error.message : String(error)
      searchError.value = 'Search failed: ' + msg
      if (window.logService) {
        window.logService.error('[NetworkSearch] Search error:', error)
      }
    } finally {
      isSearching.value = false
    }

    return matches
  }

  /**
   * Clear search state and results
   */
  function clearSearch(): void {
    searchPattern.value = ''
    matchedNodeIds.value.clear()
    searchError.value = null
    isSearching.value = false

    if (window.logService) {
      window.logService.debug('[NetworkSearch] Search cleared')
    }
  }

  /**
   * Check if a specific node ID is in the current search results
   *
   * @param nodeId - Cytoscape node ID
   * @returns True if node is in search results
   */
  function isNodeMatched(nodeId: string): boolean {
    return matchedNodeIds.value.has(nodeId)
  }

  /**
   * Get statistics about current search
   *
   * @returns Search statistics
   */
  function getSearchStats(): SearchStats {
    return {
      pattern: searchPattern.value,
      matchCount: matchCount.value,
      hasMatches: hasMatches.value,
      hasPattern: hasPattern.value,
      isSearching: isSearching.value,
      error: searchError.value
    }
  }

  return {
    // State
    searchPattern,
    matchedNodeIds,
    isSearching,
    searchError,

    // Computed
    matchCount,
    hasMatches,
    hasPattern,

    // Methods
    searchNodes,
    clearSearch,
    isNodeMatched,
    getSearchStats
  }
}

export default useNetworkSearch
