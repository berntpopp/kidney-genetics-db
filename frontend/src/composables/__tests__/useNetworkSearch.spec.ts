/**
 * useNetworkSearch Composable Tests
 *
 * Tests for network graph search with wildcard pattern matching.
 */

import { describe, it, expect, vi, beforeEach } from 'vitest'
import { useNetworkSearch } from '@/composables/useNetworkSearch'

// Stub window.logService
vi.stubGlobal('logService', {
  debug: vi.fn(),
  info: vi.fn(),
  warn: vi.fn(),
  error: vi.fn(),
  critical: vi.fn()
})

/** Create a mock Cytoscape node */
function makeMockNode(label: string, gene_id?: string) {
  return {
    data: (key: string) => {
      if (key === 'label') return label
      if (key === 'gene_id') return gene_id ?? ''
      return ''
    },
    id: () => label.toLowerCase()
  }
}

/** Create a minimal mock Cytoscape instance */
function makeMockCy(nodes: ReturnType<typeof makeMockNode>[]) {
  return {
    nodes: () => ({
      forEach: (cb: (node: ReturnType<typeof makeMockNode>) => void) => nodes.forEach(cb)
    })
  }
}

describe('useNetworkSearch', () => {
  beforeEach(() => {
    vi.clearAllMocks()
  })

  describe('initial state', () => {
    it('starts with empty search and no matches', () => {
      const { searchPattern, matchCount, hasPattern, hasMatches } = useNetworkSearch()

      expect(searchPattern.value).toBe('')
      expect(matchCount.value).toBe(0)
      expect(hasPattern.value).toBe(false)
      expect(hasMatches.value).toBe(false)
    })
  })

  describe('searchNodes', () => {
    it('returns empty array when cyInstance is null', () => {
      const { searchNodes, searchError } = useNetworkSearch()

      const result = searchNodes(null, 'COL*')

      expect(result).toHaveLength(0)
      expect(searchError.value).toBe('Network instance not available')
    })

    it('returns empty array for empty pattern', () => {
      const { searchNodes } = useNetworkSearch()

      const cy = makeMockCy([makeMockNode('COL4A1')]) as any

      const result = searchNodes(cy, '')

      expect(result).toHaveLength(0)
    })

    it('matches nodes with wildcard * pattern', () => {
      const { searchNodes, matchCount } = useNetworkSearch()
      const nodes = [
        makeMockNode('COL4A1'),
        makeMockNode('COL4A2'),
        makeMockNode('PKD1'),
        makeMockNode('NPHS1')
      ]

      const cy = makeMockCy(nodes) as any

      const result = searchNodes(cy, 'COL*')

      expect(result).toHaveLength(2)
      expect(matchCount.value).toBe(2)
    })

    it('matches nodes with wildcard ? pattern (single char)', () => {
      const { searchNodes } = useNetworkSearch()
      const nodes = [makeMockNode('PKD1'), makeMockNode('PKD2'), makeMockNode('PKD10')]

      const cy = makeMockCy(nodes) as any

      const result = searchNodes(cy, 'PKD?')

      // PKD? matches PKD1, PKD2 but NOT PKD10 (? = exactly one char)
      expect(result).toHaveLength(2)
    })

    it('returns empty array for invalid pattern (too many wildcards)', () => {
      const { searchNodes, searchError } = useNetworkSearch()

      const cy = makeMockCy([makeMockNode('COL4A1')]) as any

      const result = searchNodes(cy, '***')

      expect(result).toHaveLength(0)
      expect(searchError.value).toBeTruthy()
    })
  })

  describe('clearSearch', () => {
    it('resets all search state', () => {
      const { searchNodes, clearSearch, searchPattern, matchCount } = useNetworkSearch()
      const nodes = [makeMockNode('COL4A1'), makeMockNode('PKD1')]

      const cy = makeMockCy(nodes) as any

      searchNodes(cy, 'COL*')
      expect(matchCount.value).toBe(1)

      clearSearch()

      expect(searchPattern.value).toBe('')
      expect(matchCount.value).toBe(0)
    })
  })

  describe('isNodeMatched', () => {
    it('returns true for matched node IDs', () => {
      const { searchNodes, isNodeMatched } = useNetworkSearch()
      const nodes = [makeMockNode('COL4A1'), makeMockNode('PKD1')]

      const cy = makeMockCy(nodes) as any

      searchNodes(cy, 'COL*')

      // node IDs are lowercased labels in our mock
      expect(isNodeMatched('col4a1')).toBe(true)
      expect(isNodeMatched('pkd1')).toBe(false)
    })
  })
})
