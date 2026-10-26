import { describe, it, expect } from 'vitest'
import { mount } from '@vue/test-utils'
import MondoDiseases from '@/components/gene/MondoDiseases.vue'
import type { MondoAnnotation } from '@/types/mondo'

const data: MondoAnnotation = {
  mondo_diseases: [
    {
      mondo_id: 'MONDO:0008263',
      label: 'polycystic kidney disease 1',
      source_ids: ['OMIM:173900'],
      sources: ['GenCC', 'HPO']
    }
  ],
  mapped_count: 1,
  unmapped: [{ source_id: 'OMIM:999999', sources: ['HPO'], reason: 'no exactMatch' }],
  unmapped_count: 1,
  ambiguous: [],
  ambiguous_count: 0,
  provenance: {
    mondo_release: '2026-10-06',
    sssom_url: 'https://example.invalid/mondo.sssom.tsv',
    sssom_sha256: 'x',
    predicate: 'skos:exactMatch',
    license: 'CC BY 4.0'
  }
}

const mountWith = (mondo?: MondoAnnotation) =>
  mount(MondoDiseases, {
    props: { annotations: { annotations: mondo ? { mondo: [{ data: mondo }] } : {} } }
  })

describe('MondoDiseases (#28)', () => {
  it('renders mapped MONDO rows, source IDs, unmapped count and CC BY attribution', () => {
    const wrapper = mountWith(data)
    expect(wrapper.find('h2').text()).toBe('MONDO Diseases')
    const link = wrapper.find('a[href="https://monarchinitiative.org/MONDO:0008263"]')
    expect(link.text()).toBe('MONDO:0008263')
    expect(wrapper.text()).toContain('polycystic kidney disease 1')
    expect(wrapper.text()).toContain('OMIM:173900')
    expect(wrapper.text()).toContain('1 without an exact match')
    const attribution = wrapper.find('[data-testid="mondo-attribution"]').text()
    expect(attribution).toContain('2026-10-06')
    expect(attribution).toContain('CC BY 4.0')
  })

  it('is hidden without a MONDO annotation or without mapped diseases', () => {
    expect(mountWith().find('h2').exists()).toBe(false)
    expect(
      mountWith({ ...data, mondo_diseases: [] })
        .find('h2')
        .exists()
    ).toBe(false)
  })
})
