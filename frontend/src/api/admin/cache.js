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
 * Get cache namespaces
 * @returns {Promise} List of cache namespaces
 */
export const getCacheNamespaces = () => apiClient.get('/api/admin/cache/namespaces')

/**
 * Get namespace details
 * @param {string} namespace - Namespace name
 * @returns {Promise} Namespace details
 */
export const getNamespaceDetails = namespace =>
  apiClient.get(`/api/admin/cache/namespace/${namespace}`)

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
