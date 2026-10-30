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
    expect(w.text()).toContain('Curator A')
    expect(w.text()).toContain('Reviewer B')
    expect(w.text()).toContain('15 points (genetic 10, experimental 5)')
  })
})
