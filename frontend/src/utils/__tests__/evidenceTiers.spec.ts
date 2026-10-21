import { describe, it, expect } from 'vitest'
import * as evidenceTiers from '@/utils/evidenceTiers'
import {
  TIER_CONFIG,
  getTierConfig,
  getScoreExplanation,
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

describe('evidence-tier vocabulary (#314)', () => {
  // ClinGen/GenCC classification words; a KGDB tier must never read as one of them
  const CLINICAL_TERMS = [
    'Definitive',
    'Strong',
    'Moderate',
    'Limited',
    'Supportive',
    'Disputed',
    'Refuted'
  ]
  const labels = [...Object.values(TIER_CONFIG).map(t => t.label), getTierConfig(null).label]

  it.each(labels)('tier label "%s" uses no ClinGen/GenCC term', label => {
    for (const term of CLINICAL_TERMS) expect(label).not.toContain(term)
  })

  it('has one tier vocabulary: no separate score-range labels', () => {
    expect(evidenceTiers).not.toHaveProperty('SCORE_RANGES')
    expect(evidenceTiers).not.toHaveProperty('getScoreRangeConfig')
  })

  it('explains a score with the backend tier label', () => {
    expect(getScoreExplanation(60, 3, 'multi_source_support')).toBe(
      '60.0% — Multi-Source Support from 3 sources'
    )
  })
})
