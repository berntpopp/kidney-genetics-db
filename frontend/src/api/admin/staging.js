/**
 * Gene Staging API endpoints
 */

import apiClient from '@/api/client'

/**
 * Get pending staging records
 * @param {Object} params - Query parameters
 * @param {number} [params.limit=100] - Maximum results
 * @param {number} [params.offset=0] - Result offset
 * @param {boolean} [params.requires_expert_review] - Filter by expert review requirement
 * @returns {Promise} Pending staging records
 */
export const getPendingStaging = (params = {}) => {
  const queryParams = new URLSearchParams()

  if (params.limit) queryParams.append('limit', params.limit)
  if (params.offset) queryParams.append('offset', params.offset)
  if (params.requires_expert_review !== undefined) {
    queryParams.append('requires_expert_review', params.requires_expert_review)
  }

  return apiClient.get(`/api/staging/staging/pending?${queryParams.toString()}`)
}

/**
 * Approve staging record
 * @param {number} id - Staging record ID
 * @param {Object} data - Approval data
 * @param {string} data.approved_symbol - Approved gene symbol
 * @param {string} [data.hgnc_id] - HGNC ID
 * @returns {Promise} Approval result
 */
export const approveStaging = (id, data) =>
  apiClient.post(`/api/staging/staging/${id}/approve`, data)

/**
 * Reject staging record
 * @param {number} id - Staging record ID
 * @param {Object} data - Rejection data
 * @param {string} [data.reason] - Rejection reason
 * @returns {Promise} Rejection result
 */
export const rejectStaging = (id, data = {}) =>
  apiClient.post(`/api/staging/staging/${id}/reject`, data)

/**
 * Get staging statistics
 * @returns {Promise} Staging statistics
 */
export const getStagingStats = () => apiClient.get('/api/staging/staging/stats')

/**
 * Get normalization statistics
 * @returns {Promise} Normalization statistics
 */
export const getNormalizationStats = () => apiClient.get('/api/staging/normalization/stats')

/**
 * Get normalization logs
 * @param {Object} params - Query parameters
 * @param {number} [params.limit=100] - Maximum results
 * @param {number} [params.offset=0] - Result offset
 * @param {string} [params.source_name] - Filter by source
 * @param {boolean} [params.success] - Filter by success status
 * @returns {Promise} Normalization logs
 */
export const getNormalizationLogs = (params = {}) => {
  const queryParams = new URLSearchParams()

  if (params.limit) queryParams.append('limit', params.limit)
  if (params.offset) queryParams.append('offset', params.offset)
  if (params.source_name) queryParams.append('source_name', params.source_name)
  if (params.success !== undefined) queryParams.append('success', params.success)

  return apiClient.get(`/api/staging/normalization/logs?${queryParams.toString()}`)
}

/**
 * Test normalization for a gene symbol
 * @param {string} symbol - Gene symbol to test
 * @returns {Promise} Normalization test result
 */
export const testNormalization = symbol =>
  apiClient.post('/api/staging/normalization/test', { gene_symbol: symbol })

/**
 * Bulk approve staging records
 * @param {Array<number>} ids - Array of staging record IDs
 * @param {Object} data - Approval data
 * @returns {Promise} Bulk approval result
 */
export const bulkApprove = (ids, data) =>
  apiClient.post('/api/staging/staging/bulk-approve', { ids, ...data })

/**
 * Bulk reject staging records
 * @param {Array<number>} ids - Array of staging record IDs
 * @param {Object} data - Rejection data
 * @returns {Promise} Bulk rejection result
 */
export const bulkReject = (ids, data = {}) =>
  apiClient.post('/api/staging/staging/bulk-reject', { ids, ...data })

export default {
  getPendingStaging,
  approveStaging,
  rejectStaging,
  getStagingStats,
  getNormalizationStats,
  getNormalizationLogs,
  testNormalization,
  bulkApprove,
  bulkReject
}
