/**
 * Gene API endpoints - JSON:API compliant
 */

import apiClient from './client'
import type { Gene, GeneListParams } from '@/types/gene'
import { networkAnalysisConfig } from '@/config/networkAnalysis'

/** JSON:API item wrapper returned from the backend */
interface JsonApiItem<T> {
  id: number
  type: string
  attributes: T
}

/** JSON:API list response meta from the /genes/ endpoint */
interface GeneListMeta {
  total: number
  page: number
  per_page: number
  page_count: number
  [key: string]: unknown
}

/** Flattened result returned from getGenes / getGenesByIds */
export interface GeneListResult {
  items: Gene[]
  total: number
  page: number
  perPage: number
  pageCount: number
  meta: Record<string, unknown>
}

/** Evidence item returned from getGeneEvidence */
export interface GeneEvidenceItem {
  id: number
  [key: string]: unknown
}

/** Evidence list result returned from getGeneEvidence */
export interface GeneEvidenceResult {
  evidence: GeneEvidenceItem[]
  meta: Record<string, unknown>
}

/** HPO classification response */
export interface HPOClassificationsResult {
  data: Array<{
    gene_id: number
    clinical_group: string | null
    onset_group: string | null
    is_syndromic: boolean | null
    [key: string]: unknown
  }>
  metadata: {
    cached: boolean
    gene_count: number
    fetch_time_ms: number
    [key: string]: unknown
  }
}

/** Options for getGenesByIds */
export interface GetGenesByIdsOptions {
  sortBy?: string | null
  sortDesc?: boolean
}

