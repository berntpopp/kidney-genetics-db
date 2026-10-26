import { describe, it, expect, afterEach } from 'vitest'
import { flushPromises, mount, type VueWrapper } from '@vue/test-utils'
import AssociationForm from '@/components/curation/AssociationForm.vue'

let wrapper: VueWrapper | null = null
afterEach(() => wrapper?.unmount())

async function submit(values: Record<string, string>) {
  wrapper = mount(AssociationForm, { attachTo: document.body })
  for (const [field, value] of Object.entries(values)) {
    await wrapper.find(`#gda-${field}`).setValue(value)
  }
  await wrapper.find('form').trigger('submit')
  // vee-validate validates asynchronously before calling the submit handler
  await new Promise(resolve => setTimeout(resolve, 10))
  await flushPromises()
  return wrapper
}

const VALID = {
  gene_symbol: 'PKD1',
  disease_id: 'mondo:0005300',
  disease_name: 'chronic kidney disease',
  evidence_strength: 'Strong',
  citations: '12345678, PMID:23456789'
}

describe('AssociationForm', () => {
  it('flags an HPO id as a phenotype, marks fields invalid and focuses the first', async () => {
    const w = await submit({ disease_id: 'HP:0000083' })
    const gene = w.find('#gda-gene_symbol')
    expect(gene.attributes('aria-invalid')).toBe('true')
    expect(gene.attributes('aria-describedby')).toBe('gda-gene_symbol-error')
    expect(document.activeElement?.id).toBe('gda-gene_symbol')
    expect(w.find('#gda-disease_id-error').text()).toContain('phenotypes')
    expect(w.find('#gda-citations-error').exists()).toBe(true)
    expect(w.emitted('save')).toBeUndefined()
  })

  it('rejects malformed PMIDs', async () => {
    const w = await submit({ ...VALID, citations: 'doi:10.1/x' })
    expect(w.find('#gda-citations-error').text()).toContain('PMID')
    expect(w.emitted('save')).toBeUndefined()
  })

  it('emits normalised input when valid', async () => {
    const w = await submit(VALID)
    expect(w.emitted('save')?.[0]?.[0]).toEqual({
      gene_symbol: 'PKD1',
      disease_id: 'MONDO:0005300',
      disease_name: 'chronic kidney disease',
      evidence_strength: 'Strong',
      citations: ['12345678', 'PMID:23456789'],
      evidence_summary: null
    })
  })
})
