/**
 * Settings API Composable
 * Handles all settings-related API calls with proper error handling
 */

import { ref } from 'vue'
import type { Ref } from 'vue'
import { useAuthStore } from '@/stores/auth'

/** Load settings filter params */
interface SettingsListParams {
  category?: string
  limit?: number
  offset?: number
}

/** Return type for useSettingsApi */
export interface SettingsApiReturn {
  loading: Ref<boolean>
  error: Ref<string | null>
  loadSettings: (params?: SettingsListParams) => Promise<unknown>
  loadCategories: () => Promise<unknown>
  loadStats: () => Promise<unknown>
  updateSetting: (
    settingId: number | string,
    value: unknown,
    changeReason?: string | null
  ) => Promise<unknown>
  getSettingHistory: (settingId: number | string, limit?: number) => Promise<unknown>
  getAllAuditHistory: (limit?: number) => Promise<unknown>
}

export function useSettingsApi(): SettingsApiReturn {
  const authStore = useAuthStore()
  const loading = ref<boolean>(false)
  const error = ref<string | null>(null)

  /**
   * Generic API request handler with auth
   */
  const apiRequest = async (url: string, options: RequestInit = {}): Promise<unknown> => {
    try {
      const response = await fetch(url, {
        ...options,
        headers: {
          ...(options.headers ?? {}),
          Authorization: `Bearer ${authStore.accessToken}`
        }
      })

      if (!response.ok) {
        const errorData = (await response.json().catch(() => ({}))) as { detail?: string }
        throw new Error(errorData.detail ?? `Request failed: ${response.statusText}`)
      }

      return await response.json()
    } catch (err: unknown) {
      const msg = err instanceof Error ? err.message : String(err)
      error.value = msg
      throw err
    }
  }

  /**
   * Load all settings with optional filters
   */
  const loadSettings = async (params: SettingsListParams = {}): Promise<unknown> => {
    loading.value = true
    error.value = null
    try {
      const queryParams = new URLSearchParams()

      if (params.category) queryParams.append('category', params.category)
      if (params.limit !== undefined) queryParams.append('limit', String(params.limit))
      if (params.offset !== undefined) queryParams.append('offset', String(params.offset))

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
  const loadCategories = async (): Promise<unknown> => {
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
  const loadStats = async (): Promise<unknown> => {
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
  const updateSetting = async (
    settingId: number | string,
    value: unknown,
    changeReason: string | null = null
  ): Promise<unknown> => {
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
  const getSettingHistory = async (settingId: number | string, limit = 50): Promise<unknown> => {
    loading.value = true
    error.value = null
    try {
      const queryParams = new URLSearchParams()
      if (limit) queryParams.append('limit', String(limit))

      return await apiRequest(`/api/admin/settings/${settingId}/history?${queryParams}`)
    } finally {
      loading.value = false
    }
  }

  /**
   * Get all audit history
   */
  const getAllAuditHistory = async (limit = 100): Promise<unknown> => {
    loading.value = true
    error.value = null
    try {
      const queryParams = new URLSearchParams()
      if (limit) queryParams.append('limit', String(limit))

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
