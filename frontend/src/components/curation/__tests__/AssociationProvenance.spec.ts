import { describe, it, expect } from 'vitest'
import { mount } from '@vue/test-utils'
import AssociationProvenance from '@/components/curation/AssociationProvenance.vue'
import type { Association } from '@/api/curation'

const BASE = {
  moi: 'HP:0000007',
  moi_label: 'Autosomal recessive inheritance',
  methodology: 'Kidney Gene Curation',
  methodology_version: 'draft iteration 3',
  source: 'kgdb',
  external_id: null,
  external_url: null,
  external_curator: null,
  external_reviewer: null,
  scores: null
} as unknown as Association

describe('AssociationProvenance', () => {
  it('shows the inheritance mode, its CURIE and the methodology', () => {
    const text = mount(AssociationProvenance, { props: { record: BASE } }).text()
    expect(text).toContain('Autosomal recessive inheritance')
    expect(text).toContain('HP:0000007')
    expect(text).toContain('Kidney Gene Curation (draft iteration 3)')
    const numbered = { ...BASE, methodology_version: '1' } as Association
    expect(mount(AssociationProvenance, { props: { record: numbered } }).text()).toContain(
      'Kidney Gene Curation, version 1'
    )
  })

  it('links to Gene Curator with the external curator and reviewer only for that source', () => {
    expect(mount(AssociationProvenance, { props: { record: BASE } }).text()).not.toContain(
      'Gene Curator'
    )
    const gc = {
      ...BASE,
      source: 'gene_curator',
      external_id: 'GC-1',
      external_url: 'https://example.org/c/1',
      external_curator: 'Curator A',
      external_reviewer: 'Reviewer B',
      scores: { genetic: 10, experimental: 5, total: 15 }
    } as Association
    const w = mount(AssociationProvenance, { props: { record: gc } })
    const link = w.find('a[href="https://example.org/c/1"]')
    expect(link.text()).toContain('Curated in Gene Curator')
    expect(link.attributes('rel')).toBe('noopener noreferrer')
    // An icon, not U+2197, which renders as a colour emoji on some platforms
    expect(link.text()).not.toContain('↗')
    expect(link.find('svg[aria-hidden="true"]').exists()).toBe(true)
    expect(w.text()).toContain('Curator A')
    expect(w.text()).toContain('Reviewer B')
    expect(w.text()).toContain('15 points (genetic 10, experimental 5)')
  })

  it('shows an adopted ClinGen classification with an http(s)-only link and no points', () => {
    const adopted_clingen = {
      id: 'CGGV:assertion_1',
      classification: 'Definitive',
      expert_panel: 'Kidney Cystic and Ciliopathy Disorders GCEP',
      classified_date: '2023-05-04',
      url: 'https://search.clinicalgenome.org/kb/gene-validity/CGGV:assertion_1'
    }
    const record = {
      ...BASE,
      source: 'gene_curator',
      methodology: 'ClinGen gene-disease validity (adopted)',
      methodology_version: null,
      scores: null,
      adopted_clingen
    } as Association
    const w = mount(AssociationProvenance, { props: { record } })
    const link = w.find(`a[href="${adopted_clingen.url}"]`)
    expect(link.attributes('rel')).toBe('noopener noreferrer')
    expect(link.find('svg[aria-hidden="true"]').exists()).toBe(true)
    expect(link.text()).toContain('ClinGen')
    expect(w.text()).toContain(
      '· Kidney Cystic and Ciliopathy Disorders GCEP · Definitive · classified 2023-05-04'
    )
    expect(w.text()).not.toContain('Points')
    const unsafe = { ...record, adopted_clingen: { ...adopted_clingen, url: 'javascript:x' } }
    const w2 = mount(AssociationProvenance, { props: { record: unsafe as Association } })
    expect(w2.find('a[href^="javascript"]').exists()).toBe(false)
    expect(w2.text()).toContain('Adopted fromClinGen')
  })

  it('shows association and functional points for a susceptibility record', () => {
    const risk = {
      ...BASE,
      relationship_type: 'susceptibility',
      scores: { experimental: 1, association: 4, total: 5 }
    } as Association
    const text = mount(AssociationProvenance, { props: { record: risk } }).text()
    expect(text).toContain('5 points (association 4, functional 1)')
  })

  it('lists curator and reviewer as rows and names AI assistance without hiding the curator', () => {
    const rows = (curator: string, ai_agents: string[] | null = null) => {
      const record = {
        ...BASE,
        external_curator: curator,
        ai_agents,
        external_reviewer: 'Bob Jones'
      }
      const w = mount(AssociationProvenance, { props: { record: record as Association } })
      return Object.fromEntries(
        w.findAll('dt').map(dt => [dt.text(), dt.element.nextElementSibling?.textContent?.trim()])
      )
    }
    const ai = rows('Alice Smith', ['model-x'])
    expect(ai['Curated by']).toMatch(/^Alice Smith\s+· AI-assisted \(model-x\)$/)
    expect(ai['Reviewed by']).toBe('Bob Jones')
    expect(rows('Alice Smith')['Curated by']).toBe('Alice Smith')
  })
})
