/**
 * PubTator keeps only a retained sample of mention records; the UI must not
 * present that sample (or legacy total_mentions) as a cumulative total (#281).
 */

import { describe, it, expect } from 'vitest'
import { mount } from '@vue/test-utils'
import { h } from 'vue'
import { TooltipProvider } from '@/components/ui/tooltip'
import EvidenceCard from '@/components/evidence/EvidenceCard.vue'

describe('PubTator evidence statistics', () => {
  it('shows unique publications and labels the retained mention sample', () => {
    const mentions = Array.from({ length: 20 }, (_, i) => ({ pmid: String(i), score: 1 }))
    const evidence = {
      source_name: 'PubTator',
      evidence_data: {
        pmids: Array.from({ length: 207 }, (_, i) => String(i)),
        publication_count: 207,
        total_mentions: 21,
        mentions,
        evidence_score: 1
      }
    }
    const wrapper = mount({
      render: () =>
        h(TooltipProvider, () => h(EvidenceCard, { evidence, gene: { approved_symbol: 'PKD1' } }))
    })
    const stats = wrapper.get('[data-testid="evidence-stats"]')

    expect(stats.findAll('li').map(li => li.text())).toEqual([
      '207 publications',
      '20 sampled mentions'
    ])
    expect(stats.findAll('li')[1]!.attributes('title')).toContain('not a total mention count')
    expect(wrapper.text()).not.toContain('21')
    expect(wrapper.text()).not.toMatch(/\d+\s*Mentions/)
  })
})
