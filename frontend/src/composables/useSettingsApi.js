/**
 * Settings API Composable
 * Handles all settings-related API calls with proper error handling
 */

import { ref } from 'vue'
import { useAuthStore } from '@/stores/auth'

export function useSettingsApi() {
  const authStore = useAuthStore()
  const loading = ref(false)
  const error = ref(null)

  /**
   * Generic API request handler with auth
   */
  const apiRequest = async (url, options = {}) => {
    try {
      const response = await fetch(url, {
        ...options,
        headers: {
          ...options.headers,
          Authorization: `Bearer ${authStore.accessToken}`
        }
      })

      if (!response.ok) {
        const errorData = await response.json().catch(() => ({}))
        throw new Error(errorData.detail || `Request failed: ${response.statusText}`)
      }

      return await response.json()
    } catch (err) {
      error.value = err.message
      throw err
    }
  }

  /**
   * Load all settings with optional filters
   */
  const loadSettings = async (params = {}) => {
    loading.value = true
    error.value = null
    try {
      const queryParams = new URLSearchParams()

      if (params.category) queryParams.append('category', params.category)
      if (params.limit) queryParams.append('limit', params.limit)
      if (params.offset) queryParams.append('offset', params.offset)

      // CRITICAL: Trailing slash is required to prevent FastAPI 307 redirect
      // Without trailing slash: /api/admin/settings?query → redirects to /api/admin/settings/?query
      // The redirect causes browsers to drop the Authorization header (security feature)
      // This creates inconsistency with other endpoints but is necessary until backend routing is standardized
      return await apiRequest(`/api/admin/settings/?${queryParams}`)
    } finally {
      loading.value = false
    }
  }

  /**
   * Load setting categories with counts
   */
  const loadCategories = async () => {
    loading.value = true
    error.value = null
    try {
      return await apiRequest('/api/admin/settings/categories')
    } finally {
      loading.value = false
    }
  }

  /**
   * Load settings statistics
   */
  const loadStats = async () => {
    loading.value = true
    error.value = null
    try {
      return await apiRequest('/api/admin/settings/stats')
    } finally {
      loading.value = false
    }
  }

  /**
   * Update a setting value
   */
  const updateSetting = async (settingId, value, changeReason = null) => {
    loading.value = true
    error.value = null
    try {
      return await apiRequest(`/api/admin/settings/${settingId}`, {
        method: 'PUT',
        headers: {
          'Content-Type': 'application/json'
        },
        body: JSON.stringify({
          value,
          change_reason: changeReason
        })
      })
    } finally {
      loading.value = false
    }
  }

  /**
   * Get audit history for a specific setting
   */
  const getSettingHistory = async (settingId, limit = 50) => {
    loading.value = true
    error.value = null
    try {
      const queryParams = new URLSearchParams()
      if (limit) queryParams.append('limit', limit)

      return await apiRequest(`/api/admin/settings/${settingId}/history?${queryParams}`)
    } finally {
      loading.value = false
    }
  }

  /**
   * Get all audit history
   */
  const getAllAuditHistory = async (limit = 100) => {
    loading.value = true
    error.value = null
    try {
      const queryParams = new URLSearchParams()
      if (limit) queryParams.append('limit', limit)

      return await apiRequest(`/api/admin/settings/audit/all?${queryParams}`)
    } finally {
      loading.value = false
    }
  }

  return {
    // State
    loading,
    error,

    // Methods
    loadSettings,
    loadCategories,
    loadStats,
    updateSetting,
    getSettingHistory,
    getAllAuditHistory
  }
}
