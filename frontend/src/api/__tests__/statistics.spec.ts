/**
 * Tests for statistics.ts API module
 * Mocks the Axios client and verifies correct endpoint calls.
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

import apiClient from '@/api/client'
import { statisticsApi } from '@/api/statistics'

const mockApiClient = apiClient as {
  get: ReturnType<typeof vi.fn>
}

/** Helper to create a mock statistics response */
function makeStatResponse<T>(data: T): AxiosResponse {
  return {
    data: { data, meta: { total: 1 } }
  } as unknown as AxiosResponse
}

describe('statisticsApi', () => {
  beforeEach(() => {
    vi.clearAllMocks()
  })

  describe('getSummaryStatistics', () => {
    it('should call /api/statistics/summary and return data + meta', async () => {
      const mockData = {
        total_genes: 571,
        genes_with_evidence: 300,
        total_evidence_entries: 5000,
        sources: ['panelapp', 'clingen']
      }
      mockApiClient.get.mockResolvedValue(makeStatResponse(mockData))

      const result = await statisticsApi.getSummaryStatistics()

      expect(mockApiClient.get).toHaveBeenCalledWith('/api/statistics/summary')
      expect(result.data).toEqual(mockData)
      expect(result.meta).toBeDefined()
    })
  })

  describe('getSourceDistributions', () => {
    it('should call /api/statistics/source-distributions', async () => {
      mockApiClient.get.mockResolvedValue(makeStatResponse([]))

      await statisticsApi.getSourceDistributions()

      expect(mockApiClient.get).toHaveBeenCalledWith(
        expect.stringContaining('/api/statistics/source-distributions')
      )
    })

    it('should include tier filter in URL when tiers provided', async () => {
      mockApiClient.get.mockResolvedValue(makeStatResponse([]))

      await statisticsApi.getSourceDistributions(['1', '2'], true)

      const calledUrl = mockApiClient.get.mock.calls[0][0] as string
      expect(calledUrl).toContain('filter%5Btier%5D=1%2C2')
    })

    it('should include hide_zero_scores parameter', async () => {
      mockApiClient.get.mockResolvedValue(makeStatResponse([]))

      await statisticsApi.getSourceDistributions(null, false)

      const calledUrl = mockApiClient.get.mock.calls[0][0] as string
      expect(calledUrl).toContain('filter%5Bhide_zero_scores%5D=false')
    })
  })

  describe('getSourceOverlaps', () => {
    it('should call /api/statistics/source-overlaps', async () => {
      mockApiClient.get.mockResolvedValue(makeStatResponse({ sets: [], intersections: [] }))

      await statisticsApi.getSourceOverlaps()

      expect(mockApiClient.get).toHaveBeenCalledWith(
        expect.stringContaining('/api/statistics/source-overlaps')
      )
    })

    it('should append each source as separate query parameter', async () => {
      mockApiClient.get.mockResolvedValue(makeStatResponse({ sets: [], intersections: [] }))

      await statisticsApi.getSourceOverlaps(['panelapp', 'clingen'])

      const calledUrl = mockApiClient.get.mock.calls[0][0] as string
      expect(calledUrl).toContain('sources=panelapp')
      expect(calledUrl).toContain('sources=clingen')
    })
  })

  describe('getEvidenceComposition', () => {
    it('should call /api/statistics/evidence-composition', async () => {
      mockApiClient.get.mockResolvedValue(makeStatResponse([]))

      await statisticsApi.getEvidenceComposition()

      expect(mockApiClient.get).toHaveBeenCalledWith(
        expect.stringContaining('/api/statistics/evidence-composition')
      )
    })
  })
})
