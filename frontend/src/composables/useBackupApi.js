/**
 * Backup API Composable
 * Handles all backup-related API calls with proper error handling
 */

import { ref } from 'vue'
import { useAuthStore } from '@/stores/auth'

export function useBackupApi() {
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
   * Load backup statistics
   */
  const loadStats = async () => {
    loading.value = true
    error.value = null
    try {
      return await apiRequest('/api/admin/backups/stats')
    } finally {
      loading.value = false
    }
  }

  /**
   * Load backups list with filters
   */
  const loadBackups = async (params = {}) => {
    loading.value = true
    error.value = null
    try {
      const queryParams = new URLSearchParams()

      if (params.limit) queryParams.append('limit', params.limit)
      if (params.offset) queryParams.append('offset', params.offset)
      if (params.status) queryParams.append('status', params.status)
      if (params.triggerSource) queryParams.append('trigger_source', params.triggerSource)
      if (params.search) queryParams.append('search', params.search)

      return await apiRequest(`/api/admin/backups?${queryParams}`)
    } finally {
      loading.value = false
    }
  }

  /**
   * Create a new backup
   */
  const createBackup = async backupData => {
    loading.value = true
    error.value = null
    try {
      return await apiRequest('/api/admin/backups/create', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json'
        },
        body: JSON.stringify({
          description: backupData.description || '',
          include_logs: backupData.includeLogs || false,
          include_cache: backupData.includeCache || false,
          compression_level: backupData.compressionLevel || 6,
          parallel_jobs: backupData.parallelJobs || 2
        })
      })
    } finally {
      loading.value = false
    }
  }

  /**
   * Restore from backup
   */
  const restoreBackup = async (backupId, restoreOptions) => {
    loading.value = true
    error.value = null
    try {
      return await apiRequest(`/api/admin/backups/restore/${backupId}`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json'
        },
        body: JSON.stringify({
          create_safety_backup: restoreOptions.createSafetyBackup ?? true,
          run_analyze: restoreOptions.runAnalyze ?? true
        })
      })
    } finally {
      loading.value = false
    }
  }

  /**
   * Download backup file
   */
  const downloadBackup = async backup => {
    loading.value = true
    error.value = null
    try {
      const response = await fetch(`/api/admin/backups/${backup.id}/download`, {
        headers: {
          Authorization: `Bearer ${authStore.accessToken}`
        }
      })

      if (!response.ok) {
        throw new Error('Failed to download backup')
      }

      const blob = await response.blob()
      const url = URL.createObjectURL(blob)
      const a = document.createElement('a')
      a.href = url
      a.download = backup.filename
      document.body.appendChild(a)
      a.click()
      document.body.removeChild(a)
      URL.revokeObjectURL(url)

      return true
    } finally {
      loading.value = false
    }
  }

  /**
   * Delete a backup
   */
  const deleteBackup = async backupId => {
    loading.value = true
    error.value = null
    try {
      return await apiRequest(`/api/admin/backups/${backupId}`, {
        method: 'DELETE'
      })
    } finally {
      loading.value = false
    }
  }

  /**
   * Cleanup old backups
   */
  const cleanupOldBackups = async () => {
    loading.value = true
    error.value = null
    try {
      return await apiRequest('/api/admin/backups/cleanup', {
        method: 'POST'
      })
    } finally {
      loading.value = false
    }
  }

  return {
    // State
    loading,
    error,

    // Methods
    loadStats,
    loadBackups,
    createBackup,
    restoreBackup,
    downloadBackup,
    deleteBackup,
    cleanupOldBackups
  }
}
