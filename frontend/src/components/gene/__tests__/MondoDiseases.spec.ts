import { describe, it, expect } from 'vitest'
import { mount } from '@vue/test-utils'
import { h } from 'vue'
import { TooltipProvider } from '@/components/ui/tooltip'
import MondoDiseases from '@/components/gene/MondoDiseases.vue'
import type { MondoAnnotation } from '@/types/mondo'
// HNF1B MONDO annotation as served by https://kidney-genetics.org/api (read-only, 2026-10-27)
import hnf1b from './fixtures/mondo-HNF1B.json'

const mountWith = (mondo?: MondoAnnotation, props: Record<string, unknown> = {}) =>
  mount({
    render: () =>
      h(TooltipProvider, () =>
        h(MondoDiseases, {
          annotations: { annotations: mondo ? { mondo: [{ data: mondo }] } : {} },
          ...props
        })
      )
  })

describe('MondoDiseases (#28)', () => {
  it('lists HNF1B diseases name first, sorted by name, with linked MONDO IDs', () => {
    const wrapper = mountWith(hnf1b as MondoAnnotation)
    expect(wrapper.find('h2').text()).toBe('Diseases (MONDO)')
    const rows = wrapper.findAll('[data-testid="mondo-list"] > li')
    expect(rows).toHaveLength(9)

    const names = rows.map(r => r.find('[data-slot="ontology-term"] span').text())
    expect(names).toEqual([...names].sort((a, b) => a.localeCompare(b)))
    expect(names[0]).toBe('chromosome 17q12 deletion syndrome')

    const rcad = rows.find(r => r.text().includes('renal cysts and diabetes syndrome'))!
    const term = rcad.find('a[href="https://monarchinitiative.org/MONDO:0007669"]')
    expect(term.text()).toBe('renal cysts and diabetes syndromeMONDO:0007669')
    expect(term.find('.font-mono').text()).toBe('MONDO:0007669')
  })

  it('deduplicates source IDs, drops the term itself and links each one', () => {
    const wrapper = mountWith(hnf1b as MondoAnnotation)
    const rcad = wrapper
      .findAll('[data-testid="mondo-list"] > li')
      .find(r => r.text().includes('renal cysts and diabetes syndrome'))!
    const sourceLinks = rcad.findAll('p a').map(a => a.attributes('href'))
    // ORPHA:93111 and Orphanet:93111 are one ID; MONDO:0007669 is the term itself
    expect(sourceLinks).toEqual([
      'https://omim.org/entry/137920',
      'https://www.orpha.net/en/disease/detail/93111'
    ])
    expect(rcad.find('p').text()).not.toContain('MONDO:0007669')
    expect(rcad.findAll('[data-slot="chip"]').map(c => c.text())).toEqual([
      'ClinGen',
      'GenCC',
      'HPO'
    ])
  })

  it('keeps the licence footnote as a quiet caption', () => {
    const attribution = mountWith(hnf1b as MondoAnnotation).find(
      '[data-testid="mondo-attribution"]'
    )
    expect(attribution.classes()).toContain('text-xs')
    expect(attribution.text()).toContain('2026-10-06')
    expect(attribution.text()).toContain('CC BY 4.0')
  })

  it('shows one quiet line instead of a card when a gene has no mapping', () => {
    const empty = mountWith()
    expect(empty.find('[data-testid="mondo-empty"]').text()).toBe(
      'Diseases (MONDO): no mappings for this gene.'
    )
    expect(empty.find('h2').exists()).toBe(false)
    expect(empty.text()).not.toContain('mapped to the MONDO Disease Ontology')
  })

  it('shows a failed load as an error', () => {
    const failed = mountWith(undefined, { error: new Error('offline') })
    expect(failed.find('[data-state="error"]').text()).toContain('Could not load disease mappings')
  })
})
