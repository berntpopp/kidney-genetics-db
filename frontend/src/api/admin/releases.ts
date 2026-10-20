/**
 * Data Release API endpoints
 * Admin module: functions return Promise<AxiosResponse<T>> (callers use .data)
 */

import apiClient from '@/api/client'
import type { AxiosResponse } from 'axios'

/** List releases */
export const listReleases = (): Promise<AxiosResponse<unknown>> => apiClient.get('/api/releases/')

/** Create a draft release */
export const createRelease = (
  version: string,
  releaseNotes: string
): Promise<AxiosResponse<unknown>> =>
  apiClient.post('/api/releases/', null, {
    params: { version, release_notes: releaseNotes }
  })

/** Update a draft release */
export const updateRelease = (
  id: number,
  updates: { version: string; release_notes: string }
): Promise<AxiosResponse<unknown>> => apiClient.patch(`/api/releases/${id}`, updates)

/** Delete a draft release */
export const deleteRelease = (id: number): Promise<AxiosResponse<unknown>> =>
  apiClient.delete(`/api/releases/${id}`)

/** Publish a release */
export const publishRelease = (id: number): Promise<AxiosResponse<unknown>> =>
  apiClient.post(`/api/releases/${id}/publish`)

/** Download a release export as a Blob */
export const downloadReleaseExport = (version: string): Promise<AxiosResponse<Blob>> =>
  apiClient.get(`/api/releases/${version}/export`, { responseType: 'blob' })
