/**
 * Pinia Store for Log Management
 *
 * Manages reactive log state for the Kidney Genetics Database frontend
 * Provides centralized log storage, filtering, and UI state management
 */

import { defineStore } from 'pinia'
import { ref, computed } from 'vue'

/**
 * Log Store
 *
 * Features:
 * - Reactive log entries array
 * - LogViewer visibility control
 * - Filtering and search capabilities
 * - Statistics and counts
 * - Memory management with configurable limits
 * - Export functionality
 */
export const useLogStore = defineStore('log', () => {
  // State
  const logs = ref([])
  const isViewerVisible = ref(false)
  const maxEntries = ref(getDefaultMaxEntries())
  const searchQuery = ref('')
  const levelFilter = ref([])

  // Statistics tracking
  const stats = ref({
    totalLogsReceived: 0,
    totalLogsDropped: 0,
    lastLogTime: null,
    sessionStartTime: new Date().toISOString()
  })

  // Computed properties
  const logCount = computed(() => logs.value.length)

  const errorCount = computed(
    () => logs.value.filter(log => log.level === 'ERROR' || log.level === 'CRITICAL').length
  )

  const warningCount = computed(() => logs.value.filter(log => log.level === 'WARN').length)

  const infoCount = computed(() => logs.value.filter(log => log.level === 'INFO').length)

  const debugCount = computed(() => logs.value.filter(log => log.level === 'DEBUG').length)

  const logsByLevel = computed(() => {
    const counts = {
      DEBUG: 0,
      INFO: 0,
      WARN: 0,
      ERROR: 0,
      CRITICAL: 0
    }

    logs.value.forEach(log => {
      if (counts[log.level] !== undefined) {
        counts[log.level]++
      }
    })

    return counts
  })

  const filteredLogs = computed(() => {
    let filtered = [...logs.value]

    // Apply level filter
    if (levelFilter.value.length > 0) {
      filtered = filtered.filter(log => levelFilter.value.includes(log.level))
    }

    // Apply search query
    if (searchQuery.value) {
      const query = searchQuery.value.toLowerCase()
      filtered = filtered.filter(
        log =>
          log.message.toLowerCase().includes(query) ||
          log.level.toLowerCase().includes(query) ||
          (log.data && JSON.stringify(log.data).toLowerCase().includes(query)) ||
          (log.correlationId && log.correlationId.toLowerCase().includes(query))
      )
    }

    return filtered
  })

  const recentErrors = computed(() =>
    logs.value
      .filter(log => log.level === 'ERROR' || log.level === 'CRITICAL')
      .slice(-5)
      .reverse()
  )

  const memoryUsage = computed(() => {
    // Rough estimate of memory usage (bytes)
    const jsonSize = JSON.stringify(logs.value).length
    return {
      bytes: jsonSize,
      kb: (jsonSize / 1024).toFixed(2),
      mb: (jsonSize / (1024 * 1024)).toFixed(2)
    }
  })

  // Actions
  function addLogEntry(entry, maxEntriesOverride = null) {
    // Defer to next tick to avoid slot warning during render
    Promise.resolve().then(() => {
      const max = maxEntriesOverride || maxEntries.value

      // Add timestamp if not present
      if (!entry.timestamp) {
        entry.timestamp = new Date().toISOString()
      }

      // Update statistics
      stats.value.totalLogsReceived++
      stats.value.lastLogTime = entry.timestamp

      // Add log entry using single reactive update
      const newLogs = [...logs.value, entry]

      // Trim logs if exceeding max entries
      if (newLogs.length > max) {
        const toRemove = newLogs.length - max
        logs.value = newLogs.slice(toRemove)
        stats.value.totalLogsDropped += toRemove
      } else {
        logs.value = newLogs
      }
    })
  }

  function clearLogs() {
    const previousCount = logs.value.length
    logs.value = []
    stats.value.totalLogsDropped += previousCount
    return previousCount
  }

  function trimLogs(newMaxEntries) {
    if (logs.value.length > newMaxEntries) {
      const toRemove = logs.value.length - newMaxEntries
      logs.value = logs.value.slice(toRemove)
      stats.value.totalLogsDropped += toRemove
    }
    maxEntries.value = newMaxEntries
    saveMaxEntriesToStorage(newMaxEntries)
  }

  function showViewer() {
    isViewerVisible.value = true
  }

  function hideViewer() {
    isViewerVisible.value = false
  }

  function toggleViewer() {
    isViewerVisible.value = !isViewerVisible.value
  }

  function setSearchQuery(query) {
    searchQuery.value = query
  }

  function setLevelFilter(levels) {
    levelFilter.value = levels
  }

  function getMaxEntries() {
    return maxEntries.value
  }

  function setMaxEntries(value) {
    maxEntries.value = value
    saveMaxEntriesToStorage(value)
    trimLogs(value)
  }

  function exportLogs(options = {}) {
    const { format = 'json', includeMetadata = true, filtered = false } = options

    const logsToExport = filtered ? filteredLogs.value : logs.value

    const exportData = {
      exportedAt: new Date().toISOString(),
      application: 'Kidney Genetics Database',
      environment: import.meta.env.MODE,
      sessionStartTime: stats.value.sessionStartTime,
      statistics: {
        totalExported: logsToExport.length,
        totalReceived: stats.value.totalLogsReceived,
        totalDropped: stats.value.totalLogsDropped,
        ...logsByLevel.value
      }
    }

    if (includeMetadata) {
      exportData.metadata = {
        url: window.location.href,
        userAgent: navigator.userAgent,
        screenResolution: `${window.screen.width}x${window.screen.height}`,
        viewport: `${window.innerWidth}x${window.innerHeight}`
      }
    }

    exportData.logs = logsToExport

    if (format === 'json') {
      return JSON.stringify(exportData, null, 2)
    } else if (format === 'csv') {
      return convertToCSV(logsToExport)
    }

    return exportData
  }

  function getLogById(correlationId) {
    return logs.value.filter(log => log.correlationId === correlationId)
  }

  function getLogsByTimeRange(startTime, endTime) {
    const start = new Date(startTime).getTime()
    const end = new Date(endTime).getTime()

    return logs.value.filter(log => {
      const logTime = new Date(log.timestamp).getTime()
      return logTime >= start && logTime <= end
    })
  }

  function getStatistics() {
    return {
      ...stats.value,
      currentCount: logs.value.length,
      maxEntries: maxEntries.value,
      memoryUsage: memoryUsage.value,
      levelCounts: logsByLevel.value,
      oldestLog: logs.value[0]?.timestamp || null,
      newestLog: logs.value[logs.value.length - 1]?.timestamp || null
    }
  }

  // Utility functions
  function convertToCSV(logsArray) {
    if (logsArray.length === 0) return ''

    const headers = ['Timestamp', 'Level', 'Message', 'Data', 'Correlation ID', 'URL']
    const rows = logsArray.map(log => [
      log.timestamp,
      log.level,
      log.message,
      log.data ? JSON.stringify(log.data) : '',
      log.correlationId || '',
      log.url || ''
    ])

    const csvContent = [
      headers.join(','),
      ...rows.map(row => row.map(cell => `"${String(cell).replace(/"/g, '""')}"`).join(','))
    ].join('\n')

    return csvContent
  }

  function getDefaultMaxEntries() {
    try {
      const stored = localStorage.getItem('kidney-genetics-log-max-entries')
      if (stored) {
        const parsed = parseInt(stored, 10)
        if (!isNaN(parsed) && parsed > 0) {
          return parsed
        }
      }
    } catch (error) {
      console.error('Failed to load max entries from storage:', error)
    }
    return import.meta.env.DEV ? 100 : 50
  }

  function saveMaxEntriesToStorage(value) {
    try {
      localStorage.setItem('kidney-genetics-log-max-entries', value.toString())
    } catch (error) {
      console.error('Failed to save max entries to storage:', error)
    }
  }

  // Return public API
  return {
    // State
    logs,
    isViewerVisible,
    maxEntries,
    searchQuery,
    levelFilter,

    // Computed
    logCount,
    errorCount,
    warningCount,
    infoCount,
    debugCount,
    logsByLevel,
    filteredLogs,
    recentErrors,
    memoryUsage,

    // Actions
    addLogEntry,
    clearLogs,
    trimLogs,
    showViewer,
    hideViewer,
    toggleViewer,
    setSearchQuery,
    setLevelFilter,
    getMaxEntries,
    setMaxEntries,
    exportLogs,
    getLogById,
    getLogsByTimeRange,
    getStatistics
  }
})
