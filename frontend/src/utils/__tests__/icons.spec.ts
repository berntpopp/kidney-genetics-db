import { describe, it, expect } from 'vitest'
import { MdiToLucide, resolveMdiIcon } from '@/utils/icons'
import { ADMIN_ICONS } from '@/utils/adminIcons'

describe('icons.ts — MDI to Lucide mapping', () => {
  it('exports MdiToLucide with at least 190 entries', () => {
    const count = Object.keys(MdiToLucide).length
    expect(count).toBeGreaterThanOrEqual(190)
  })

  it('every key starts with "mdi-"', () => {
    for (const key of Object.keys(MdiToLucide)) {
      expect(key).toMatch(/^mdi-/)
    }
  })

  it('every value is a valid Vue component (object or function)', () => {
    for (const [key, value] of Object.entries(MdiToLucide)) {
      expect(
        typeof value === 'object' || typeof value === 'function',
        `${key} should map to a component, got ${typeof value}`
      ).toBe(true)
    }
  })

  it('resolves known icons correctly', () => {
    expect(resolveMdiIcon('mdi-account')).toBeTruthy()
    expect(resolveMdiIcon('mdi-dna')).toBeTruthy()
    expect(resolveMdiIcon('mdi-magnify')).toBeTruthy()
    expect(resolveMdiIcon('mdi-check')).toBeTruthy()
  })

  it('returns null for unknown icons', () => {
    expect(resolveMdiIcon('mdi-nonexistent-icon')).toBeNull()
    expect(resolveMdiIcon('')).toBeNull()
    expect(resolveMdiIcon('not-mdi')).toBeNull()
  })

  it('does not include mdi-vuejs (dropped icon)', () => {
    expect(MdiToLucide['mdi-vuejs']).toBeUndefined()
  })

  it('maps mdi-vuejs returns null via resolver', () => {
    expect(resolveMdiIcon('mdi-vuejs')).toBeNull()
  })
})

describe('adminIcons.ts — Lucide component exports', () => {
  it('exports all expected admin section icons', () => {
    const expectedKeys = [
      'dashboard',
      'users',
      'cache',
      'logs',
      'settings',
      'pipeline',
      'staging',
      'annotations',
      'releases',
      'backups',
      'hybridSources',
      'refresh',
      'play',
      'stop',
      'delete',
      'edit',
      'add',
      'success',
      'error',
      'warning',
      'info'
    ]
    for (const key of expectedKeys) {
      expect(ADMIN_ICONS[key], `${key} should be defined`).toBeTruthy()
    }
  })

  it('every value is a Vue component (not an mdi-* string)', () => {
    for (const [key, value] of Object.entries(ADMIN_ICONS)) {
      expect(typeof value !== 'string', `${key} should not be a string — got "${value}"`).toBe(true)
    }
  })
})
