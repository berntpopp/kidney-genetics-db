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
    expect(wrapper.text()).toContain('ClinGen: 80')
  })

  it('spells out source names on the gene detail card (#329)', () => {
    const wrapper = mount(ScoreBreakdown, {
      props: { score: 60, breakdown: { DiagnosticPanels: 0.5, PubTator: 0.4 }, variant: 'card' }
    })
    expect(wrapper.text()).toContain('Diagnostic Panels: 50')
    expect(wrapper.text()).toContain('PubTator3: 40')
    expect(wrapper.text()).not.toMatch(/\b(DI|PT): /)
  })

  it('never renders non-numeric breakdown values as percentages (#301)', () => {
    const wrapper = mount(ScoreBreakdown, {
      props: { score: 50, breakdown: { ClinGen: true, GenCC: null }, variant: 'card' }
    })
    expect(wrapper.text()).toContain('50.0')
    expect(wrapper.text()).not.toContain('CG')
    expect(wrapper.text()).not.toContain('100')
  })

  it('labels the score with the backend evidence tier (#314)', () => {
    // A 60% score is "Strong" in the old score ranges but multi_source_support in the API
    const wrapper = mount(ScoreBreakdown, {
      props: { score: 60, tier: 'multi_source_support', variant: 'card' }
    })
    expect(wrapper.text()).toContain('Multi-Source Support')
    expect(wrapper.text()).not.toContain('Strong')
  })

  it('labels low scores as Minimal Evidence, never as a ClinGen term (#314)', () => {
    // CPLX1: evidence_score 0.0093, API evidence_tier minimal_evidence
    const wrapper = mount(ScoreBreakdown, {
      props: {
        score: 0.0093,
        tier: 'minimal_evidence',
        breakdown: { HPO: 0.0007 },
        variant: 'card'
      }
    })
    expect(wrapper.text()).toContain('Minimal Evidence')
    expect(wrapper.text()).not.toContain('Disputed')
  })

  it('describes ClinGen/GenCC sub-scores as scores, not classification words (#314)', () => {
    // A ClinGen "Disputed" classification scores 0.2; it must not read as "Moderate"
    const wrapper = mount(ScoreBreakdown, {
      props: { score: 40, breakdown: { ClinGen: 0.2, GenCC: 0.9 }, variant: 'card' },
      global: {
        stubs: { HoverPopover: { template: '<div><slot /><slot name="content" /></div>' } }
      }
    })
    const text = wrapper.text()
    expect(text).toContain('Evidence score: 20.0%')
    expect(text).toContain('Evidence score: 90.0%')
    for (const term of ['Definitive', 'Strong', 'Moderate', 'clinical validity', 'association']) {
      expect(text).not.toContain(term)
    }
  })
})
