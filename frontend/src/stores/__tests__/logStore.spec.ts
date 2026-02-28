/**
 * Log Store Tests
 *
 * Tests for log state management:
 * - addLogEntry behavior and trimming
 * - clearLogs
 * - trimLogs
 * - filter computed properties
 */

import { describe, it, expect, vi, beforeEach } from 'vitest'
import { setActivePinia, createPinia } from 'pinia'
import { useLogStore } from '@/stores/logStore'
import type { LogEntry } from '@/types/log'

/** Build a minimal LogEntry for testing */
function makeEntry(
  level: LogEntry['level'] = 'INFO',
  message = 'test message',
  correlationId?: string
): LogEntry {
  return {
    timestamp: new Date().toISOString(),
    level,
    message,
    ...(correlationId ? { correlationId } : {})
  }
}

describe('useLogStore', () => {
  beforeEach(() => {
    setActivePinia(createPinia())
    vi.clearAllMocks()
    localStorage.clear()
  })

  describe('addLogEntry', () => {
    it('adds entries to the logs array asynchronously', async () => {
      const store = useLogStore()
      const entry = makeEntry('INFO', 'Hello')

      store.addLogEntry(entry)
      // addLogEntry defers to Promise.resolve() so wait a tick
      await Promise.resolve()

      expect(store.logs).toHaveLength(1)
      expect(store.logs[0].message).toBe('Hello')
    })

    it('adds timestamp if entry has no timestamp', async () => {
      const store = useLogStore()
      const entry: LogEntry = { level: 'INFO', message: 'no ts', timestamp: '' }

      store.addLogEntry(entry)
      await Promise.resolve()

      expect(store.logs[0].timestamp).not.toBe('')
      expect(store.logs[0].timestamp).toBeTruthy()
    })

    it('trims oldest logs when maxEntries is exceeded via override', async () => {
      const store = useLogStore()

      // Add 5 entries with maxEntries override of 3
      for (let i = 0; i < 5; i++) {
        store.addLogEntry(makeEntry('DEBUG', `msg ${i}`), 3)
        await Promise.resolve()
      }

      expect(store.logs).toHaveLength(3)
      // Should keep the most recent 3
      expect(store.logs[2].message).toBe('msg 4')
    })

    it('increments totalLogsReceived statistics', async () => {
      const store = useLogStore()

      store.addLogEntry(makeEntry())
      await Promise.resolve()
      store.addLogEntry(makeEntry())
      await Promise.resolve()

      const stats = store.getStatistics()
      expect(stats.totalLogsReceived).toBe(2)
    })
  })

  describe('clearLogs', () => {
    it('removes all log entries and returns the count cleared', async () => {
      const store = useLogStore()

      store.addLogEntry(makeEntry('INFO', 'entry 1'))
      store.addLogEntry(makeEntry('ERROR', 'entry 2'))
      await Promise.resolve()

      const cleared = store.clearLogs()

      expect(cleared).toBe(2)
      expect(store.logs).toHaveLength(0)
    })

    it('increments totalLogsDropped by the number cleared', async () => {
      const store = useLogStore()

      store.addLogEntry(makeEntry())
      store.addLogEntry(makeEntry())
      await Promise.resolve()
      store.clearLogs()

      const stats = store.getStatistics()
      expect(stats.totalLogsDropped).toBe(2)
    })
  })

  describe('trimLogs', () => {
    it('removes oldest entries when count exceeds new max', async () => {
      const store = useLogStore()

      for (let i = 0; i < 5; i++) {
        store.addLogEntry(makeEntry('DEBUG', `msg ${i}`))
        await Promise.resolve()
      }

      store.trimLogs(3)

      expect(store.logs).toHaveLength(3)
      expect(store.logs[0].message).toBe('msg 2')
      expect(store.logs[2].message).toBe('msg 4')
    })

    it('updates maxEntries to new value', async () => {
      const store = useLogStore()
      store.trimLogs(42)
      expect(store.maxEntries).toBe(42)
    })
  })

  describe('computed counts', () => {
    it('errorCount counts ERROR and CRITICAL levels', async () => {
      const store = useLogStore()

      store.addLogEntry(makeEntry('ERROR', 'err1'))
      store.addLogEntry(makeEntry('CRITICAL', 'crit'))
      store.addLogEntry(makeEntry('INFO', 'info'))
      await Promise.resolve()

      expect(store.errorCount).toBe(2)
      expect(store.infoCount).toBe(1)
      expect(store.warningCount).toBe(0)
    })

    it('filteredLogs respects levelFilter', async () => {
      const store = useLogStore()

      store.addLogEntry(makeEntry('DEBUG', 'debug'))
      store.addLogEntry(makeEntry('INFO', 'info'))
      store.addLogEntry(makeEntry('ERROR', 'error'))
      await Promise.resolve()

      store.setLevelFilter(['ERROR'])
      expect(store.filteredLogs).toHaveLength(1)
      expect(store.filteredLogs[0].level).toBe('ERROR')
    })

    it('filteredLogs respects searchQuery', async () => {
      const store = useLogStore()

      store.addLogEntry(makeEntry('INFO', 'kidney gene data'))
      store.addLogEntry(makeEntry('INFO', 'other message'))
      await Promise.resolve()

      store.setSearchQuery('kidney')
      expect(store.filteredLogs).toHaveLength(1)
      expect(store.filteredLogs[0].message).toContain('kidney')
    })
  })

  describe('viewer visibility', () => {
    it('toggles viewer visibility', () => {
      const store = useLogStore()

      expect(store.isViewerVisible).toBe(false)
      store.showViewer()
      expect(store.isViewerVisible).toBe(true)
      store.hideViewer()
      expect(store.isViewerVisible).toBe(false)
      store.toggleViewer()
      expect(store.isViewerVisible).toBe(true)
    })
  })
})
