/**
 * System Logs API endpoints
 */

import apiClient from '@/api/client'

/**
 * Query logs with filters
 * @param {Object} params - Query parameters
 * @param {string} [params.level] - Log level filter
 * @param {string} [params.source] - Source module filter
 * @param {string} [params.request_id] - Request ID filter
 * @param {string} [params.start_time] - Start time filter
 * @param {string} [params.end_time] - End time filter
 * @param {number} [params.limit=100] - Maximum results
 * @param {number} [params.offset=0] - Result offset
 * @returns {Promise} Log entries with pagination
 */
export const queryLogs = (params = {}) => {
  const queryParams = new URLSearchParams()

  if (params.level) queryParams.append('level', params.level)
  if (params.source) queryParams.append('source', params.source)
  if (params.request_id) queryParams.append('request_id', params.request_id)
  if (params.start_time) queryParams.append('start_time', params.start_time)
  if (params.end_time) queryParams.append('end_time', params.end_time)
  if (params.limit) queryParams.append('limit', params.limit)
  if (params.offset) queryParams.append('offset', params.offset)

  return apiClient.get(`/api/admin/logs/?${queryParams.toString()}`)
}

/**
 * Get log statistics
 * @param {number} hours - Hours to analyze (default 24)
 * @returns {Promise} Log statistics
 */
export const getLogStatistics = (hours = 24) =>
  apiClient.get(`/api/admin/logs/statistics?hours=${hours}`)

/**
 * Clean up old logs
 * @param {number} days - Delete logs older than this many days
 * @returns {Promise} Cleanup result
 */
export const cleanupLogs = (days = 30) => apiClient.delete(`/api/admin/logs/cleanup?days=${days}`)

/**
 * Export logs to file
 * @param {Object} params - Export parameters
 * @returns {Promise} Export result
 */
export const exportLogs = async (params = {}) => {
  const response = await queryLogs({ ...params, limit: 10000 })
  return response.data
}

export default {
  queryLogs,
  getLogStatistics,
  cleanupLogs,
  exportLogs
}
