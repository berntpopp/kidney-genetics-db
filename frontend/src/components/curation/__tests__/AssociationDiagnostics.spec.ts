import { describe, it, expect } from 'vitest'
import { mount } from '@vue/test-utils'
import AssociationDiagnostics from '@/components/curation/AssociationDiagnostics.vue'
import type { Diagnostics } from '@/api/curation'

const DIAGNOSTICS: Diagnostics = {
  recommended_transcript: {
    refseq: null,
    ensembl: 'ENST00000620103.4',
    mane_status: 'none',
    legacy_transcript: 'NM_002456.5',
    numbering_conversion: 'No MANE Select; literature uses NM_002456.5.'
  },
  detectability: [
    {
      challenge: 'VNTR frameshift not called by short-read pipelines',
      share_of_variants: '~99%',
      affected_variants: null,
      methods: ['long_read_sequencing'],
      tools: [{ name: 'VNtyper 2', url: 'https://example.org/vntyper', pmid_or_doi: null }],
      negative_report_does_not_exclude: true,
      sources: []
    }
  ],
  resources: [
    {
      type: 'patient_organisation',
      name: 'Example ADTKD group',
      url: 'https://example.org/adtkd',
      language: 'de',
      audiences: ['patients'],
      maintainer: null,
      conflict_of_interest: null,
      verified: { method: 'fetched', date: '2026-10-30' }
    }
  ]
}

const mountWith = (diagnostics: Diagnostics | null) =>
  mount(AssociationDiagnostics, { props: { diagnostics } })

describe('AssociationDiagnostics', () => {
  it('renders verified resource links that open safely in a new tab', () => {
    const w = mountWith(DIAGNOSTICS)
    const link = w.find('a[href="https://example.org/adtkd"]')
    expect(link.exists()).toBe(true)
    expect(link.attributes('rel')).toBe('noopener noreferrer')
    expect(link.attributes('target')).toBe('_blank')
    expect(w.text()).toContain('Diagnostics & resources')
    expect(w.text()).toContain('verified 2026-10-30')
    expect(w.text()).toContain('ENST00000620103.4')
    expect(w.text()).toContain('No MANE Select')
  })

  it('warns that a negative short-read result does not exclude a variant only when flagged', () => {
    expect(mountWith(DIAGNOSTICS).text()).toContain('does not exclude')
    const unflagged = {
      ...DIAGNOSTICS,
      detectability: [{ ...DIAGNOSTICS.detectability[0], negative_report_does_not_exclude: false }]
    }
    expect(mountWith(unflagged).text()).not.toContain('does not exclude')
  })

  it('never renders a non-http link as an anchor', () => {
    const bad = {
      ...DIAGNOSTICS,
      resources: [{ ...DIAGNOSTICS.resources[0], url: 'javascript:alert(1)' }]
    }
    const w = mountWith(bad)
    expect(w.findAll('a').some(a => a.attributes('href')?.startsWith('javascript'))).toBe(false)
    expect(w.text()).toContain('Example ADTKD group')
  })

  it('renders nothing without diagnostics content', () => {
    expect(mountWith(null).text()).toBe('')
    expect(
      mountWith({ recommended_transcript: null, detectability: [], resources: [] }).text()
    ).toBe('')
  })

  it('shows the transcript verified-via, detectability note and resource scope', () => {
    const w = mountWith({
      ...DIAGNOSTICS,
      recommended_transcript: {
        ...DIAGNOSTICS.recommended_transcript!,
        verified_via: 'MANE v1.4 summary'
      },
      detectability_note: 'CNV calling recommended',
      resources: [{ ...DIAGNOSTICS.resources[0]!, country_or_scope: 'Germany' }]
    })
    expect(w.text()).toContain('Verified via MANE v1.4 summary')
    expect(w.text()).toContain('CNV calling recommended')
    expect(w.text()).toContain('Germany')
  })

  it('renders a detectability note on its own', () => {
    const w = mountWith({
      recommended_transcript: null,
      detectability: [],
      detectability_note: 'standard short-read testing adequate',
      resources: []
    })
    expect(w.text()).toContain('standard short-read testing adequate')
  })
})
