import { describe, it, expect } from 'vitest'
import { formatDate, formatDateTime } from '@/utils/formatDate'

describe('formatDate', () => {
  it('formats a date and a date-time in en-GB short form', () => {
    expect(formatDate('2026-03-15T14:05:00')).toBe('15 Mar 2026')
    expect(formatDateTime('2026-03-15T14:05:00')).toBe('15 Mar 2026, 14:05')
  })

  it('returns an empty string for missing or invalid input', () => {
    expect(formatDate(null)).toBe('')
    expect(formatDate(undefined)).toBe('')
    expect(formatDateTime('not a date')).toBe('')
  })
})
