/**
 * Backup Formatters Composable
 * Reusable formatting functions for backup data
 */

export function useBackupFormatters() {
  /**
   * Get status color for chips
   */
  const getStatusColor = status => {
    const colors = {
      completed: 'success',
      running: 'info',
      failed: 'error',
      pending: 'warning',
      restored: 'purple'
    }
    return colors[status] || 'grey'
  }

  /**
   * Get status icon
   */
  const getStatusIcon = status => {
    const icons = {
      completed: 'mdi-check-circle',
      running: 'mdi-progress-clock',
      failed: 'mdi-alert-circle',
      pending: 'mdi-clock-outline',
      restored: 'mdi-database-import'
    }
    return icons[status] || 'mdi-help-circle'
  }

  /**
   * Format file size in MB/GB
   */
  const formatSize = sizeMb => {
    if (!sizeMb && sizeMb !== 0) return '—'
    if (sizeMb >= 1024) return `${(sizeMb / 1024).toFixed(2)} GB`
    return `${sizeMb.toFixed(2)} MB`
  }

  /**
   * Format duration in seconds to human-readable
   */
  const formatDuration = seconds => {
    if (!seconds && seconds !== 0) return '—'
    if (seconds < 60) return `${seconds}s`
    const minutes = Math.floor(seconds / 60)
    const secs = seconds % 60
    return `${minutes}m ${secs}s`
  }

  /**
   * Format date to locale string
   */
  const formatDate = date => {
    if (!date) return '—'
    return new Date(date).toLocaleString()
  }

  /**
   * Format relative time (e.g., "2h ago")
   */
  const formatRelativeTime = date => {
    if (!date) return '—'
    const now = new Date()
    const then = new Date(date)
    const diffMs = now - then
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
  const formatBytes = bytes => {
    if (!bytes && bytes !== 0) return '—'
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
