import { describe, it, expect } from 'vitest'
import { mount } from '@vue/test-utils'
import ScoreBreakdown from '@/components/ScoreBreakdown.vue'

describe('ScoreBreakdown', () => {
  it('renders real numeric per-source contributions', () => {
    const wrapper = mount(ScoreBreakdown, {
      props: { score: 72.5, breakdown: { ClinGen: 0.8, HPO: 0.901 }, variant: 'card' }
    })
    expect(wrapper.text()).toContain('72.5')
    expect(wrapper.text()).toContain('HPO: 90')
    expect(wrapper.text()).toContain('CG: 80')
  })

  it('never renders non-numeric breakdown values as percentages (#301)', () => {
    const wrapper = mount(ScoreBreakdown, {
      props: { score: 50, breakdown: { ClinGen: true, GenCC: null }, variant: 'card' }
    })
    expect(wrapper.text()).toContain('50.0')
    expect(wrapper.text()).not.toContain('CG')
    expect(wrapper.text()).not.toContain('100')
  })

  it('labels low scores from SCORE_RANGES, never as a ClinGen term (#314)', () => {
    // CPLX1: evidence_score 0.0093, API evidence_tier minimal_evidence
    const wrapper = mount(ScoreBreakdown, {
      props: { score: 0.0093, breakdown: { HPO: 0.0007 }, variant: 'card' }
    })
    expect(wrapper.text()).toContain('Minimal')
    expect(wrapper.text()).not.toContain('Disputed')
  })

  it('uses the SCORE_RANGES label for high scores (#314)', () => {
    const wrapper = mount(ScoreBreakdown, { props: { score: 96, variant: 'card' } })
    expect(wrapper.text()).toContain('Exceptional')
    expect(wrapper.text()).not.toContain('Definitive')
  })
})
