/**
 * Gene Annotations Management API endpoints
 */

import apiClient from '@/api/client'

/**
 * Get annotation sources
 * @param {boolean} [activeOnly=true] - Filter for active sources only
 * @returns {Promise} List of annotation sources
 */
export const getAnnotationSources = (activeOnly = true) => {
  const queryParams = new URLSearchParams()
  queryParams.append('active_only', activeOnly)
  return apiClient.get(`/api/annotations/sources?${queryParams.toString()}`)
}

/**
 * Get annotation statistics
 * @returns {Promise} Annotation statistics
 */
export const getAnnotationStatistics = () => apiClient.get('/api/annotations/statistics')

/**
 * Get annotations for a specific gene
 * @param {number} geneId - Gene ID
 * @param {string} [source] - Filter by annotation source
 * @returns {Promise} Gene annotations
 */
export const getGeneAnnotations = (geneId, source = null) => {
  const queryParams = new URLSearchParams()
  if (source) queryParams.append('source', source)
  const query = queryParams.toString()
  return apiClient.get(`/api/annotations/genes/${geneId}/annotations${query ? `?${query}` : ''}`)
}

/**
 * Get annotation summary for a specific gene
 * @param {number} geneId - Gene ID
 * @returns {Promise} Gene annotation summary
 */
export const getGeneAnnotationSummary = geneId =>
  apiClient.get(`/api/annotations/genes/${geneId}/annotations/summary`)

/**
 * Update annotations for a specific gene
 * @param {number} geneId - Gene ID
 * @param {string[]} [sources] - List of sources to update
 * @returns {Promise} Update result
 */
export const updateGeneAnnotations = (
  geneId,
  sources = ['hgnc', 'gnomad', 'gtex', 'hpo', 'clinvar', 'string_ppi']
) => {
  const queryParams = new URLSearchParams()
  sources.forEach(source => queryParams.append('sources', source))
  return apiClient.post(
    `/api/annotations/genes/${geneId}/annotations/update?${queryParams.toString()}`
  )
}

/**
 * Refresh materialized view
 * @returns {Promise} Refresh result
 */
export const refreshMaterializedView = () => apiClient.post('/api/annotations/refresh-view')

/**
 * Get pipeline status
 * @returns {Promise} Pipeline status
 */
export const getPipelineStatus = () => apiClient.get('/api/annotations/pipeline/status')

/**
 * Trigger pipeline update
 * @param {Object} params - Update parameters
 * @param {string} [params.strategy='incremental'] - Update strategy
 * @param {string[]} [params.sources] - Specific sources to update
 * @param {number[]} [params.geneIds] - Specific gene IDs to update
 * @param {boolean} [params.force=false] - Force update regardless of TTL
 * @returns {Promise} Pipeline update result
 */
export const triggerPipelineUpdate = (params = {}) => {
  const queryParams = new URLSearchParams()

  if (params.strategy) queryParams.append('strategy', params.strategy)
  if (params.sources) params.sources.forEach(source => queryParams.append('sources', source))
  if (params.geneIds) params.geneIds.forEach(id => queryParams.append('gene_ids', id))
  if (params.force !== undefined) queryParams.append('force', params.force)

  return apiClient.post(`/api/annotations/pipeline/update?${queryParams.toString()}`)
}

/**
 * Validate annotations
 * @param {string} [source] - Specific source to validate
 * @returns {Promise} Validation results
 */
export const validateAnnotations = (source = null) => {
  const queryParams = new URLSearchParams()
  if (source) queryParams.append('source', source)
  const query = queryParams.toString()
  return apiClient.post(`/api/annotations/pipeline/validate${query ? `?${query}` : ''}`)
}

/**
 * Get scheduled jobs
 * @returns {Promise} List of scheduled jobs
 */
export const getScheduledJobs = () => apiClient.get('/api/annotations/scheduler/jobs')

/**
 * Trigger scheduled job
 * @param {string} jobId - Job ID to trigger
 * @returns {Promise} Trigger result
 */
export const triggerScheduledJob = jobId =>
  apiClient.post(`/api/annotations/scheduler/trigger/${jobId}`)

/**
 * Get batch annotations for multiple genes
 * @param {number[]} geneIds - List of gene IDs
 * @param {string[]} [sources] - Optional source filter
 * @returns {Promise} Batch annotation results
 */
export const getBatchAnnotations = (geneIds, sources = null) => {
  const queryParams = new URLSearchParams()
  if (sources) sources.forEach(source => queryParams.append('sources', source))

  return apiClient.post(`/api/annotations/batch?${queryParams.toString()}`, {
    gene_ids: geneIds
  })
}

export default {
  getAnnotationSources,
  getAnnotationStatistics,
  getGeneAnnotations,
  getGeneAnnotationSummary,
  updateGeneAnnotations,
  refreshMaterializedView,
  getPipelineStatus,
  triggerPipelineUpdate,
  validateAnnotations,
  getScheduledJobs,
  triggerScheduledJob,
  getBatchAnnotations
}
