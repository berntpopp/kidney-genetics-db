/**
 * Data Pipeline API endpoints
 * Admin module: functions return Promise<AxiosResponse<T>> (callers use .data)
 */

import apiClient from '@/api/client'
import type { AxiosResponse } from 'axios'

/**
 * Get status of all data sources
 */
export const getAllStatus = (): Promise<AxiosResponse<unknown>> =>
  apiClient.get('/api/progress/status')

/**
 * Get status of specific data source
 */
export const getSourceStatus = (sourceName: string): Promise<AxiosResponse<unknown>> =>
  apiClient.get(`/api/progress/status/${sourceName}`)

/**
 * Trigger update for a data source
 */
export const triggerUpdate = (sourceName: string): Promise<AxiosResponse<unknown>> =>
  apiClient.post(`/api/progress/trigger/${sourceName}`)

/**
 * Pause a running data source
 */
export const pauseSource = (sourceName: string): Promise<AxiosResponse<unknown>> =>
  apiClient.post(`/api/progress/pause/${sourceName}`)

/**
 * Resume a paused data source
 */
export const resumeSource = (sourceName: string): Promise<AxiosResponse<unknown>> =>
  apiClient.post(`/api/progress/resume/${sourceName}`)

/**
 * Get dashboard data with summary statistics
 */
export const getDashboardData = (): Promise<AxiosResponse<unknown>> =>
  apiClient.get('/api/progress/dashboard')

/**
 * Get annotation sources
 */
export const getAnnotationSources = (): Promise<AxiosResponse<unknown>> =>
  apiClient.get('/api/annotations/sources')

/**
 * Get annotation statistics
 */
export const getAnnotationStatistics = (): Promise<AxiosResponse<unknown>> =>
  apiClient.get('/api/annotations/statistics')

/**
 * Trigger pipeline update
 */
export const triggerPipelineUpdate = (): Promise<AxiosResponse<unknown>> =>
  apiClient.post('/api/annotations/pipeline/update')

/**
 * Get pipeline status
 */
export const getPipelineStatus = (): Promise<AxiosResponse<unknown>> =>
  apiClient.get('/api/annotations/pipeline/status')

/**
 * Validate annotations
 */
export const validateAnnotations = (): Promise<AxiosResponse<unknown>> =>
  apiClient.post('/api/annotations/pipeline/validate')

/**
 * Get scheduled jobs
 */
export const getScheduledJobs = (): Promise<AxiosResponse<unknown>> =>
  apiClient.get('/api/annotations/scheduler/jobs')

/**
 * Trigger specific job
 */
export const triggerJob = (jobId: string): Promise<AxiosResponse<unknown>> =>
  apiClient.post(`/api/annotations/scheduler/trigger/${jobId}`)

/**
 * Refresh materialized view
 */
export const refreshView = (): Promise<AxiosResponse<unknown>> =>
  apiClient.post('/api/annotations/refresh-view')

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
