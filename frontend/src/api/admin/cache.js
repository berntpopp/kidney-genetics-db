/**
 * Cache Management API endpoints
 */

import apiClient from '@/api/client'

/**
 * Get cache statistics
 * @returns {Promise} Cache statistics
 */
export const getCacheStats = () => apiClient.get('/api/admin/cache/stats')

/**
 * Get cache namespaces (from health endpoint)
 * @returns {Promise} List of cache namespaces
 */
export const getCacheNamespaces = async () => {
  const healthResponse = await apiClient.get('/api/admin/cache/health')
  const namespaces = healthResponse.data.namespaces || []

  // Fetch stats for each namespace
  const namespaceDetails = await Promise.all(
    namespaces.map(async namespace => {
      try {
        const statsResponse = await apiClient.get(`/api/admin/cache/stats/${namespace}`)
        const stats = statsResponse.data
        return {
          namespace: namespace,
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
          namespace: namespace,
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
 * @param {string} namespace - Namespace name
 * @returns {Promise} Namespace details
 */
export const getNamespaceDetails = namespace => apiClient.get(`/api/admin/cache/stats/${namespace}`)

/**
 * Clear all cache
 * @returns {Promise} Clear result
 */
export const clearAllCache = () => apiClient.delete('/api/admin/cache')

/**
 * Clear specific namespace
 * @param {string} namespace - Namespace to clear
 * @returns {Promise} Clear result
 */
export const clearNamespace = namespace => apiClient.delete(`/api/admin/cache/${namespace}`)

/**
 * Warm cache
 * @param {Object} params - Warm parameters
 * @returns {Promise} Warm result
 */
export const warmCache = (params = {}) => apiClient.post('/api/admin/cache/warm', params)

/**
 * Get cache health
 * @returns {Promise} Cache health status
 */
export const getCacheHealth = () => apiClient.get('/api/admin/cache/health')

export default {
  getCacheStats,
  getCacheNamespaces,
  getNamespaceDetails,
  clearAllCache,
  clearNamespace,
  warmCache,
  getCacheHealth
}
