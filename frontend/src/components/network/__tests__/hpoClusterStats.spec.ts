import { describe, it, expect } from 'vitest'
import { computeHpoClusterStats } from '../hpoClusterStats'

const row = (
  gene_id: number,
  is_syndromic: boolean | null,
  clinical_group: string | null = null,
  onset_group: string | null = null
) => ({ gene_id, clinical_group, onset_group, is_syndromic })

const lookup = (rows: ReturnType<typeof row>[]) => new Map(rows.map(r => [r.gene_id, r]))

describe('computeHpoClusterStats (#253)', () => {
  it('keeps unassessed genes out of isolated counts and denominators', () => {
    const stats = computeHpoClusterStats(
      [1, 2, 3, 4, 5],
      lookup([
        row(1, true, 'cyst_cilio'),
        row(2, false, 'cyst_cilio'),
        row(3, false),
        row(4, null) // annotation without any assessment (view row, all null)
        // gene 5: no row at all
      ])
    )
    expect(stats.hpoDataCount).toBe(3)
    expect(stats.hpoDataPercentage).toBe('60.0')
    expect(stats.syndromic).toEqual({
      assessedCount: 3,
      unknownCount: 2,
      syndromicCount: 1,
      syndromicPercentage: '33.3',
      isolatedCount: 2,
      isolatedPercentage: '66.7'
    })
  })

  it('returns null percentages instead of NaN when nothing is assessed', () => {
    const stats = computeHpoClusterStats([1, 2], lookup([row(1, null), row(2, null)]))
    expect(stats.hpoDataCount).toBe(0)
    expect(stats.clinical).toEqual([])
    expect(stats.syndromic).toMatchObject({
      assessedCount: 0,
      unknownCount: 2,
      syndromicPercentage: null,
      isolatedPercentage: null
    })
  })

  it('counts a gene with a known group but unknown syndromic status as HPO data only', () => {
    const stats = computeHpoClusterStats([1], lookup([row(1, null, 'complement')]))
    expect(stats.hpoDataCount).toBe(1)
    expect(stats.clinical[0]).toMatchObject({ key: 'complement', percentage: '100.0' })
    expect(stats.syndromic.assessedCount).toBe(0)
    expect(stats.syndromic.unknownCount).toBe(1)
  })
})
