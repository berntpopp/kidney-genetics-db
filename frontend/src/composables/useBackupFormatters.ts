/**
 * Backup Formatters Composable
 * Reusable formatting functions for backup data
 */

/** Return type for useBackupFormatters */
export interface BackupFormatters {
  getStatusColor: (status: string) => string
  getStatusIcon: (status: string) => string
  formatSize: (sizeMb: number | null | undefined) => string
  formatDuration: (seconds: number | null | undefined) => string
  formatDate: (date: string | Date | null | undefined) => string
  formatRelativeTime: (date: string | Date | null | undefined) => string
  formatBytes: (bytes: number | null | undefined) => string
}

export function useBackupFormatters(): BackupFormatters {
  /**
   * Get status color for chips
   */
  const getStatusColor = (status: string): string => {
    const colors: Record<string, string> = {
      completed: 'success',
      running: 'info',
      failed: 'error',
      pending: 'warning',
      restored: 'purple'
    }
    return colors[status] ?? 'grey'
  }

  /**
   * Get status icon
   */
  const getStatusIcon = (status: string): string => {
    const icons: Record<string, string> = {
      completed: 'mdi-check-circle',
      running: 'mdi-progress-clock',
      failed: 'mdi-alert-circle',
      pending: 'mdi-clock-outline',
      restored: 'mdi-database-import'
    }
    return icons[status] ?? 'mdi-help-circle'
  }

  /**
   * Format file size in MB/GB
   */
  const formatSize = (sizeMb: number | null | undefined): string => {
    if (sizeMb == null) return '\u2014'
    if (sizeMb >= 1024) return `${(sizeMb / 1024).toFixed(2)} GB`
    return `${sizeMb.toFixed(2)} MB`
  }

  /**
   * Format duration in seconds to human-readable
   */
  const formatDuration = (seconds: number | null | undefined): string => {
    if (seconds == null) return '\u2014'
    if (seconds < 60) return `${seconds}s`
    const minutes = Math.floor(seconds / 60)
    const secs = seconds % 60
    return `${minutes}m ${secs}s`
  }

  /**
   * Format date to locale string
   */
  const formatDate = (date: string | Date | null | undefined): string => {
    if (!date) return '\u2014'
    return new Date(date).toLocaleString()
  }

  /**
   * Format relative time (e.g., "2h ago")
   */
  const formatRelativeTime = (date: string | Date | null | undefined): string => {
    if (!date) return '\u2014'
    const now = new Date()
    const then = new Date(date)
    const diffMs = now.getTime() - then.getTime()
    const diffHours = Math.floor(diffMs / (1000 * 60 * 60))

    if (diffHours < 1) return 'Just now'
    if (diffHours < 24) return `${diffHours}h ago`
    const diffDays = Math.floor(diffHours / 24)
    if (diffDays < 7) return `${diffDays}d ago`
    const diffWeeks = Math.floor(diffDays / 7)
    return `${diffWeeks}w ago`
  }

  /**
   * Format bytes to human-readable size
   */
  const formatBytes = (bytes: number | null | undefined): string => {
    if (bytes == null) return '\u2014'
    const gb = bytes / (1024 * 1024 * 1024)
    if (gb >= 1) return `${gb.toFixed(2)} GB`
    const mb = bytes / (1024 * 1024)
    if (mb >= 1) return `${mb.toFixed(2)} MB`
    const kb = bytes / 1024
    return `${kb.toFixed(2)} KB`
  }

  return {
    getStatusColor,
    getStatusIcon,
    formatSize,
    formatDuration,
    formatDate,
    formatRelativeTime,
    formatBytes
  }
}
