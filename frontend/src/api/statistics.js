/**
 * Statistics API endpoints for data visualization
 */

import apiClient from './client'

export const statisticsApi = {
  /**
   * Get gene intersections between data sources for UpSet plot
   * @returns {Promise} UpSet plot data with sets and intersections
   */
  async getSourceOverlaps() {
    const response = await apiClient.get('/api/statistics/source-overlaps')
    return {
      data: response.data.data,
      meta: response.data.meta
    }
  },

  /**
   * Get source count distributions for bar charts
   * @returns {Promise} Distribution data for each source
   */
  async getSourceDistributions() {
    const response = await apiClient.get('/api/statistics/source-distributions')
    return {
      data: response.data.data,
      meta: response.data.meta
    }
  },

  /**
   * Get evidence quality and composition analysis
   * @returns {Promise} Evidence composition data
   */
  async getEvidenceComposition() {
    const response = await apiClient.get('/api/statistics/evidence-composition')
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
