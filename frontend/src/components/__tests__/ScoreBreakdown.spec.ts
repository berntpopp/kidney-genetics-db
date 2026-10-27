import { describe, it, expect } from 'vitest'
import { mount } from '@vue/test-utils'
import { h } from 'vue'
import { TooltipProvider } from '@/components/ui/tooltip'
import { Chip } from '@/components/shared'
import ScoreBreakdown from '@/components/ScoreBreakdown.vue'

const card = (props: Record<string, unknown>) =>
  mount({
    render: () => h(TooltipProvider, () => h(ScoreBreakdown, { variant: 'card', ...props }))
  })

describe('ScoreBreakdown', () => {
  it('renders real numeric per-source contributions with one format', () => {
    const wrapper = card({ score: 72.5, breakdown: { ClinGen: 0.8, HPO: 0.901 } })
    expect(wrapper.text()).toContain('72.5')
    expect(wrapper.text()).toContain('HPO 90.1%')
    expect(wrapper.text()).toContain('ClinGen 80.0%')
  })

  it('spells out source names on the gene detail card (#329)', () => {
    const wrapper = card({ score: 60, breakdown: { DiagnosticPanels: 0.5, PubTator: 0.4 } })
    expect(wrapper.text()).toContain('Diagnostic panels 50.0%')
    expect(wrapper.text()).toContain('PubTator3 40.0%')
    expect(wrapper.text()).not.toMatch(/\b(DI|PT)\b/)
  })

  it('never renders non-numeric breakdown values as percentages (#301)', () => {
    const wrapper = card({ score: 50, breakdown: { ClinGen: true, GenCC: null } })
    expect(wrapper.text()).toContain('50.0')
    expect(wrapper.text()).not.toContain('ClinGen')
    expect(wrapper.text()).not.toContain('100')
  })

  it('labels the score with the backend evidence tier (#314)', () => {
    // A 60% score is "Strong" in the old score ranges but multi_source_support in the API
    const wrapper = card({ score: 60, tier: 'multi_source_support' })
    expect(wrapper.text()).toContain('Multi-Source Support')
    expect(wrapper.text()).not.toContain('Strong')
  })

  it('labels low scores as Minimal Evidence, never as a ClinGen term (#314)', () => {
    // CPLX1: evidence_score 0.0093, API evidence_tier minimal_evidence
    const wrapper = card({ score: 0.0093, tier: 'minimal_evidence', breakdown: { HPO: 0.0007 } })
    expect(wrapper.text()).toContain('Minimal Evidence')
    expect(wrapper.text()).not.toContain('Disputed')
  })

  it('describes ClinGen/GenCC sub-scores as scores, not classification words (#314)', () => {
    // A ClinGen "Disputed" classification scores 0.2; it must not read as "Moderate"
    const chips = card({ score: 40, breakdown: { ClinGen: 0.2, GenCC: 0.9 } })
      .findAllComponents(Chip)
      .filter(c => c.props('kind') === 'neutral')
    const tips = chips.map(c => String(c.props('tooltip'))).join(' ')
    expect(tips).toContain('Evidence score: 20.0%')
    expect(tips).toContain('Evidence score: 90.0%')
    for (const term of ['Definitive', 'Strong', 'Moderate', 'clinical validity', 'association']) {
      expect(tips).not.toContain(term)
    }
  })
})
