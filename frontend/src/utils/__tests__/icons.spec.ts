import { describe, it, expect } from 'vitest'
import { ADMIN_ICONS } from '@/utils/adminIcons'

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

  it('every value is a Vue component (not an icon-name string)', () => {
    for (const [key, value] of Object.entries(ADMIN_ICONS)) {
      expect(typeof value !== 'string', `${key} should not be a string — got "${value}"`).toBe(true)
    }
  })
})