export const geneApi = {
  /**
   * Get paginated list of genes
   */
  async getGenes(params: GeneListParams = {}): Promise<GeneListResult> {
    const {
      page = 1,
      perPage = 20,
      search = '',
      minScore = null,
      maxScore = null,
      minCount = null,
      maxCount = null,
      source = null,
      tiers = null,
      sortBy = null,
      sortDesc = false,
      hideZeroScores = true
    } = params

    // Build JSON:API query parameters
    const queryParams: Record<string, unknown> = {
      'page[number]': page,
      'page[size]': perPage
    }

    // Add filters (only if values are provided)
    if (search) queryParams['filter[search]'] = search
    if (minScore !== null) queryParams['filter[min_score]'] = minScore
    if (maxScore !== null) queryParams['filter[max_score]'] = maxScore
    if (minCount !== null) queryParams['filter[min_count]'] = minCount
    if (maxCount !== null) queryParams['filter[max_count]'] = maxCount
    if (source) queryParams['filter[source]'] = source
    if (tiers && tiers.length > 0) {
      // Join multiple tiers with commas for OR logic
      queryParams['filter[tier]'] = tiers.join(',')
    }

    // Hide zero scores filter (explicitly set to control default behavior)
    queryParams['filter[hide_zero_scores]'] = hideZeroScores

    // Build sort parameter (JSON:API spec: prefix with - for descending)
    if (sortBy) {
      const sortPrefix = sortDesc ? '-' : ''
      queryParams.sort = `${sortPrefix}${sortBy}`
    }

    const response = await apiClient.get<{ data: JsonApiItem<Omit<Gene, 'id'>>[], meta: GeneListMeta }>(
      '/api/genes/',
      { params: queryParams }
    )

    // Transform JSON:API response to simpler format for Vue components
    return {
      items: response.data.data.map(item => ({
        id: item.id,
        ...item.attributes
      })),
      total: response.data.meta.total,
      page: response.data.meta.page,
      perPage: response.data.meta.per_page,
      pageCount: response.data.meta.page_count,
      meta: response.data.meta
    }
  },

  /**
   * Get single gene by symbol
   */
  async getGene(symbol: string): Promise<Gene> {
    const response = await apiClient.get<{ data: JsonApiItem<Omit<Gene, 'id'>> }>(
      `/api/genes/${symbol}`
    )

    // Transform JSON:API response
    return {
      id: response.data.data.id,
      ...response.data.data.attributes
    }
  },

  /**
   * Get evidence for a gene
   */
  async getGeneEvidence(symbol: string): Promise<GeneEvidenceResult> {
    const response = await apiClient.get<{
      data: JsonApiItem<Record<string, unknown>>[]
      meta: Record<string, unknown>
    }>(`/api/genes/${symbol}/evidence`)

    // Transform JSON:API response
    return {
      evidence: response.data.data.map(item => ({
        id: item.id,
        ...item.attributes
      })),
      meta: response.data.meta
    }
  },

  /**
   * Get annotations for a gene (including gnomAD data)
   */
  async getGeneAnnotations(geneId: number): Promise<Record<string, unknown>> {
    const response = await apiClient.get<Record<string, unknown>>(
      `/api/annotations/genes/${geneId}/annotations`
    )
    return response.data
  },

  /**
   * Get HPO classifications for multiple genes
   */
  async getHPOClassifications(geneIds: number[]): Promise<HPOClassificationsResult> {
    if (!geneIds || geneIds.length === 0) {
      return { data: [], metadata: { cached: false, gene_count: 0, fetch_time_ms: 0 } }
    }

    const response = await apiClient.post<HPOClassificationsResult>('/api/genes/hpo-classifications', {
      gene_ids: geneIds
    })

    return response.data
  },

  /**
   * Get genes by IDs (for URL state restoration)
   */
  async getGenesByIds(
    geneIds: number[],
    options: GetGenesByIdsOptions = {}
  ): Promise<GeneListResult> {
    window.logService?.info('[geneApi.getGenesByIds] Called with', {
      requestedCount: geneIds?.length || 0,
      firstFiveIds: geneIds?.slice(0, 5),
      options
    })

    if (!geneIds || geneIds.length === 0) {
      window.logService?.warn('[geneApi.getGenesByIds] No gene IDs provided')
      return {
        items: [],
        total: 0,
        page: 1,
        perPage: 20,
        pageCount: 0,
        meta: {}
      }
    }

    // Validate max gene IDs (backend limit from config)
    const maxGeneIds = networkAnalysisConfig.geneSelection.maxGeneIds
    if (geneIds.length > maxGeneIds) {
      throw new Error(`Maximum ${maxGeneIds} gene IDs allowed per request`)
    }

    const { sortBy = null, sortDesc = false } = options

    // Fetch all genes with pagination (API max is 100 per page)
    const allGenes: Gene[] = []
    const perPage = 100 // API maximum
    let page = 1

    // Build sort parameter (JSON:API spec: prefix with - for descending)
    let sortParam: string | null = null
    if (sortBy) {
      const sortPrefix = sortDesc ? '-' : ''
      sortParam = `${sortPrefix}${sortBy}`
    }

    // Fetch pages until we have all genes
    while (true) {
      const queryParams: Record<string, unknown> = {
        'filter[ids]': geneIds.join(','),
        'page[number]': page,
        'page[size]': perPage
      }

      if (sortParam) {
        queryParams.sort = sortParam
      }

      window.logService?.debug('[geneApi.getGenesByIds] Fetching page', {
        page,
        perPage,
        currentTotal: allGenes.length
      })

      const response = await apiClient.get<{
        data: JsonApiItem<Omit<Gene, 'id'>>[]
        meta: GeneListMeta
      }>('/api/genes/', { params: queryParams })

      const pageGenes: Gene[] = response.data.data.map(item => ({
        id: item.id,
        ...item.attributes
      }))

      window.logService?.debug('[geneApi.getGenesByIds] Page received', {
        page,
        receivedCount: pageGenes.length,
        metaTotal: response.data.meta.total,
        cumulativeTotal: allGenes.length + pageGenes.length
      })

      allGenes.push(...pageGenes)

      // Stop if we've fetched all genes or this page was not full
      if (allGenes.length >= response.data.meta.total || pageGenes.length < perPage) {
        window.logService?.info('[geneApi.getGenesByIds] Pagination complete', {
          totalPages: page,
          finalCount: allGenes.length,
          metaTotal: response.data.meta.total
        })
        break
      }

      page++
    }

    // Transform JSON:API response to simpler format for Vue components
    const result: GeneListResult = {
      items: allGenes,
      total: allGenes.length,
      page: 1,
      perPage: allGenes.length,
      pageCount: 1,
      meta: {}
    }

    window.logService?.info('[geneApi.getGenesByIds] Returning', {
      returnedCount: result.items.length,
      requestedCount: geneIds.length,
      match: result.items.length === geneIds.length ? 'ok' : 'MISMATCH!'
    })

    return result
  }
}
