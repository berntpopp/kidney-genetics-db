/**
 * Data Pipeline API endpoints
 */

import apiClient from '@/api/client'

/**
 * Get status of all data sources
 * @returns {Promise} List of source statuses
 */
export const getAllStatus = () => apiClient.get('/api/progress/status')

/**
 * Get status of specific data source
 * @param {string} sourceName - Name of the data source
 * @returns {Promise} Source status
 */
export const getSourceStatus = sourceName => apiClient.get(`/api/progress/status/${sourceName}`)

/**
 * Trigger update for a data source
 * @param {string} sourceName - Name of the data source
 * @returns {Promise} Trigger result
 */
export const triggerUpdate = sourceName => apiClient.post(`/api/progress/trigger/${sourceName}`)

/**
 * Pause a running data source
 * @param {string} sourceName - Name of the data source
 * @returns {Promise} Pause result
 */
export const pauseSource = sourceName => apiClient.post(`/api/progress/pause/${sourceName}`)

/**
 * Resume a paused data source
 * @param {string} sourceName - Name of the data source
 * @returns {Promise} Resume result
 */
export const resumeSource = sourceName => apiClient.post(`/api/progress/resume/${sourceName}`)

/**
 * Get dashboard data with summary statistics
 * @returns {Promise} Dashboard data
 */
export const getDashboardData = () => apiClient.get('/api/progress/dashboard')

/**
 * Get annotation sources
 * @returns {Promise} List of annotation sources
 */
export const getAnnotationSources = () => apiClient.get('/api/annotations/sources')

/**
 * Get annotation statistics
 * @returns {Promise} Annotation statistics
 */
export const getAnnotationStatistics = () => apiClient.get('/api/annotations/statistics')

/**
 * Trigger pipeline update
 * @returns {Promise} Update result
 */
export const triggerPipelineUpdate = () => apiClient.post('/api/annotations/pipeline/update')

/**
 * Get pipeline status
 * @returns {Promise} Pipeline status
 */
export const getPipelineStatus = () => apiClient.get('/api/annotations/pipeline/status')

/**
 * Validate annotations
 * @returns {Promise} Validation result
 */
export const validateAnnotations = () => apiClient.post('/api/annotations/pipeline/validate')

/**
 * Get scheduled jobs
 * @returns {Promise} List of scheduled jobs
 */
export const getScheduledJobs = () => apiClient.get('/api/annotations/scheduler/jobs')

/**
 * Trigger specific job
 * @param {string} jobId - Job ID
 * @returns {Promise} Trigger result
 */
export const triggerJob = jobId => apiClient.post(`/api/annotations/scheduler/trigger/${jobId}`)

/**
 * Refresh materialized view
 * @returns {Promise} Refresh result
 */
export const refreshView = () => apiClient.post('/api/annotations/refresh-view')

export default {
  getAllStatus,
  getSourceStatus,
  triggerUpdate,
  pauseSource,
  resumeSource,
  getDashboardData,
  getAnnotationSources,
  getAnnotationStatistics,
  triggerPipelineUpdate,
  getPipelineStatus,
  validateAnnotations,
  getScheduledJobs,
  triggerJob,
  refreshView
}
