/**
 * Hybrid Source Ingestion API
 * Handles DiagnosticPanels and Literature file uploads
 * Admin module: functions return Promise<AxiosResponse<T>> (callers use .data)
 */

import apiClient from '@/api/client'
import type { AxiosResponse } from 'axios'

/**
 * Get list of available hybrid sources
 */
export const getHybridSources = (): Promise<AxiosResponse<unknown>> =>
  apiClient.get('/api/ingestion/')

/**
 * Get status and statistics for a hybrid source
 */
export const getSourceStatus = (sourceName: string): Promise<AxiosResponse<unknown>> =>
  apiClient.get(`/api/ingestion/${sourceName}/status`)

/**
 * Upload file for hybrid source
 */
export const uploadSourceFile = async (
  sourceName: string,
  file: File,
  providerName: string | null = null,
  mode = 'merge'
): Promise<AxiosResponse<unknown>> => {
  const formData = new FormData()
  formData.append('file', file)
  formData.append('mode', mode)
  if (providerName) {
    formData.append('provider_name', providerName)
  }

  return apiClient.post(`/api/ingestion/${sourceName}/upload`, formData, {
    headers: {
      'Content-Type': 'multipart/form-data'
    }
  })
}

/**
 * Delete evidence by provider/publication identifier
 */
export const deleteByIdentifier = (
  sourceName: string,
  identifier: string
): Promise<AxiosResponse<unknown>> =>
  apiClient.delete(`/api/ingestion/${sourceName}/identifiers/${identifier}`)

/**
 * Soft delete an upload record
 */
export const softDeleteUpload = (
  sourceName: string,
  uploadId: number
): Promise<AxiosResponse<unknown>> =>
  apiClient.delete(`/api/ingestion/${sourceName}/uploads/${uploadId}`)

/**
 * List upload history for a source
 */
export const listUploads = (
  sourceName: string,
  limit = 50,
  offset = 0
): Promise<AxiosResponse<unknown>> =>
  apiClient.get(`/api/ingestion/${sourceName}/uploads`, {
    params: { limit, offset }
  })

/**
 * Get audit trail for a source
 */
export const getAuditTrail = (
  sourceName: string,
  limit = 50,
  offset = 0
): Promise<AxiosResponse<unknown>> =>
  apiClient.get(`/api/ingestion/${sourceName}/audit`, {
    params: { limit, offset }
  })

/**
 * List all providers (DiagnosticPanels) or PMIDs (Literature)
 */
export const listIdentifiers = (sourceName: string): Promise<AxiosResponse<unknown>> =>
  apiClient.get(`/api/ingestion/${sourceName}/identifiers`)

export default {
  getHybridSources,
  getSourceStatus,
  uploadSourceFile,
  deleteByIdentifier,
  softDeleteUpload,
  listUploads,
  getAuditTrail,
  listIdentifiers
}
