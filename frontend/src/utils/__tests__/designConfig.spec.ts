import { describe, it, expect } from 'vitest'
import { getSourceConfig, resolveCssColor, SOURCE_CONFIG, SOURCE_NAMES } from '@/utils/sources'
import { getStatusConfig, STATUS, STATUS_TONE_CLASSES } from '@/utils/status'
import { ontologyUrl, parseOntologyId } from '@/utils/ontology'
import type { AnnotationSourceName } from '@/types/evidence'

describe('sources', () => {
  it('covers every evidence source with a display name and a unique chart colour', () => {
    const backend: AnnotationSourceName[] = [
      'ClinGen',
      'GenCC',
      'HPO',
      'PanelApp',
      'PubTator',
      'DiagnosticPanels',
      'Literature'
    ]
    expect([...SOURCE_NAMES].sort()).toEqual([...backend].sort())
    const colors = Object.values(SOURCE_CONFIG).map(c => c.chartColor)
    expect(new Set(colors).size).toBe(colors.length)
    expect(colors.every(c => /^var\(--source-[1-7]\)$/.test(c))).toBe(true)
    expect(getSourceConfig('DiagnosticPanels').displayName).toBe('Diagnostic panels')
  })

  it('falls back to the raw name and the neutral colour', () => {
    expect(getSourceConfig('gnomad')).toMatchObject({
      displayName: 'gnomad',
      chartColor: 'var(--source-8)'
    })
  })

  it('resolves CSS variables for chart code', () => {
    document.documentElement.style.setProperty('--source-1', 'oklch(0.5 0.1 244)')
    expect(resolveCssColor('var(--source-1)')).toBe('oklch(0.5 0.1 244)')
    expect(resolveCssColor('#000000')).toBe('#000000')
  })
})

describe('status', () => {
  it('maps the same status to the same tone in any spelling', () => {
    expect(getStatusConfig('FAILED').tone).toBe('danger')
    expect(getStatusConfig('in-progress')).toBe(STATUS.in_progress)
    expect(getStatusConfig('WARNING').tone).toBe('warning')
    expect(getStatusConfig('completed').tone).toBe('success')
    expect(getStatusConfig('draft').tone).toBe('neutral')
  })

  it('classes HTTP codes and keeps unknown labels neutral', () => {
    expect(getStatusConfig(503).tone).toBe('danger')
    expect(getStatusConfig('404').tone).toBe('warning')
    expect(getStatusConfig(200).tone).toBe('success')
    expect(getStatusConfig('mystery')).toMatchObject({ tone: 'neutral', label: 'mystery' })
  })

  it('gives every status a label and icon and every tone token classes', () => {
    for (const c of Object.values(STATUS)) expect(c.label && c.icon).toBeTruthy()
    for (const cls of Object.values(STATUS_TONE_CLASSES)) expect(cls).not.toMatch(/-\d{3}\b/)
  })
})

describe('ontology', () => {
  it.each([
    ['HP:0000112', 'HPO', 'HP:0000112', 'https://hpo.jax.org/browse/term/HP:0000112'],
    ['MONDO:0008263', 'MONDO', 'MONDO:0008263', 'https://monarchinitiative.org/MONDO:0008263'],
    ['MIM:173900', 'OMIM', 'OMIM:173900', 'https://omim.org/entry/173900'],
    ['Orphanet_93', 'Orphanet', 'ORPHA:93', 'https://www.orpha.net/en/disease/detail/93'],
    ['PMID: 8004675', 'PubMed', 'PMID:8004675', 'https://pubmed.ncbi.nlm.nih.gov/8004675/'],
    [
      'HGNC:5024',
      'HGNC',
      'HGNC:5024',
      'https://www.genenames.org/data/gene-symbol-report/#!/hgnc_id/HGNC:5024'
    ],
    [
      'ENSG00000108753',
      'Ensembl',
      'ENSG00000108753',
      'https://www.ensembl.org/Homo_sapiens/Gene/Summary?g=ENSG00000108753'
    ],
    [
      'VCV000012345',
      'ClinVar',
      'VCV000012345',
      'https://www.ncbi.nlm.nih.gov/clinvar/variation/12345/'
    ]
  ])('parses %s', (raw, source, id, url) => {
    expect(parseOntologyId(raw)).toMatchObject({ source, id, url })
  })

  it('needs a hint for bare numbers and rejects unknown prefixes', () => {
    expect(parseOntologyId('173900')).toBeNull()
    expect(ontologyUrl(173900, 'OMIM')).toBe('https://omim.org/entry/173900')
    expect(parseOntologyId('FOO:1')).toBeNull()
    expect(parseOntologyId('')).toBeNull()
  })
})
