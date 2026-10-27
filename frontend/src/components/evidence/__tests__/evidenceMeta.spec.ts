import { describe, it, expect } from 'vitest'
import { flushPromises, mount } from '@vue/test-utils'
import { h } from 'vue'
import { TooltipProvider } from '@/components/ui/tooltip'
import EvidenceCard from '@/components/evidence/EvidenceCard.vue'
import {
  evidenceMeta,
  formatInheritance,
  parsePanelAppPhenotypes,
  strongestClassification
} from '@/components/evidence/evidenceMeta'

const gene = { approved_symbol: 'HNF1B', hgnc_id: 'HGNC:11630' }

describe('evidence card summaries', () => {
  it('builds the GenCC summary from structured fields, without repeating classifications', () => {
    const meta = evidenceMeta(
      'GenCC',
      {
        classifications: ['Definitive', 'Strong', 'Supportive'],
        diseases: ['renal cysts and diabetes syndrome', 'medullary sponge kidney'],
        submitters: ['ClinGen', 'Orphanet'],
        submissions: [
          { classification: 'Supportive', disease_name: 'medullary sponge kidney' },
          { classification: 'Definitive', disease_name: 'renal cysts and diabetes syndrome' }
        ]
      },
      gene
    )
    expect(meta.summary).toBe('Definitive for renal cysts and diabetes syndrome and 1 more disease')
    expect(meta.classification).toBe('Definitive')
    expect(meta.stats.map(s => `${s.value} ${s.unit}`)).toEqual([
      '2 submissions',
      '2 submitters',
      '2 diseases'
    ])
    expect(meta.link?.href).toBe('https://search.thegencc.org/genes/HGNC:11630')
  })

  it('keeps the full ClinGen disease name (CSS truncates, not JS) and links the gene page', () => {
    const meta = evidenceMeta(
      'ClinGen',
      {
        validities: [
          { classification: 'Definitive', disease_name: 'renal cysts and diabetes syndrome' }
        ],
        expert_panels: ['Monogenic Diabetes Gene Curation Expert Panel']
      },
      gene
    )
    expect(meta.summary).toBe('Definitive for renal cysts and diabetes syndrome')
    expect(meta.link?.href).toBe('https://search.clinicalgenome.org/kb/genes/HGNC:11630')
  })

  it('never links Diagnostic panels to "#" and hides ingestion artefacts as providers', () => {
    const meta = evidenceMeta(
      'DiagnosticPanels',
      { panels: ['Renasight', 'CentoNephro'], providers: ['Seeded from 9 files'] },
      gene
    )
    expect(meta.link).toBeNull()
    expect(meta.stats.map(s => s.unit)).toEqual(['panels'])
    expect(meta.summary).toBe('CentoNephro and 1 more panel')
  })

  it('links HPO by NCBI gene ID only when it is known', () => {
    expect(evidenceMeta('HPO', { hpo_terms: [] }, gene).link).toBeNull()
    expect(evidenceMeta('HPO', { hpo_terms: [] }, gene, { ncbiGeneId: '6928' }).link?.href).toBe(
      'https://hpo.jax.org/browse/gene/NCBIGene:6928'
    )
  })

  it('counts PanelApp panels once although the payload repeats them', () => {
    const panel = { id: 678, name: 'Unexplained young onset ESRD', region: 'UK' }
    const meta = evidenceMeta('PanelApp', { panels: [panel, panel, panel] }, gene)
    expect(meta.stats[0]).toEqual({ value: 1, unit: 'panel' })
  })
})

describe('evidence helpers', () => {
  it('ranks classifications by strength, below which Disputed/Refuted fall', () => {
    expect(strongestClassification(['Limited', 'Disputed Evidence', 'Strong'])).toBe('Strong')
    expect(strongestClassification(['Refuted Evidence'])).toBe('Refuted Evidence')
    expect(strongestClassification([])).toBeNull()
  })

  it('spells out inheritance abbreviations', () => {
    expect(formatInheritance('AD')).toBe('Autosomal dominant (AD)')
    expect(formatInheritance('Autosomal recessive')).toBe('Autosomal recessive')
  })

  it('splits OMIM numbers off PanelApp phenotype text and deduplicates the variants', () => {
    expect(
      parsePanelAppPhenotypes([
        'Renal cysts and diabetes syndrome',
        'Renal cysts and diabetes syndrome, MIM#137920',
        'Renal cysts and diabetes syndrome\t137920',
        'Renal cysts and diabetes syndrome 137920 AD',
        'Diabetes mellitus, noninsulin-dependent, 125853',
        'NIDDM MIM 125853',
        '{Renal cell carcinoma} 144700'
      ])
    ).toEqual([
      { name: 'Diabetes mellitus, noninsulin-dependent', omim: '125853' },
      { name: 'Renal cell carcinoma', omim: '144700' },
      { name: 'Renal cysts and diabetes syndrome', omim: '137920' }
    ])
  })
})

describe('EvidenceCard anatomy', () => {
  it('expands from a real button with aria-expanded and shows the footer link', async () => {
    const wrapper = mount(
      {
        render: () =>
          h(TooltipProvider, () =>
            h(EvidenceCard, {
              gene,
              evidence: {
                source_name: 'DiagnosticPanels',
                evidence_date: '2026-03-15',
                evidence_data: { panels: ['Renasight'], providers: ['Seeded from 9 files'] }
              }
            })
          )
      },
      { attachTo: document.body }
    )
    expect(wrapper.find('h3').text()).toBe('Diagnostic panels')
    const toggle = wrapper.get('button[aria-expanded]')
    expect(toggle.attributes('aria-expanded')).toBe('false')
    expect(toggle.attributes('aria-label')).toBe('Show Diagnostic panels details')
    await toggle.trigger('click')
    await flushPromises()
    expect(toggle.attributes('aria-expanded')).toBe('true')
    expect(wrapper.text()).toContain('Last updated Mar 15, 2026')
    expect(wrapper.text()).toContain('Renasight')
    expect(wrapper.text()).not.toContain('Seeded from')
    expect(wrapper.find('a[href="#"]').exists()).toBe(false)
    wrapper.unmount()
  })
})
