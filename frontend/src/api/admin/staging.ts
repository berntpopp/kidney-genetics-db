/**
 * Gene Staging API endpoints
 * Admin module: functions return Promise<AxiosResponse<T>> (callers use .data)
 */

import apiClient from '@/api/client'
import type { AxiosResponse } from 'axios'

/** Parameters for getPendingStaging */
export interface StagingQueryParams {
  limit?: number
  offset?: number
  requires_expert_review?: boolean
}

/** Parameters for getNormalizationLogs */
export interface NormalizationLogParams {
  limit?: number
  offset?: number
  source_name?: string
  success?: boolean
}

/** Approval data for approveStaging */
export interface StagingApprovalData {
  approved_symbol: string
  hgnc_id?: string
  [key: string]: unknown
}

/** Rejection data for rejectStaging */
export interface StagingRejectionData {
  reason?: string
  [key: string]: unknown
}

/**
 * Get pending staging records
 */
export const getPendingStaging = (
  params: StagingQueryParams = {}
): Promise<AxiosResponse<unknown>> => {
  const queryParams = new URLSearchParams()

  if (params.limit) queryParams.append('limit', String(params.limit))
  if (params.offset) queryParams.append('offset', String(params.offset))
  if (params.requires_expert_review !== undefined) {
    queryParams.append('requires_expert_review', String(params.requires_expert_review))
  }

  return apiClient.get(`/api/staging/staging/pending?${queryParams.toString()}`)
}

/**
 * Approve staging record
 */
export const approveStaging = (
  id: number,
  data: StagingApprovalData
): Promise<AxiosResponse<unknown>> =>
  apiClient.post(`/api/staging/staging/${id}/approve`, data)

/**
 * Reject staging record
 */
export const rejectStaging = (
  id: number,
  data: StagingRejectionData = {}
): Promise<AxiosResponse<unknown>> => apiClient.post(`/api/staging/staging/${id}/reject`, data)

/**
 * Get staging statistics
 */
export const getStagingStats = (): Promise<AxiosResponse<unknown>> =>
  apiClient.get('/api/staging/staging/stats')

/**
 * Get normalization statistics
 */
export const getNormalizationStats = (): Promise<AxiosResponse<unknown>> =>
  apiClient.get('/api/staging/normalization/stats')

/**
 * Get normalization logs
 */
export const getNormalizationLogs = (
  params: NormalizationLogParams = {}
): Promise<AxiosResponse<unknown>> => {
  const queryParams = new URLSearchParams()

  if (params.limit) queryParams.append('limit', String(params.limit))
  if (params.offset) queryParams.append('offset', String(params.offset))
  if (params.source_name) queryParams.append('source_name', params.source_name)
  if (params.success !== undefined) queryParams.append('success', String(params.success))

  return apiClient.get(`/api/staging/normalization/logs?${queryParams.toString()}`)
}

/**
 * Test normalization for a gene symbol
 */
export const testNormalization = (
  geneText: string,
  sourceName = 'Manual Test'
): Promise<AxiosResponse<unknown>> => {
  const queryParams = new URLSearchParams()
  queryParams.append('gene_text', geneText)
  queryParams.append('source_name', sourceName)
  return apiClient.post(`/api/staging/normalization/test?${queryParams.toString()}`)
}

/**
 * Bulk approve staging records
 */
export const bulkApprove = (
  ids: number[],
  data: Record<string, unknown>
): Promise<AxiosResponse<unknown>> =>
  apiClient.post('/api/staging/staging/bulk-approve', { ids, ...data })

/**
 * Bulk reject staging records
 */
export const bulkReject = (
  ids: number[],
  data: StagingRejectionData = {}
): Promise<AxiosResponse<unknown>> =>
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
