import { describe, it, expect } from 'vitest'
import {
  SCORE_RANGES,
  TIER_CONFIG,
  getScoreRangeConfig,
  tintedChipStyle
} from '@/utils/evidenceTiers'

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

describe('score-range vocabulary (#314)', () => {
  // ClinGen classifications that describe contrary or absent evidence, not a low score
  const CLINGEN_NEGATIVE_TERMS = ['Disputed', 'Refuted', 'No Known Disease Relationship']

  it('never maps a score in 0..100 to a ClinGen negative classification', () => {
    for (let score = 0; score <= 100; score += 0.25) {
      const label = getScoreRangeConfig(score)?.label ?? ''
      for (const term of CLINGEN_NEGATIVE_TERMS) expect(label).not.toContain(term)
    }
  })

  it('labels every score 0..100 with one of the SCORE_RANGES labels', () => {
    const labels = SCORE_RANGES.map(r => r.label)
    for (let score = 0; score <= 100; score += 0.25) {
      expect(labels).toContain(getScoreRangeConfig(score)?.label)
    }
  })
})
