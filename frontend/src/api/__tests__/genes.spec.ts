/**
 * Tests for genes.ts API module
 * Mocks the Axios client and verifies correct request construction.
 */

import { describe, it, expect, vi, beforeEach } from 'vitest'
import type { AxiosResponse } from 'axios'

// Mock the API client
vi.mock('@/api/client', () => ({
  default: {
    get: vi.fn(),
    post: vi.fn(),
    put: vi.fn(),
    delete: vi.fn()
  }
}))

// Mock networkAnalysis config dependency
vi.mock('@/config/networkAnalysis', () => ({
  networkAnalysisConfig: {
    geneSelection: {
      maxGeneIds: 1000
    }
  }
}))

// Stub window.logService
vi.stubGlobal('logService', {
  debug: vi.fn(),
  info: vi.fn(),
  warn: vi.fn(),
  error: vi.fn()
})

import apiClient from '@/api/client'
import { geneApi } from '@/api/genes'

const mockApiClient = apiClient as {
  get: ReturnType<typeof vi.fn>
  post: ReturnType<typeof vi.fn>
}

/** Helper to create a mock JSON:API list response */
function makeGeneListResponse(items: Array<Record<string, unknown>> = []) {
  return {
    data: {
      data: items.map((attrs, i) => ({ id: i + 1, type: 'gene', attributes: attrs })),
      meta: { total: items.length, page: 1, per_page: 20, page_count: 1 }
    }
  } as unknown as AxiosResponse
}

describe('geneApi', () => {
  beforeEach(() => {
    vi.clearAllMocks()
  })

  describe('getGenes', () => {
    it('should call /api/genes/ with correct pagination params', async () => {
      const mockResponse = makeGeneListResponse([
        { gene_symbol: 'PKD1', hgnc_id: 'HGNC:9008', gene_score: 0.9 }
      ])
      mockApiClient.get.mockResolvedValue(mockResponse)

      const result = await geneApi.getGenes({ page: 2, perPage: 10 })

      expect(mockApiClient.get).toHaveBeenCalledWith('/api/genes/', {
        params: expect.objectContaining({
          'page[number]': 2,
          'page[size]': 10
        })
      })
      expect(result.items).toHaveLength(1)
      expect(result.total).toBe(1)
      expect(result.page).toBe(1)
    })

    it('should include filter params when search is provided', async () => {
      mockApiClient.get.mockResolvedValue(makeGeneListResponse([]))

      await geneApi.getGenes({ search: 'PKD', source: 'panelapp' })

      expect(mockApiClient.get).toHaveBeenCalledWith('/api/genes/', {
        params: expect.objectContaining({
          'filter[search]': 'PKD',
          'filter[source]': 'panelapp'
        })
      })
    })

    it('should build sort parameter with minus prefix for descending', async () => {
      mockApiClient.get.mockResolvedValue(makeGeneListResponse([]))

      await geneApi.getGenes({ sortBy: 'gene_score', sortDesc: true })

      expect(mockApiClient.get).toHaveBeenCalledWith('/api/genes/', {
        params: expect.objectContaining({
          sort: '-gene_score'
        })
      })
    })
  })

  describe('getGene', () => {
    it('should call /api/genes/:symbol and flatten JSON:API response', async () => {
      mockApiClient.get.mockResolvedValue({
        data: {
          data: {
            id: 42,
            type: 'gene',
            attributes: { gene_symbol: 'PKD1', hgnc_id: 'HGNC:9008' }
          }
        }
      } as unknown as AxiosResponse)

      const result = await geneApi.getGene('PKD1')

      expect(mockApiClient.get).toHaveBeenCalledWith('/api/genes/PKD1')
      expect(result.id).toBe(42)
      expect(result.gene_symbol).toBe('PKD1')
    })
  })

  describe('getGeneEvidence', () => {
    it('should call /api/genes/:symbol/evidence', async () => {
      mockApiClient.get.mockResolvedValue({
        data: {
          data: [{ id: 1, type: 'evidence', attributes: { source_name: 'panelapp' } }],
          meta: {}
        }
      } as unknown as AxiosResponse)

      const result = await geneApi.getGeneEvidence('PKD1')

      expect(mockApiClient.get).toHaveBeenCalledWith('/api/genes/PKD1/evidence')
      expect(result.evidence).toHaveLength(1)
      expect(result.evidence[0].source_name).toBe('panelapp')
    })
  })

  describe('getHPOClassifications', () => {
    it('should return empty result when no gene IDs provided', async () => {
      const result = await geneApi.getHPOClassifications([])

      expect(mockApiClient.post).not.toHaveBeenCalled()
      expect(result.data).toHaveLength(0)
    })

    it('should post gene IDs to /api/genes/hpo-classifications', async () => {
      mockApiClient.post.mockResolvedValue({
        data: {
          data: [
            { gene_id: 1, clinical_group: 'nephropathy', onset_group: null, is_syndromic: false }
          ],
          metadata: { cached: false, gene_count: 1, fetch_time_ms: 10 }
        }
      } as unknown as AxiosResponse)

      await geneApi.getHPOClassifications([1, 2, 3])

      expect(mockApiClient.post).toHaveBeenCalledWith('/api/genes/hpo-classifications', {
        gene_ids: [1, 2, 3]
      })
    })
  })
})
