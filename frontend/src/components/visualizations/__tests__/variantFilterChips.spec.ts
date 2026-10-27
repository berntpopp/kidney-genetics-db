/**
 * Variant filters on /genes/:symbol/structure: one shared component for both plots, real
 * toggle buttons at a usable size, and clinical-significance colours shared with the ClinVar
 * chips on the gene page (struct-filter-chips-tiny, struct-colors-hex, #320).
 */
import { describe, it, expect } from 'vitest'
import { mount } from '@vue/test-utils'
import structureSrc from '../GeneStructureVisualization.vue?raw'
import domainSrc from '../ProteinDomainVisualization.vue?raw'
import clinvarSrc from '@/components/gene/ClinVarVariants.vue?raw'
import VariantFilters from '@/components/gene/VariantFilters.vue'
import { SIGNIFICANCE, significanceColor } from '@/components/gene/variantColors'

describe.each([
  ['GeneStructureVisualization', structureSrc],
  ['ProteinDomainVisualization', domainSrc]
])('%s', (_name, src) => {
  it('uses the shared VariantFilters and token colours only', () => {
    expect(src).toContain('<VariantFilters')
    expect(src).toContain('significanceColor')
    expect(src).not.toMatch(/#[0-9a-fA-F]{6}\b/)
  })
})

describe('VariantFilters', () => {
  it('toggles values with aria-pressed buttons and offers All / None', async () => {
    const wrapper = mount(VariantFilters, {
      props: {
        classifications: ['pathogenic'],
        'onUpdate:classifications': (v: string[]) => wrapper.setProps({ classifications: v }),
        effects: []
      }
    })
    const group = () => wrapper.get('[aria-label="Classification filter"]')
    const vus = () =>
      group()
        .findAll('button')
        .find(b => b.text() === 'VUS')!
    expect(vus().attributes('aria-pressed')).toBe('false')
    expect(vus().classes()).toContain('h-7')
    await vus().trigger('click')
    expect(vus().attributes('aria-pressed')).toBe('true')

    await group()
      .findAll('button')
      .find(b => b.text() === 'None')!
      .trigger('click')
    expect(wrapper.props('classifications')).toEqual([])
    await group()
      .findAll('button')
      .find(b => b.text() === 'All')!
      .trigger('click')
    expect(wrapper.props('classifications')).toEqual(Object.keys(SIGNIFICANCE))
  })
})

describe('clinical significance colours', () => {
  it('are status tones, not the strength ramp, and shared with the ClinVar chips', () => {
    expect(SIGNIFICANCE.pathogenic!.tone).toBe('danger')
    expect(SIGNIFICANCE.vus!.tone).toBe('warning')
    expect(SIGNIFICANCE.benign!.tone).toBe('neutral')
    for (const c of Object.values(SIGNIFICANCE)) expect(c.color).not.toContain('strength')
    expect(significanceColor('unknown')).toContain('--muted-foreground')
    expect(clinvarSrc).toContain('SIGNIFICANCE')
  })
})
