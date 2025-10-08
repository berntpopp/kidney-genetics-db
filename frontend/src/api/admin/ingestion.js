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
 * @returns {Promise<Object>} Upload result with statistics
 */
export const uploadSourceFile = async (sourceName, file, providerName = null) => {
  const formData = new FormData()
  formData.append('file', file)
  if (providerName) {
    formData.append('provider_name', providerName)
  }

  return apiClient.post(`/api/ingestion/${sourceName}/upload`, formData, {
    headers: {
      'Content-Type': 'multipart/form-data'
    }
  })
}

export default {
  getHybridSources,
  getSourceStatus,
  uploadSourceFile
}
