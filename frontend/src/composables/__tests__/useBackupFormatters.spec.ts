/**
 * useBackupFormatters Composable Tests
 *
 * Tests for pure formatting functions.
 * These are deterministic, no async or mocking needed.
 */

import { describe, it, expect } from 'vitest'
import { useBackupFormatters } from '@/composables/useBackupFormatters'

describe('useBackupFormatters', () => {
  const {
    getStatusColor,
    getStatusIcon,
    formatSize,
    formatDuration,
    formatDate,
    formatRelativeTime,
    formatBytes
  } = useBackupFormatters()

  describe('getStatusColor', () => {
    it('returns correct color for known statuses', () => {
      expect(getStatusColor('completed')).toBe('success')
      expect(getStatusColor('running')).toBe('info')
      expect(getStatusColor('failed')).toBe('error')
      expect(getStatusColor('pending')).toBe('warning')
      expect(getStatusColor('restored')).toBe('purple')
    })

    it('returns "grey" for unknown status', () => {
      expect(getStatusColor('unknown-status')).toBe('grey')
      expect(getStatusColor('')).toBe('grey')
    })
  })

  describe('getStatusIcon', () => {
    it('returns correct icon for known statuses', () => {
      expect(getStatusIcon('completed')).toBe('mdi-check-circle')
      expect(getStatusIcon('failed')).toBe('mdi-alert-circle')
      expect(getStatusIcon('running')).toBe('mdi-progress-clock')
    })

    it('returns fallback icon for unknown status', () => {
      expect(getStatusIcon('bogus')).toBe('mdi-help-circle')
    })
  })

  describe('formatSize', () => {
    it('formats MB sizes correctly', () => {
      expect(formatSize(512)).toBe('512.00 MB')
      expect(formatSize(0)).toBe('0.00 MB')
    })

    it('formats GB sizes when >= 1024 MB', () => {
      expect(formatSize(2048)).toBe('2.00 GB')
    })

    it('returns em dash for null/undefined', () => {
      expect(formatSize(null)).toBe('\u2014')
      expect(formatSize(undefined)).toBe('\u2014')
    })
  })

  describe('formatDuration', () => {
    it('formats seconds for durations under 1 minute', () => {
      expect(formatDuration(30)).toBe('30s')
      expect(formatDuration(0)).toBe('0s')
    })

    it('formats minutes and seconds for durations >= 60s', () => {
      expect(formatDuration(90)).toBe('1m 30s')
      expect(formatDuration(120)).toBe('2m 0s')
    })

    it('returns em dash for null/undefined', () => {
      expect(formatDuration(null)).toBe('\u2014')
      expect(formatDuration(undefined)).toBe('\u2014')
    })
  })

  describe('formatBytes', () => {
    it('formats KB correctly', () => {
      expect(formatBytes(512)).toBe('0.50 KB')
    })

    it('formats MB when >= 1 MB', () => {
      expect(formatBytes(1024 * 1024)).toBe('1.00 MB')
    })

    it('formats GB when >= 1 GB', () => {
      expect(formatBytes(1024 * 1024 * 1024)).toBe('1.00 GB')
    })

    it('returns em dash for null/undefined', () => {
      expect(formatBytes(null)).toBe('\u2014')
      expect(formatBytes(undefined)).toBe('\u2014')
    })
  })

  describe('formatDate', () => {
    it('returns em dash for null/undefined', () => {
      expect(formatDate(null)).toBe('\u2014')
      expect(formatDate(undefined)).toBe('\u2014')
    })

    it('returns a non-empty string for a valid date', () => {
      const result = formatDate('2024-01-15T10:00:00Z')
      expect(result).not.toBe('\u2014')
      expect(result.length).toBeGreaterThan(0)
    })
  })

  describe('formatRelativeTime', () => {
    it('returns em dash for null/undefined', () => {
      expect(formatRelativeTime(null)).toBe('\u2014')
      expect(formatRelativeTime(undefined)).toBe('\u2014')
    })

    it('returns "Just now" for a very recent date', () => {
      const recent = new Date(Date.now() - 1000 * 30).toISOString() // 30 seconds ago
      expect(formatRelativeTime(recent)).toBe('Just now')
    })

    it('returns hours ago for dates within 24 hours', () => {
      const twoHoursAgo = new Date(Date.now() - 1000 * 60 * 60 * 2).toISOString()
      expect(formatRelativeTime(twoHoursAgo)).toBe('2h ago')
    })
  })
})
