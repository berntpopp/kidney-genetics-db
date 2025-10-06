/**
 * Statistics API endpoints for data visualization
 */

import apiClient from './client'

export const statisticsApi = {
  /**
   * Get gene intersections between data sources for UpSet plot
   * @param {Array<string>} sources - Optional array of source names to filter by
   * @param {Array<string>} tiers - Optional array of evidence tiers for filtering
   * @param {boolean} hideZeroScores - Hide genes with percentage_score = 0 (default: true)
   * @returns {Promise} UpSet plot data with sets and intersections
   */
  async getSourceOverlaps(sources = null, tiers = null, hideZeroScores = true) {
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

    const response = await apiClient.get(url)
    return {
      data: response.data.data,
      meta: response.data.meta
    }
  },

  /**
   * Get source count distributions for bar charts
   * @param {Array<string>} tiers - Optional array of evidence tiers for filtering
   * @param {boolean} hideZeroScores - Hide genes with percentage_score = 0 (default: true)
   * @returns {Promise} Distribution data for each source
   */
  async getSourceDistributions(tiers = null, hideZeroScores = true) {
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

    const response = await apiClient.get(url)
    return {
      data: response.data.data,
      meta: response.data.meta
    }
  },

  /**
   * Get evidence quality and composition analysis
   * @param {Array<string>} tiers - Optional array of evidence tiers for filtering
   * @param {boolean} hideZeroScores - Hide genes with percentage_score = 0 (default: true)
   * @returns {Promise} Evidence composition data
   */
  async getEvidenceComposition(tiers = null, hideZeroScores = true) {
    const params = new URLSearchParams()

    // Add tier filter parameter if provided (comma-separated for multi-select with OR logic)
    if (tiers && tiers.length > 0) {
      params.append('filter[tier]', tiers.join(','))
    }

    // Always pass hide_zero_scores parameter (matches /genes endpoint behavior)
    params.append('filter[hide_zero_scores]', hideZeroScores.toString())

    const queryString = params.toString()
    const url = `/api/statistics/evidence-composition?${queryString}`

    const response = await apiClient.get(url)
    return {
      data: response.data.data,
      meta: response.data.meta
    }
  },

  /**
   * Get summary statistics for dashboard overview
   * @returns {Promise} Summary statistics
   */
  async getSummaryStatistics() {
    const response = await apiClient.get('/api/statistics/summary')
    return {
      data: response.data.data,
      meta: response.data.meta
    }
  }
}
