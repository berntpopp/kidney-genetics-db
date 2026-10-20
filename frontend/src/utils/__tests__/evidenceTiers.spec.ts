import { describe, it, expect } from 'vitest'
import { TIER_CONFIG, tintedChipStyle } from '@/utils/evidenceTiers'

describe('tintedChipStyle (#320)', () => {
  it('keeps the tint but never uses the raw 500-shade as text color', () => {
    for (const { color } of Object.values(TIER_CONFIG)) {
      const style = tintedChipStyle(color)
      expect(style.backgroundColor).toBe(color + '20')
      expect(style.borderColor).toBe(color + '40')
      expect(style.color).not.toBe(color)
      expect(style.color).toBe(`color-mix(in oklab, ${color} 55%, var(--foreground))`)
    }
  })
})
