/**
 * Gene Annotations Management API endpoints
 * Admin module: functions return Promise<AxiosResponse<T>> (callers use .data)
 */

import apiClient from '@/api/client'
import type { AxiosResponse } from 'axios'

/** Pipeline update parameters */
export interface PipelineUpdateParams {
  strategy?: string
  sources?: string[]
  geneIds?: number[]
  force?: boolean
}

/**
 * Get annotation sources
 */
export const getAnnotationSources = (activeOnly = true): Promise<AxiosResponse<unknown>> => {
  const queryParams = new URLSearchParams()
  queryParams.append('active_only', String(activeOnly))
  return apiClient.get(`/api/annotations/sources?${queryParams.toString()}`)
}

/**
 * Get annotation statistics
 */
export const getAnnotationStatistics = (): Promise<AxiosResponse<unknown>> =>
  apiClient.get('/api/annotations/statistics')

/**
 * Get annotations for a specific gene
 */
export const getGeneAnnotations = (
  geneId: number,
  source: string | null = null
): Promise<AxiosResponse<unknown>> => {
  const queryParams = new URLSearchParams()
  if (source) queryParams.append('source', source)
  const query = queryParams.toString()
  return apiClient.get(`/api/annotations/genes/${geneId}/annotations${query ? `?${query}` : ''}`)
}

/**
 * Get annotation summary for a specific gene
 */
export const getGeneAnnotationSummary = (geneId: number): Promise<AxiosResponse<unknown>> =>
  apiClient.get(`/api/annotations/genes/${geneId}/annotations/summary`)

/**
 * Update annotations for a specific gene
 */
export const updateGeneAnnotations = (
  geneId: number,
  sources: string[] = ['hgnc', 'gnomad', 'gtex', 'hpo', 'clinvar', 'string_ppi']
): Promise<AxiosResponse<unknown>> => {
  const queryParams = new URLSearchParams()
  sources.forEach(source => queryParams.append('sources', source))
  return apiClient.post(
    `/api/annotations/genes/${geneId}/annotations/update?${queryParams.toString()}`
  )
}

/**
 * Refresh materialized view
 */
export const refreshMaterializedView = (): Promise<AxiosResponse<unknown>> =>
  apiClient.post('/api/annotations/refresh-view')

/**
 * Get pipeline status
 */
export const getPipelineStatus = (): Promise<AxiosResponse<unknown>> =>
  apiClient.get('/api/annotations/pipeline/status')

/**
 * Trigger pipeline update
 */
export const triggerPipelineUpdate = (
  params: PipelineUpdateParams = {}
): Promise<AxiosResponse<unknown>> => {
  const queryParams = new URLSearchParams()

  if (params.strategy) queryParams.append('strategy', params.strategy)
  if (params.sources) params.sources.forEach(source => queryParams.append('sources', source))
  if (params.geneIds) params.geneIds.forEach(id => queryParams.append('gene_ids', String(id)))
  if (params.force !== undefined) queryParams.append('force', String(params.force))

  return apiClient.post(`/api/annotations/pipeline/update?${queryParams.toString()}`)
}

/**
 * Validate annotations
 */
export const validateAnnotations = (
  source: string | null = null
): Promise<AxiosResponse<unknown>> => {
  const queryParams = new URLSearchParams()
  if (source) queryParams.append('source', source)
  const query = queryParams.toString()
  return apiClient.post(`/api/annotations/pipeline/validate${query ? `?${query}` : ''}`)
}

/**
 * Get scheduled jobs
 */
export const getScheduledJobs = (): Promise<AxiosResponse<unknown>> =>
  apiClient.get('/api/annotations/scheduler/jobs')

/**
 * Trigger scheduled job
 */
export const triggerScheduledJob = (jobId: string): Promise<AxiosResponse<unknown>> =>
  apiClient.post(`/api/annotations/scheduler/trigger/${jobId}`)

/**
 * Get batch annotations for multiple genes
 */
export const getBatchAnnotations = (
  geneIds: number[],
  sources: string[] | null = null
): Promise<AxiosResponse<unknown>> => {
  const queryParams = new URLSearchParams()
  if (sources) sources.forEach(source => queryParams.append('sources', source))

  return apiClient.post(`/api/annotations/batch?${queryParams.toString()}`, {
    gene_ids: geneIds
  })
}

/**
 * Pause running pipeline
 */
export const pausePipeline = (): Promise<AxiosResponse<unknown>> =>
  apiClient.post('/api/progress/pause/annotation_pipeline')

/**
 * Resume paused pipeline
 */
export const resumePipeline = (): Promise<AxiosResponse<unknown>> =>
  apiClient.post('/api/progress/resume/annotation_pipeline')

/**
 * Update only failed genes
 */
export const updateFailedGenes = (
  sources: string[] | null = null
): Promise<AxiosResponse<unknown>> => {
  const queryParams = new URLSearchParams()
  if (sources) sources.forEach(source => queryParams.append('sources', source))
  const query = queryParams.toString()
  return apiClient.post(`/api/annotations/pipeline/update-failed${query ? `?${query}` : ''}`)
}

/**
 * Update only new genes without annotations
 */
export const updateNewGenes = (daysBack = 7): Promise<AxiosResponse<unknown>> => {
  const queryParams = new URLSearchParams()
  queryParams.append('days_back', String(daysBack))
  return apiClient.post(`/api/annotations/pipeline/update-new?${queryParams.toString()}`)
}

/**
 * Update missing annotations for specific source
 */
export const updateMissingForSource = (sourceName: string): Promise<AxiosResponse<unknown>> =>
  apiClient.post(`/api/annotations/pipeline/update-missing/${sourceName}`)

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
  getBatchAnnotations,
  pausePipeline,
  resumePipeline,
  updateFailedGenes,
  updateNewGenes,
  updateMissingForSource
}
