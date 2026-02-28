/**
 * Backup API Composable
 * Handles all backup-related API calls with proper error handling
 */

import { ref } from 'vue'
import type { Ref } from 'vue'
import { useAuthStore } from '@/stores/auth'

/** Backup creation options */
interface BackupCreateOptions {
  description?: string
  includeLogs?: boolean
  includeCache?: boolean
  compressionLevel?: number
  parallelJobs?: number
}

/** Restore options */
interface RestoreOptions {
  createSafetyBackup?: boolean
  runAnalyze?: boolean
}

/** Backup list filter params */
interface BackupListParams {
  limit?: number
  offset?: number
  status?: string
  triggerSource?: string
  search?: string
}

/** Backup record shape returned from API */
interface BackupRecord {
  id: number
  filename: string
  [key: string]: unknown
}

/** Return type for useBackupApi */
export interface BackupApiReturn {
  loading: Ref<boolean>
  error: Ref<string | null>
  loadStats: () => Promise<unknown>
  loadBackups: (params?: BackupListParams) => Promise<unknown>
  createBackup: (backupData: BackupCreateOptions) => Promise<unknown>
  restoreBackup: (backupId: number, restoreOptions: RestoreOptions) => Promise<unknown>
  downloadBackup: (backup: BackupRecord) => Promise<boolean>
  deleteBackup: (backupId: number) => Promise<unknown>
  cleanupOldBackups: () => Promise<unknown>
}

export function useBackupApi(): BackupApiReturn {
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
   * Load backup statistics
   */
  const loadStats = async (): Promise<unknown> => {
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
  const loadBackups = async (params: BackupListParams = {}): Promise<unknown> => {
    loading.value = true
    error.value = null
    try {
      const queryParams = new URLSearchParams()

      if (params.limit !== undefined) queryParams.append('limit', String(params.limit))
      if (params.offset !== undefined) queryParams.append('offset', String(params.offset))
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
  const createBackup = async (backupData: BackupCreateOptions): Promise<unknown> => {
    loading.value = true
    error.value = null
    try {
      return await apiRequest('/api/admin/backups/create', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json'
        },
        body: JSON.stringify({
          description: backupData.description ?? '',
          include_logs: backupData.includeLogs ?? false,
          include_cache: backupData.includeCache ?? false,
          compression_level: backupData.compressionLevel ?? 6,
          parallel_jobs: backupData.parallelJobs ?? 2
        })
      })
    } finally {
      loading.value = false
    }
  }

  /**
   * Restore from backup
   */
  const restoreBackup = async (
    backupId: number,
    restoreOptions: RestoreOptions
  ): Promise<unknown> => {
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
  const downloadBackup = async (backup: BackupRecord): Promise<boolean> => {
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
  const deleteBackup = async (backupId: number): Promise<unknown> => {
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
  const cleanupOldBackups = async (): Promise<unknown> => {
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
