/**
 * GenCC evidence shows only the scored (two-stage) normalized contribution,
 * not the pipeline's raw MAX evidence_score (#330).
 */

import { describe, it, expect } from 'vitest'
import { mount } from '@vue/test-utils'
import { h } from 'vue'
import { Accordion } from '@/components/ui/accordion'
import EvidenceCard from '@/components/evidence/EvidenceCard.vue'

const evidence = (source_name: string) => ({
  source_name,
  source_id: 'x',
  normalized_score: 0.7,
  evidence_data: {
    evidence_score: 0.8,
    classifications: ['Strong', 'Limited'],
    submissions: [
      { classification: 'Strong', submitter: 'Ambry Genetics' },
      { classification: 'Limited', submitter: 'G2P' }
    ]
  }
})

const render = (source: string) =>
  mount(() =>
    h(Accordion, { type: 'single', defaultValue: source }, () =>
      h(EvidenceCard, { evidence: evidence(source) })
    )
  )

describe('GenCC evidence score display', () => {
  it('shows the adjusted normalized score and hides the raw MAX score', () => {
    const wrapper = render('GenCC')
    const badge = wrapper.find('[title^="Normalized"]')
    expect(badge.text()).toBe('70.0%')
    expect(badge.attributes('title')).toContain(
      'strongest classification, adjusted for agreeing and conflicting submitters'
    )
    expect(wrapper.text()).not.toContain('Weighted Evidence Score')
    expect(wrapper.text()).not.toContain('0.80')
  })

  it('keeps the ClinGen tooltip as a classification weight', () => {
    const badge = render('ClinGen').find('[title^="Normalized"]')
    expect(badge.attributes('title')).toBe('Normalized score: classification weight (0–100%)')
  })
})
