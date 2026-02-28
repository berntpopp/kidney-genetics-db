/**
 * Cache Management API endpoints
 * Admin module: functions return Promise<AxiosResponse<T>> (callers use .data)
 */

import apiClient from '@/api/client'
import type { AxiosResponse } from 'axios'

/** Cache namespace detail item */
export interface CacheNamespaceDetail {
  namespace: string
  entry_count: number
  size_bytes: number
  size_mb: number
  oldest_entry: string | null
  newest_entry: string | null
  active_entries?: number
  expired_entries?: number
}

/** Response from getCacheNamespaces (processed, not raw AxiosResponse) */
export interface CacheNamespacesResult {
  data: CacheNamespaceDetail[]
}

/** Cache health response data shape */
interface CacheHealthData {
  namespaces: string[]
  [key: string]: unknown
}

/** Cache namespace stats data shape */
interface NamespaceStatsData {
  total_entries: number
  total_size_bytes: number
  oldest_entry: string | null
  newest_entry: string | null
  active_entries: number
  expired_entries: number
  [key: string]: unknown
}

/**
 * Get cache statistics
 */
export const getCacheStats = (): Promise<AxiosResponse<unknown>> =>
  apiClient.get('/api/admin/cache/stats')

/**
 * Get cache namespaces (from health endpoint, processed result)
 * Note: returns a processed object, not raw AxiosResponse
 */
export const getCacheNamespaces = async (): Promise<CacheNamespacesResult> => {
  const healthResponse = await apiClient.get<CacheHealthData>('/api/admin/cache/health')
  const namespaces: string[] = healthResponse.data.namespaces || []

  // Fetch stats for each namespace
  const namespaceDetails = await Promise.all(
    namespaces.map(async (namespace: string): Promise<CacheNamespaceDetail> => {
      try {
        const statsResponse = await apiClient.get<NamespaceStatsData>(
          `/api/admin/cache/stats/${namespace}`
        )
        const stats = statsResponse.data
        return {
          namespace,
          entry_count: stats.total_entries || 0,
          size_bytes: stats.total_size_bytes || 0,
          size_mb: (stats.total_size_bytes || 0) / (1024 * 1024),
          oldest_entry: stats.oldest_entry,
          newest_entry: stats.newest_entry,
          active_entries: stats.active_entries || 0,
          expired_entries: stats.expired_entries || 0
        }
      } catch {
        // If individual namespace fails, return basic info
        return {
          namespace,
          entry_count: 0,
          size_bytes: 0,
          size_mb: 0,
          oldest_entry: null,
          newest_entry: null
        }
      }
    })
  )

  return { data: namespaceDetails }
}

/**
 * Get namespace details
 */
export const getNamespaceDetails = (namespace: string): Promise<AxiosResponse<unknown>> =>
  apiClient.get(`/api/admin/cache/stats/${namespace}`)

/**
 * Clear all cache
 */
export const clearAllCache = (): Promise<AxiosResponse<unknown>> =>
  apiClient.delete('/api/admin/cache')

/**
 * Clear specific namespace
 */
export const clearNamespace = (namespace: string): Promise<AxiosResponse<unknown>> =>
  apiClient.delete(`/api/admin/cache/${namespace}`)

/**
 * Warm cache
 */
export const warmCache = (
  params: Record<string, unknown> = {}
): Promise<AxiosResponse<unknown>> => apiClient.post('/api/admin/cache/warm', params)

/**
 * Get cache health
 */
export const getCacheHealth = (): Promise<AxiosResponse<unknown>> =>
  apiClient.get('/api/admin/cache/health')

export default {
  getCacheStats,
  getCacheNamespaces,
  getNamespaceDetails,
  clearAllCache,
  clearNamespace,
  warmCache,
  getCacheHealth
}
