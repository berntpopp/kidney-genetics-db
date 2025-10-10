/**
 * Network Search Composable
 *
 * Provides reactive search functionality for network graph nodes.
 * Supports wildcard pattern matching (*, ?) for gene symbols.
 *
 * @module composables/useNetworkSearch
 */

import { ref, computed } from 'vue'
import { matchesWildcard, validatePattern } from '../utils/wildcardMatcher'

/**
 * Composable for network search functionality
 *
 * @returns {Object} Search state and methods
 *
 * @example
 * const { searchPattern, matchCount, searchNodes, clearSearch } = useNetworkSearch()
 * const matches = searchNodes(cyInstance, "COL*")
 */
export function useNetworkSearch() {
  // Reactive state
  const searchPattern = ref('')
  const matchedNodeIds = ref(new Set())
  const isSearching = ref(false)
  const searchError = ref(null)

  // Computed properties
  const matchCount = computed(() => matchedNodeIds.value.size)
  const hasMatches = computed(() => matchCount.value > 0)
  const hasPattern = computed(() => searchPattern.value.trim().length > 0)

  /**
   * Search nodes by gene symbol with wildcard support
   *
   * @param {Object} cyInstance - Cytoscape instance
   * @param {string} pattern - Search pattern (e.g., "COL*", "PKD?")
   * @returns {Array} Array of matched Cytoscape node elements
   *
   * @example
   * const matches = searchNodes(cyInstance, "COL*")
   * // Returns array of nodes matching pattern
   */
  function searchNodes(cyInstance, pattern) {
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
    const matches = []
    let searchCount = 0

    try {
      cyInstance.nodes().forEach(node => {
        searchCount++
        // Get gene symbol from node data (prefer label, fallback to gene_id)
        const geneSymbol = node.data('label') || node.data('gene_id') || ''

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
    } catch (error) {
      searchError.value = 'Search failed: ' + error.message
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
  function clearSearch() {
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
   * @param {string} nodeId - Cytoscape node ID
   * @returns {boolean} True if node is in search results
   */
  function isNodeMatched(nodeId) {
    return matchedNodeIds.value.has(nodeId)
  }

  /**
   * Get statistics about current search
   *
   * @returns {Object} Search statistics
   */
  function getSearchStats() {
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
