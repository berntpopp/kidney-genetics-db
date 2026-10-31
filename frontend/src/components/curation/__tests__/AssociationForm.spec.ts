import { describe, it, expect, afterEach } from 'vitest'
import { flushPromises, mount, type VueWrapper } from '@vue/test-utils'
import AssociationForm from '@/components/curation/AssociationForm.vue'
import type { Diagnostics } from '@/api/curation'

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
      evidence_summary: null,
      relationship_type: 'mendelian',
      moi: null,
      methodology: null,
      methodology_version: null,
      source: 'kgdb',
      external_id: null,
      external_url: null,
      external_curator: null,
      external_reviewer: null,
      scores: null,
      diagnostics: null
    })
  })

  it('offers only susceptibility strengths for a susceptibility record and resets a misfit', async () => {
    wrapper = mount(AssociationForm, { attachTo: document.body })
    await wrapper.find('#gda-evidence_strength').setValue('Strong')
    await wrapper.find('#gda-relationship_type').setValue('susceptibility')
    await flushPromises()
    const options = wrapper
      .findAll('#gda-evidence_strength option')
      .map(o => o.text())
      .filter(t => t !== 'Select…')
    expect(options).toEqual([
      'Established association',
      'Likely association',
      'Uncertain association',
      'Refuted association'
    ])
    expect(wrapper.find('#gda-evidence_strength').element).toHaveProperty('value', '')
  })

  it('requires an external ID and http(s) URL for a Gene Curator record', async () => {
    wrapper = mount(AssociationForm, { attachTo: document.body })
    for (const [field, value] of Object.entries(VALID)) {
      await wrapper.find(`#gda-${field}`).setValue(value)
    }
    await wrapper.find('#gda-source').setValue('gene_curator')
    await flushPromises()
    await wrapper.find('#gda-external_url').setValue('javascript:alert(1)')
    await wrapper.find('form').trigger('submit')
    await new Promise(resolve => setTimeout(resolve, 10))
    await flushPromises()
    expect(wrapper.find('#gda-external_id-error').text()).toContain('required')
    expect(wrapper.find('#gda-external_url-error').text()).toContain('http')
    expect(wrapper.emitted('save')).toBeUndefined()
  })

  it('emits MOI, provenance, points and a resource row', async () => {
    wrapper = mount(AssociationForm, { attachTo: document.body })
    for (const [field, value] of Object.entries(VALID)) {
      await wrapper.find(`#gda-${field}`).setValue(value)
    }
    await wrapper.find('#gda-moi').setValue('HP:0000007')
    await wrapper.find('#gda-methodology').setValue('Kidney Gene Curation')
    await wrapper.find('#gda-methodology_version').setValue('draft iteration 3')
    await wrapper.find('#gda-score_total').setValue('12')
    await wrapper.find('[data-testid="add-resource"]').trigger('click')
    await wrapper.find('#gda-res-0-name').setValue('Example group')
    await wrapper.find('#gda-res-0-url').setValue('https://example.org/group')
    await wrapper.find('#gda-res-0-date').setValue('2026-10-30')
    await wrapper.find('form').trigger('submit')
    await new Promise(resolve => setTimeout(resolve, 10))
    await flushPromises()
    const saved = wrapper.emitted('save')?.[0]?.[0] as Record<string, unknown>
    expect(saved.moi).toBe('HP:0000007')
    expect(saved.methodology_version).toBe('draft iteration 3')
    expect(saved.scores).toEqual({ genetic: null, experimental: null, total: 12 })
    expect(saved.diagnostics).toEqual({
      recommended_transcript: null,
      detectability: [],
      detectability_note: null,
      resources: [
        {
          type: 'patient_organisation',
          name: 'Example group',
          url: 'https://example.org/group',
          language: null,
          country_or_scope: null,
          audiences: [],
          maintainer: null,
          conflict_of_interest: null,
          verified: { method: 'fetched', date: '2026-10-30' }
        }
      ]
    })
  })

  it('blocks saving a resource row without a valid link', async () => {
    wrapper = mount(AssociationForm, { attachTo: document.body })
    for (const [field, value] of Object.entries(VALID)) {
      await wrapper.find(`#gda-${field}`).setValue(value)
    }
    await wrapper.find('[data-testid="add-resource"]').trigger('click')
    await wrapper.find('#gda-res-0-name').setValue('Example group')
    await wrapper.find('#gda-res-0-url').setValue('example.org')
    await wrapper.find('form').trigger('submit')
    await new Promise(resolve => setTimeout(resolve, 10))
    await flushPromises()
    expect(wrapper.find('#gda-res-0-error').text()).toContain('http')
    expect(wrapper.emitted('save')).toBeUndefined()
  })

  it('asks for a new verification date when a verified link is changed', async () => {
    const record = {
      id: 1,
      gene_symbol: 'MUC1',
      disease_id: 'MONDO:0005300',
      disease_name: 'ADTKD',
      relationship_type: 'mendelian',
      evidence_strength: 'Definitive',
      citations: ['PMID:1'],
      evidence_summary: null,
      source: 'kgdb',
      diagnostics: {
        recommended_transcript: null,
        detectability: [],
        resources: [
          {
            type: 'patient_organisation',
            name: 'Group',
            url: 'https://example.org/old',
            language: null,
            audiences: [],
            maintainer: null,
            conflict_of_interest: null,
            verified: { method: 'fetched', date: '2026-09-01' }
          }
        ]
      }
    }
    wrapper = mount(AssociationForm, {
      props: { record: record as never },
      attachTo: document.body
    })
    await flushPromises()
    await wrapper.find('#gda-res-0-url').setValue('https://example.org/new')
    await wrapper.find('form').trigger('submit')
    await new Promise(resolve => setTimeout(resolve, 10))
    await flushPromises()
    expect(wrapper.find('#gda-res-0-error').text()).toContain('new verification date')
    expect(wrapper.emitted('save')).toBeUndefined()
    await wrapper.find('#gda-res-0-date').setValue('2026-10-30')
    await wrapper.find('form').trigger('submit')
    await new Promise(resolve => setTimeout(resolve, 10))
    await flushPromises()
    expect(wrapper.emitted('save')).toHaveLength(1)
  })

  it('pre-fills diagnostics rows when editing and labels every input', async () => {
    const record = {
      id: 1,
      gene_symbol: 'MUC1',
      disease_id: 'MONDO:0005300',
      disease_name: 'ADTKD',
      relationship_type: 'mendelian',
      evidence_strength: 'Definitive',
      citations: ['PMID:1'],
      evidence_summary: null,
      moi: 'HP:0000006',
      source: 'kgdb',
      diagnostics: {
        recommended_transcript: null,
        detectability: [
          {
            challenge: 'VNTR',
            share_of_variants: null,
            affected_variants: null,
            methods: [],
            tools: [],
            negative_report_does_not_exclude: true,
            sources: []
          }
        ],
        detectability_note: 'CNV calling advised',
        resources: []
      }
    }
    wrapper = mount(AssociationForm, {
      props: { record: record as never },
      attachTo: document.body
    })
    await flushPromises()
    expect(wrapper.find('#gda-det-0-challenge').element).toHaveProperty('value', 'VNTR')
    expect(wrapper.find('#gda-det-note').element).toHaveProperty('value', 'CNV calling advised')
    expect(wrapper.find('#gda-det-0-negative').element).toHaveProperty('checked', true)
    for (const el of wrapper.findAll('input, select, textarea')) {
      const id = el.attributes('id')
      expect(id, el.html()).toBeTruthy()
      expect(wrapper.find(`label[for="${id}"]`).exists(), id).toBe(true)
    }
  })

  it('emits the transcript verified-via, detectability note and resource scope', async () => {
    wrapper = mount(AssociationForm, { attachTo: document.body })
    for (const [field, value] of Object.entries(VALID)) {
      await wrapper.find(`#gda-${field}`).setValue(value)
    }
    await wrapper.find('#gda-tx-mane').setValue('select')
    await wrapper.find('#gda-tx-verified_via').setValue('MANE v1.4 summary')
    await wrapper.find('#gda-det-note').setValue('standard short-read testing adequate')
    await wrapper.find('[data-testid="add-resource"]').trigger('click')
    await wrapper.find('#gda-res-0-name').setValue('Example group')
    await wrapper.find('#gda-res-0-url').setValue('https://example.org/group')
    await wrapper.find('#gda-res-0-country').setValue('Germany')
    await wrapper.find('#gda-res-0-date').setValue('2026-10-30')
    await wrapper.find('form').trigger('submit')
    await new Promise(resolve => setTimeout(resolve, 10))
    await flushPromises()
    const d = (wrapper.emitted('save')?.[0]?.[0] as { diagnostics: Diagnostics }).diagnostics
    expect(d.recommended_transcript?.verified_via).toBe('MANE v1.4 summary')
    expect(d.detectability_note).toBe('standard short-read testing adequate')
    expect(d.resources[0]?.country_or_scope).toBe('Germany')
  })
})
