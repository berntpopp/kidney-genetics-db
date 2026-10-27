/**
 * HPO evidence must show one unambiguous normalized contribution, not the
 * capped raw phenotype-count heuristic (#278), and name its terms.
 */

import { describe, it, expect } from 'vitest'
import { flushPromises, mount } from '@vue/test-utils'
import { h } from 'vue'
import { TooltipProvider } from '@/components/ui/tooltip'
import { Chip } from '@/components/shared'
import EvidenceCard from '@/components/evidence/EvidenceCard.vue'
import type { HPOTermEntry } from '@/types/evidence'

const hpoEvidence = (normalized_score: number | null) => ({
  source_name: 'HPO',
  source_id: 'x',
  normalized_score,
  evidence_data: {
    evidence_score: 100,
    hpo_terms: Array.from(
      { length: 19 },
      (_, i) => `HP:${String(i).padStart(7, '0')}`
    ) as HPOTermEntry[]
  }
})

const render = (evidence: ReturnType<typeof hpoEvidence>, context = {}) =>
  mount(
    { render: () => h(TooltipProvider, () => h(EvidenceCard, { evidence, context })) },
    { attachTo: document.body }
  )

const scoreChip = (evidence: ReturnType<typeof hpoEvidence>) =>
  render(evidence)
    .findAllComponents(Chip)
    .find(c => String(c.props('label')).startsWith('Score'))

describe('HPO evidence score display', () => {
  it('shows the normalized percentile as a percentage and hides the raw heuristic', () => {
    const wrapper = render(hpoEvidence(0.901))
    const chip = wrapper
      .findAllComponents(Chip)
      .find(c => String(c.props('label')).startsWith('Score'))!
    expect(chip.text()).toBe('Score 90.1%')
    expect(chip.props('tooltip')).toContain('percentile rank')
    expect(wrapper.text()).not.toContain('Evidence Score')
    expect(wrapper.text()).not.toMatch(/\b100\b/)
    expect(wrapper.get('[data-testid="evidence-stats"]').text()).toBe('19 phenotype terms')
    wrapper.unmount()
  })

  it('shows a zero contribution as 0.0% and an unavailable one not at all', () => {
    expect(scoreChip(hpoEvidence(0))!.text()).toBe('Score 0.0%')
    expect(scoreChip(hpoEvidence(null))).toBeUndefined()
  })
})

describe('HPO evidence terms', () => {
  it('renders term names from the evidence, name first, sorted, linked to HPO (#421)', async () => {
    const evidence = hpoEvidence(0.5)
    evidence.evidence_data.hpo_terms = [
      { id: 'HP:0000107', name: 'Renal cyst' },
      { id: 'HP:0000003', name: 'Multicystic kidney dysplasia' },
      'HP:0000083' // legacy bare-ID entry
    ]
    const wrapper = render(evidence)
    expect(wrapper.get('[data-testid="evidence-summary"]').text()).toBe(
      'Multicystic kidney dysplasia, Renal cyst and 1 more term'
    )
    await wrapper.get('button[aria-expanded]').trigger('click')
    await flushPromises()

    const terms = wrapper.findAll('[data-slot="ontology-term"]')
    expect(terms.map(t => t.text())).toEqual([
      'Multicystic kidney dysplasiaHP:0000003',
      'Renal cystHP:0000107',
      // a term without a loaded name keeps its linked ID, sorted last
      'HP:0000083'
    ])
    expect(terms[1]!.attributes('href')).toBe('https://hpo.jax.org/browse/term/HP:0000107')
    expect(terms[1]!.find('.font-mono').classes()).toContain('text-muted-foreground')
    wrapper.unmount()
  })
})
