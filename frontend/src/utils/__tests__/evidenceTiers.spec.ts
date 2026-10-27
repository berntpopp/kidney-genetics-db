import { describe, it, expect } from 'vitest'
import * as evidenceTiers from '@/utils/evidenceTiers'
import {
  TIER_CONFIG,
  getTierConfig,
  getScoreExplanation,
  getClassificationConfig,
  tintedChipStyle
} from '@/utils/evidenceTiers'

describe('getClassificationConfig', () => {
  it.each([
    ['Definitive', 5],
    ['Strong', 4],
    ['moderate', 3],
    ['Limited', 2],
    ['Supportive', 2],
    ['No Known Disease Relationship', 1],
    ['animal_model_only', 1]
  ])('%s maps to strength %i', (label, strength) => {
    const c = getClassificationConfig(label)
    expect(c.strength).toBe(strength)
    expect(c.color).toBe(`var(--strength-${strength})`)
    expect(c.description).not.toBe('')
  })

  it('treats Disputed and Refuted as warning and danger, not strengths', () => {
    expect(getClassificationConfig('Disputed Evidence')).toMatchObject({
      strength: null,
      tone: 'warning',
      label: 'Disputed'
    })
    expect(getClassificationConfig('Refuted')).toMatchObject({ strength: null, tone: 'danger' })
  })

  it('renders unknown labels neutral and keeps the label', () => {
    expect(getClassificationConfig('Something else')).toMatchObject({
      tone: 'neutral',
      label: 'Something else'
    })
    expect(getClassificationConfig(null).label).toBe('No Classification')
  })
})

describe('tintedChipStyle (#320)', () => {
  it('keeps the tint but never uses the raw 500-shade as text color', () => {
    for (const { color } of Object.values(TIER_CONFIG)) {
      const style = tintedChipStyle(color)
      expect(style.backgroundColor).toBe(`color-mix(in srgb, ${color} 12.5%, transparent)`)
      expect(style.borderColor).toBe(`color-mix(in srgb, ${color} 25%, transparent)`)
      expect(style.color).not.toBe(color)
      expect(style.color).toBe(`color-mix(in oklab, ${color} 45%, var(--foreground))`)
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
