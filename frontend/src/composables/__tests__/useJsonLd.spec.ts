import { describe, it, expect } from 'vitest'
import { getGeneSchema } from '../useJsonLd'

describe('getGeneSchema', () => {
  it('includes BioSchemas conformsTo and required properties', () => {
    const schema = getGeneSchema({
      approved_symbol: 'PKD1',
      approved_name: 'polycystin 1, transient receptor potential channel interacting',
      hgnc_id: 'HGNC:9008',
      aliases: ['PKD', 'PBP'],
      evidence_score: 95.2,
      ensembl_gene_id: 'ENSG00000008710',
      ncbi_gene_id: '5310',
      uniprot_id: 'P98161',
      chromosome: '16'
    })

    expect(schema['@type']).toBe('Gene')
    expect(schema['dct:conformsTo']).toBe('https://bioschemas.org/profiles/Gene/1.0-RELEASE')
    expect(schema.name).toBe('PKD1')
    expect(schema.description).toContain('polycystin 1')
    expect(schema.taxonomicRange).toEqual({
      '@type': 'Taxon',
      name: 'Homo sapiens',
      '@id': 'https://identifiers.org/taxonomy:9606'
    })
    expect(schema.sameAs).toBeInstanceOf(Array)
    expect(schema.sameAs.length).toBeGreaterThanOrEqual(3)
  })

  it('handles minimal gene data gracefully', () => {
    const schema = getGeneSchema({
      approved_symbol: 'UNKNOWN'
    })

    expect(schema['@type']).toBe('Gene')
    expect(schema.name).toBe('UNKNOWN')
    expect(schema.identifier).toBe('UNKNOWN')
    expect(schema.sameAs).toEqual([])
  })
})
