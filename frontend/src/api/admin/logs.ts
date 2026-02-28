/**
 * System Logs API endpoints
 * Admin module: most functions return Promise<AxiosResponse<T>> (callers use .data)
 * Exception: exportLogs returns response.data directly
 */

import apiClient from '@/api/client'
import type { AxiosResponse } from 'axios'

/** Parameters for log queries */
export interface LogQueryParams {
  level?: string
  source?: string
  request_id?: string
  start_time?: string
  end_time?: string
  limit?: number
  offset?: number
  sort_by?: string
  sort_order?: string
}

/**
 * Query logs with filters
 */
export const queryLogs = (params: LogQueryParams = {}): Promise<AxiosResponse<unknown>> => {
  const queryParams = new URLSearchParams()

  if (params.level) queryParams.append('level', params.level)
  if (params.source) queryParams.append('source', params.source)
  if (params.request_id) queryParams.append('request_id', params.request_id)
  if (params.start_time) queryParams.append('start_time', params.start_time)
  if (params.end_time) queryParams.append('end_time', params.end_time)
  if (params.limit) queryParams.append('limit', String(params.limit))
  if (params.offset) queryParams.append('offset', String(params.offset))
  if (params.sort_by) queryParams.append('sort_by', params.sort_by)
  if (params.sort_order) queryParams.append('sort_order', params.sort_order)

  return apiClient.get(`/api/admin/logs/?${queryParams.toString()}`)
}

/**
 * Get log statistics
 */
export const getLogStatistics = (hours = 24): Promise<AxiosResponse<unknown>> =>
  apiClient.get(`/api/admin/logs/statistics?hours=${hours}`)

/**
 * Clean up old logs
 */
export const cleanupLogs = (days = 30): Promise<AxiosResponse<unknown>> =>
  apiClient.delete(`/api/admin/logs/cleanup?days=${days}`)

/**
 * Export logs to file
 * Note: returns response.data directly (exception to admin module pattern)
 */
export const exportLogs = async (params: LogQueryParams = {}): Promise<unknown> => {
  const response = await queryLogs({ ...params, limit: 10000 })
  return response.data
}

export default {
  queryLogs,
  getLogStatistics,
  cleanupLogs,
  exportLogs
}
