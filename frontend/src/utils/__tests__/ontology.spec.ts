import { describe, it, expect } from 'vitest'
import { ontologyUrl } from '@/utils/ontology'

describe('ClinVar links', () => {
  it('links RCV accessions to the record page and VCV accessions without version', () => {
    expect(ontologyUrl('RCV000012345')).toBe('https://www.ncbi.nlm.nih.gov/clinvar/RCV000012345/')
    expect(ontologyUrl('VCV000012345.3')).toBe(
      'https://www.ncbi.nlm.nih.gov/clinvar/variation/12345/'
    )
    expect(ontologyUrl('VCV000012345')).toBe(
      'https://www.ncbi.nlm.nih.gov/clinvar/variation/12345/'
    )
  })
})
