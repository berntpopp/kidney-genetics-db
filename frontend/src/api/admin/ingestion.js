/**
 * Hybrid Source Ingestion API
 * Handles DiagnosticPanels and Literature file uploads
 */

/* global FormData */

import apiClient from '@/api/client'

/**
 * Get list of available hybrid sources
 * @returns {Promise<Object>} List of sources with capabilities
 */
export const getHybridSources = () => apiClient.get('/api/ingestion/')

/**
 * Get status and statistics for a hybrid source
 * @param {string} sourceName - DiagnosticPanels or Literature
 * @returns {Promise<Object>} Source status and stats
 */
export const getSourceStatus = sourceName => apiClient.get(`/api/ingestion/${sourceName}/status`)

/**
 * Upload file for hybrid source
 * @param {string} sourceName - DiagnosticPanels or Literature
 * @param {File} file - File to upload
 * @param {string} providerName - Optional provider identifier
 * @param {string} mode - Upload mode: 'merge' (default) or 'replace'
 * @returns {Promise<Object>} Upload result with statistics
 */
export const uploadSourceFile = async (sourceName, file, providerName = null, mode = 'merge') => {
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
 * @param {string} sourceName - DiagnosticPanels or Literature
 * @param {string} identifier - Provider name (DiagnosticPanels) or PMID (Literature)
 * @returns {Promise<Object>} Deletion statistics
 */
export const deleteByIdentifier = (sourceName, identifier) =>
  apiClient.delete(`/api/ingestion/${sourceName}/identifiers/${identifier}`)

/**
 * Soft delete an upload record
 * @param {string} sourceName - DiagnosticPanels or Literature
 * @param {number} uploadId - ID of the upload to delete
 * @returns {Promise<Object>} Updated upload record
 */
export const softDeleteUpload = (sourceName, uploadId) =>
  apiClient.delete(`/api/ingestion/${sourceName}/uploads/${uploadId}`)

/**
 * List upload history for a source
 * @param {string} sourceName - DiagnosticPanels or Literature
 * @param {number} limit - Maximum number of records (default: 50)
 * @param {number} offset - Number of records to skip (default: 0)
 * @returns {Promise<Object>} List of upload records
 */
export const listUploads = (sourceName, limit = 50, offset = 0) =>
  apiClient.get(`/api/ingestion/${sourceName}/uploads`, {
    params: { limit, offset }
  })

/**
 * Get audit trail for a source
 * @param {string} sourceName - DiagnosticPanels or Literature
 * @param {number} limit - Maximum number of records (default: 50)
 * @param {number} offset - Number of records to skip (default: 0)
 * @returns {Promise<Object>} List of audit records
 */
export const getAuditTrail = (sourceName, limit = 50, offset = 0) =>
  apiClient.get(`/api/ingestion/${sourceName}/audit`, {
    params: { limit, offset }
  })

/**
 * List all providers (DiagnosticPanels) or PMIDs (Literature)
 * @param {string} sourceName - DiagnosticPanels or Literature
 * @returns {Promise<Object>} List of identifiers with gene counts
 */
export const listIdentifiers = sourceName =>
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
