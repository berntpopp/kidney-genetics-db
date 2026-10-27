import { describe, it, expect } from 'vitest'
import { mount } from '@vue/test-utils'
import { h } from 'vue'
import { TooltipProvider } from '@/components/ui/tooltip'
import { Chip } from '@/components/shared'
import GenePhenotypes from '@/components/gene/GenePhenotypes.vue'

const render = (hpoData: Record<string, unknown>) =>
  mount({ render: () => h(TooltipProvider, () => h(GenePhenotypes, { hpoData })) })
import { networkAnalysisConfig } from '@/config/networkAnalysis'

const hpo = (clinicalGroup: Record<string, unknown>) => ({
  phenotype_count: 10,
  kidney_phenotype_count: 4,
  disease_count: 2,
  classification: { clinical_group: clinicalGroup }
})

describe('GenePhenotypes clinical group (#338)', () => {
  it('labels neoplasia and shows secondary groups as chips', () => {
    const wrapper = render(
      hpo({
        primary: 'neoplasia',
        secondary: ['glomerulopathy'],
        scores: { neoplasia: 0.543, glomerulopathy: 0.457 }
      })
    )
    const secondary = wrapper.find('[data-testid="clinical-group-secondary"]')
    expect(wrapper.text()).toContain('Neoplasia')
    expect(secondary.text()).toContain('Glomerulopathy')
  })

  it('renders v1 annotations without secondary groups', () => {
    const wrapper = render(hpo({ primary: 'cakut', scores: { cakut: 1 } }))
    expect(wrapper.text()).toContain('CAKUT')
    expect(wrapper.find('[data-testid="clinical-group-secondary"]').exists()).toBe(false)
  })
})

describe('GenePhenotypes score label (#338)', () => {
  const label = (clinicalGroup: Record<string, unknown>) =>
    String(
      render(hpo(clinicalGroup))
        .findAllComponents(Chip)
        .find(c => String(c.props('tooltip')).startsWith('Clinical group'))!
        .props('tooltip')
    )

  it('calls a v2 score a share of kidney-group evidence', () => {
    expect(label({ primary: 'cakut', scores: { cakut: 0.6 }, method: 'hpo-freq-ic-v2' })).toContain(
      'Share of kidney-group evidence: 60%'
    )
  })

  it('does not present a pre-v2 score as a share', () => {
    const text = label({ primary: 'cakut', scores: { cakut: 0.2 } })
    expect(text).toContain('pre-v2')
    expect(text).not.toContain('Share')
  })
})

describe('network clinical-group colours (#338)', () => {
  it('has a neoplasia colour and label distinct from the other groups', () => {
    const { colorSchemes, labels } = networkAnalysisConfig.nodeColoring
    const colours = Object.values(colorSchemes.clinical_group)
    expect(labels.clinical_group.neoplasia).toBe('Neoplasia')
    expect(colorSchemes.clinical_group.neoplasia).toBeDefined()
    expect(new Set(colours).size).toBe(colours.length)
  })
})
