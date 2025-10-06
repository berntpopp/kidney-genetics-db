/**
 * Statistics API endpoints for data visualization
 */

import apiClient from './client'

export const statisticsApi = {
  /**
   * Get gene intersections between data sources for UpSet plot
   * @param {Array<string>} sources - Optional array of source names to filter by
   * @param {string} minTier - Optional minimum evidence tier for filtering
   * @returns {Promise} UpSet plot data with sets and intersections
   */
  async getSourceOverlaps(sources = null, minTier = null) {
    const params = new URLSearchParams()

    // Add sources as query parameters if provided
    if (sources && sources.length > 0) {
      sources.forEach(source => params.append('sources', source))
    }

    // Add min_tier parameter if provided
    if (minTier) {
      params.append('min_tier', minTier)
    }

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
   * @param {string} minTier - Optional minimum evidence tier for filtering
   * @returns {Promise} Distribution data for each source
   */
  async getSourceDistributions(minTier = null) {
    const params = new URLSearchParams()

    // Add min_tier parameter if provided
    if (minTier) {
      params.append('min_tier', minTier)
    }

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
   * @param {string} minTier - Optional minimum evidence tier for filtering
   * @returns {Promise} Evidence composition data
   */
  async getEvidenceComposition(minTier = null) {
    const params = new URLSearchParams()

    // Add min_tier parameter if provided
    if (minTier) {
      params.append('min_tier', minTier)
    }

    const queryString = params.toString()
    const url = queryString
      ? `/api/statistics/evidence-composition?${queryString}`
      : '/api/statistics/evidence-composition'

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
