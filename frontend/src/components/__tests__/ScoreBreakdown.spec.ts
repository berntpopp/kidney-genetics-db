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
})
