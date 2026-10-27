/**
 * GenCC evidence shows only the scored (two-stage) normalized contribution,
 * not the pipeline's raw MAX evidence_score (#330).
 */

import { describe, it, expect } from 'vitest'
import { mount } from '@vue/test-utils'
import { h } from 'vue'
import { TooltipProvider } from '@/components/ui/tooltip'
import { Chip } from '@/components/shared'
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

const scoreChip = (source: string) =>
  mount({ render: () => h(TooltipProvider, () => h(EvidenceCard, { evidence: evidence(source) })) })
    .findAllComponents(Chip)
    .find(c => String(c.props('label')).startsWith('Score'))!

describe('GenCC evidence score display', () => {
  it('shows the adjusted normalized score and hides the raw MAX score', () => {
    const chip = scoreChip('GenCC')
    expect(chip.text()).toBe('Score 70.0%')
    expect(chip.props('tooltip')).toContain(
      'strongest classification, adjusted for agreeing and conflicting submitters'
    )
    expect(chip.props('kind')).toBe('neutral')
  })

  it('keeps the ClinGen tooltip as a classification weight', () => {
    expect(scoreChip('ClinGen').props('tooltip')).toBe(
      'Source score (0–100%): weight of the strongest classification'
    )
  })
})
