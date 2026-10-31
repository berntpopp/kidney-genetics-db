import { describe, expect, it } from 'vitest'
import type { ClusterResult, DomainResult, ScanResult } from '@/types/positionStats'
import {
  clusterSentence,
  domainSentence,
  formatOR,
  formatP,
  hotspotSentence,
  residueRanges,
  scanSentence
} from '../sentences'

const row = (o: Partial<DomainResult>): DomainResult => ({
  key: 'k',
  label: 'POU-specific atypical',
  type: 'Domain',
  start: 93,
  end: 188,
  caseIn: 40,
  ctrlIn: 20,
  caseOut: 10,
  ctrlOut: 200,
  p: 1e-10,
  or: 4.4,
  lo: 2.5,
  hi: 7.5,
  q: 1e-9,
  ...o
})

const scan = (regions: ScanResult['regions']): ScanResult => ({
  windows: [],
  regions,
  B: 10000,
  seed: 20261031,
  w: 15
})

describe('sentences', () => {
  it('names the top significant domain with OR, CI and q', () => {
    expect(
      domainSentence([row({ key: 'b', label: 'Disordered', type: 'Region', q: 0.4 }), row({})])
    ).toBe(
      'Pathogenic missense variants are 4.4× more likely than population variants to fall in the POU-specific atypical domain (95% CI 2.5–7.5; q < 0.001).'
    )
  })

  it('says plainly when nothing is significant', () => {
    expect(domainSentence([row({ q: 0.2 })])).toContain('No domain is significantly enriched')
  })

  it('counts further significant features and handles depletion', () => {
    expect(domainSentence([row({}), row({ key: 'x', q: 0.01 })])).toContain(
      '1 other feature also differs significantly.'
    )
    expect(domainSentence([row({ or: 0.25, lo: 0.1, hi: 0.5, q: 0.02 })])).toContain(
      '4.0× less likely'
    )
  })

  it('formats p values with the permutation floor', () => {
    expect(formatP(0.0000999, 10000)).toBe('< 0.0001')
    expect(formatP(0.0002, 10000)).toBe('0.0002')
    expect(formatP(3.8e-13)).toBe('< 0.001')
    expect(formatP(0.034)).toBe('0.03')
    expect(formatOR(Infinity)).toBe('∞')
  })

  it('never rounds a significant value up to 0.05', () => {
    expect(formatP(0.0496)).toBe('0.049')
    expect(Number(formatP(0.0496))).toBeLessThan(0.05)
    expect(formatP(0.0496, 10000)).toBe('0.049')
    expect(formatP(0.05)).toBe('0.05')
    expect(formatP(0.0501)).toBe('0.05')
  })

  it('describes scan regions and their benign count', () => {
    const s = scanSentence(
      scan([
        { start: 122, end: 179, cases: 30, ctrls: 5, benign: 0, adjP: 1 / 10001 },
        { start: 282, end: 309, cases: 10, ctrls: 1, benign: 0, adjP: 2e-4 }
      ])
    )
    expect(s).toBe(
      'Pathogenic missense variants cluster in residues 122–179 and 282–309 (family-wise adjusted p < 0.0001 to 0.0002); no ClinVar benign or likely benign missense variant falls in them.'
    )
    // PKD1-like: the sentence spans every region's adjusted p, not only the best
    expect(
      scanSentence(
        scan([
          { start: 100, end: 120, cases: 30, ctrls: 5, benign: 0, adjP: 1 / 10001 },
          { start: 3132, end: 3146, cases: 6, ctrls: 1, benign: 1, adjP: 0.046 }
        ])
      )
    ).toContain('(family-wise adjusted p < 0.0001 to 0.046)')
    expect(
      scanSentence(scan([{ start: 5, end: 9, cases: 6, ctrls: 1, benign: 0, adjP: 0.012 }]))
    ).toContain('(family-wise adjusted p = 0.01)')
    expect(scanSentence(scan([]))).toContain('No stretch of the protein is significantly enriched')
  })

  it('reports 3D clustering in both directions', () => {
    const c: ClusterResult = {
      observed: 18.24,
      nullMean: 26.5,
      nullLo: 22,
      nullHi: 31,
      p: 0.0003,
      histogram: [],
      nCaseResidues: 20,
      B: 10000,
      seed: 1
    }
    expect(clusterSentence(c)).toContain('closer together in the 3D structure than expected')
    expect(clusterSentence(c)).toContain('18.2 Å vs 26.5 Å expected; p = 0.0003')
    expect(clusterSentence({ ...c, p: 0.4 })).toContain('not significant')
  })
})

describe('3D hotspot sentences', () => {
  const c = (residues: number[], adjP: number) => ({
    residues,
    residueAdjP: residues.map(() => adjP),
    cases: 10,
    ctrls: 2,
    adjP
  })
  it('collapses residues into ranges', () => {
    expect(residueRanges([145, 140, 141, 142, 159])).toBe('140–142, 145, 159')
  })
  it('names the hotspots and the best adjusted p', () => {
    const h = {
      clusters: [c([140, 142, 159], 0.0005), c([300], 0.02)],
      B: 2000,
      seed: 1,
      radius: 10
    }
    expect(hotspotSentence(h)).toBe(
      'Pathogenic missense variants concentrate in 2 hotspots in the 3D structure: residues 140, 142, 159 and residues 300 (10 Å neighbourhoods; best family-wise adjusted p = 0.0005).'
    )
  })
  it('never reports a non-contiguous cluster as one sequence span', () => {
    const many = [140, 145, 148, 149, 150, 151, 152, 153, 155, 156, 158, 159, 187, 286]
    const s = hotspotSentence({
      clusters: [c([140, 145, 148, 149, 150, 153, 155, 156, 158, 159], 0.01)],
      B: 2000,
      seed: 1,
      radius: 10
    })
    expect(s).toContain('residues 140, 145, 148–150, 153, 155–156, 158–159')
    expect(s).not.toContain('140–159')
    expect(hotspotSentence({ clusters: [c(many, 0.01)], B: 2000, seed: 1, radius: 10 })).toContain(
      '14 residues spanning 140–286 in sequence, close together in 3D'
    )
  })
  it('says plainly when there is no hotspot', () => {
    expect(hotspotSentence({ clusters: [], B: 2000, seed: 1, radius: 10 })).toBe(
      'No 10 Å neighbourhood in the 3D structure is significantly enriched for pathogenic missense variants (family-wise adjusted p ≥ 0.05).'
    )
  })
})
