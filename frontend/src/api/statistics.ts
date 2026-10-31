/**
 * Statistics API endpoints for data visualization
 */

import apiClient from './client'

/** Generic statistics response wrapper */
export interface StatisticsResult<T = unknown> {
  data: T
  meta: Record<string, unknown>
}

/** Source overlap (UpSet plot) data */
export interface SourceOverlapData {
  sets: string[]
  intersections: Array<{ sets: string[]; size: number }>
  [key: string]: unknown
}

/** Source distribution data for a single source */
export interface SourceDistributionItem {
  source: string
  count: number
  [key: string]: unknown
}

/** Evidence composition data */
export interface EvidenceCompositionItem {
  tier: string
  count: number
  percentage: number
  [key: string]: unknown
}

/** Summary statistics */
export interface SummaryStatisticsData {
  total_genes: number
  genes_with_evidence: number
  total_evidence_entries: number
  sources: string[]
  [key: string]: unknown
}

// Statistics change only with pipeline runs: tab switches and toggles back to a seen view
// reuse the response instead of refetching (and hitting the rate limit). Failures are not kept.
const CACHE_TTL_MS = 5 * 60 * 1000
const cache = new Map<string, { at: number; promise: Promise<unknown> }>()

function cachedGet<T>(url: string): Promise<T> {
  const hit = cache.get(url)
  if (hit && Date.now() - hit.at < CACHE_TTL_MS) return hit.promise as Promise<T>
  const promise = apiClient.get<T>(url).then(r => r.data)
  promise.catch(() => cache.delete(url))
  cache.set(url, { at: Date.now(), promise })
  return promise
}

export const statisticsApi = {
  /**
   * Get gene intersections between data sources for UpSet plot
   */
  async getSourceOverlaps(
    sources: string[] | null = null,
    tiers: string[] | null = null,
    hideZeroScores: boolean = true
  ): Promise<StatisticsResult<SourceOverlapData>> {
    const params = new URLSearchParams()

    // Add sources as query parameters if provided
    if (sources && sources.length > 0) {
      sources.forEach(source => params.append('sources', source))
    }

    // Add tier filter parameter if provided (comma-separated for multi-select with OR logic)
    if (tiers && tiers.length > 0) {
      params.append('filter[tier]', tiers.join(','))
    }

    // Add hide_zero_scores parameter
    params.append('filter[hide_zero_scores]', hideZeroScores.toString())

    const queryString = params.toString()
    const url = queryString
      ? `/api/statistics/source-overlaps?${queryString}`
      : '/api/statistics/source-overlaps'

    const body = await cachedGet<StatisticsResult<SourceOverlapData>>(url)
    return { data: body.data, meta: body.meta }
  },

  /**
   * Get source count distributions for bar charts
   */
  async getSourceDistributions(
    tiers: string[] | null = null,
    hideZeroScores: boolean = true
  ): Promise<StatisticsResult<SourceDistributionItem[]>> {
    const params = new URLSearchParams()

    // Add tier filter parameter if provided (comma-separated for multi-select with OR logic)
    if (tiers && tiers.length > 0) {
      params.append('filter[tier]', tiers.join(','))
    }

    // Add hide_zero_scores parameter
    params.append('filter[hide_zero_scores]', hideZeroScores.toString())

    const queryString = params.toString()
    const url = queryString
      ? `/api/statistics/source-distributions?${queryString}`
      : '/api/statistics/source-distributions'

    const body = await cachedGet<StatisticsResult<SourceDistributionItem[]>>(url)
    return { data: body.data, meta: body.meta }
  },

  /**
   * Get evidence quality and composition analysis
   */
  async getEvidenceComposition(
    tiers: string[] | null = null,
    hideZeroScores: boolean = true
  ): Promise<StatisticsResult<EvidenceCompositionItem[]>> {
    const params = new URLSearchParams()

    // Add tier filter parameter if provided (comma-separated for multi-select with OR logic)
    if (tiers && tiers.length > 0) {
      params.append('filter[tier]', tiers.join(','))
    }

    // Always pass hide_zero_scores parameter (matches /genes endpoint behavior)
    params.append('filter[hide_zero_scores]', hideZeroScores.toString())

    const queryString = params.toString()
    const url = `/api/statistics/evidence-composition?${queryString}`

    const body = await cachedGet<StatisticsResult<EvidenceCompositionItem[]>>(url)
    return { data: body.data, meta: body.meta }
  },

  /**
   * Get summary statistics for dashboard overview
   */
  async getSummaryStatistics(): Promise<StatisticsResult<SummaryStatisticsData>> {
    const response =
      await apiClient.get<StatisticsResult<SummaryStatisticsData>>('/api/statistics/summary')
    return {
      data: response.data.data,
      meta: response.data.meta
    }
  }
}
