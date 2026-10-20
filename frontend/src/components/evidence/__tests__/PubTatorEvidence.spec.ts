/**
 * PubTator keeps only a retained sample of mention records; the UI must not
 * present that sample (or legacy total_mentions) as a cumulative total (#281).
 */

import { describe, it, expect } from 'vitest'
import { mount } from '@vue/test-utils'
import PubTatorEvidence from '@/components/evidence/PubTatorEvidence.vue'

describe('PubTatorEvidence statistics', () => {
  it('shows unique publications and labels the retained mention sample', () => {
    const mentions = Array.from({ length: 20 }, (_, i) => ({ pmid: String(i), score: 1 }))
    const wrapper = mount(PubTatorEvidence, {
      props: {
        evidenceData: {
          pmids: Array.from({ length: 207 }, (_, i) => String(i)),
          publication_count: 207,
          total_mentions: 21,
          mentions,
          evidence_score: 1
        }
      }
    })
    const text = wrapper.text()

    expect(text).toContain('207')
    expect(text).toContain('Publications')
    expect(text).toContain('20Sampled mentions')
    expect(text).not.toContain('21')
    expect(text).not.toMatch(/\d+\s*Mentions/)
  })
})
