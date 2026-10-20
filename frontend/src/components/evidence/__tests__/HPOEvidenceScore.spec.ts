/**
 * HPO evidence must show one unambiguous normalized contribution, not the
 * capped raw phenotype-count heuristic (#278).
 */

import { describe, it, expect } from 'vitest'
import { mount } from '@vue/test-utils'
import { h } from 'vue'
import { Accordion } from '@/components/ui/accordion'
import EvidenceCard from '@/components/evidence/EvidenceCard.vue'

const hpoEvidence = (normalized_score: number | null) => ({
  source_name: 'HPO',
  source_id: 'x',
  normalized_score,
  evidence_data: {
    evidence_score: 100,
    hpo_terms: Array.from({ length: 19 }, (_, i) => `HP:${String(i).padStart(7, '0')}`)
  }
})

const render = (evidence: ReturnType<typeof hpoEvidence>) =>
  mount(() =>
    h(Accordion, { type: 'single', defaultValue: 'HPO' }, () => h(EvidenceCard, { evidence }))
  )

describe('HPO evidence score display', () => {
  it('shows the normalized percentile as a percentage and hides the raw heuristic', () => {
    const wrapper = render(hpoEvidence(0.901))
    const badge = wrapper.find('[title^="Normalized"]')
    expect(badge.text()).toBe('90.1%')
    expect(badge.attributes('title')).toContain('percentile rank')
    expect(wrapper.text()).not.toContain('Evidence Score')
    expect(wrapper.text()).not.toMatch(/\b100\b/)
  })

  it('shows a zero contribution as 0.0% and an unavailable one not at all', () => {
    expect(render(hpoEvidence(0)).find('[title^="Normalized"]').text()).toBe('0.0%')
    expect(render(hpoEvidence(null)).find('[title^="Normalized"]').exists()).toBe(false)
  })
})
