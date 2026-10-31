import { describe, it, expect } from 'vitest'
import { binCounts } from '../histogramBins'

const rows = (pairs: [number, number][]) =>
  pairs.map(([n, c]) => ({ category: String(n), gene_count: c }))

describe('binCounts', () => {
  it('fills empty integer bins so gaps stay visible', () => {
    expect(
      binCounts(
        rows([
          [1, 5],
          [3, 2]
        ])
      )
    ).toEqual([
      { category: '1', gene_count: 5 },
      { category: '2', gene_count: 0 },
      { category: '3', gene_count: 2 }
    ])
  })

  it('bins long tails 1-2-5 and keeps every gene', () => {
    const out = binCounts(
      rows([
        [1, 10],
        [7, 3],
        [15, 2],
        [1272, 1]
      ])
    )
    expect(out.map(r => r.category)).toEqual([
      '1',
      '2',
      '3',
      '4',
      '5',
      '6–10',
      '11–20',
      '21–50',
      '51–100',
      '101–200',
      '201–500',
      '501–1000',
      '1001–2000'
    ])
    expect(out.reduce((s, r) => s + r.gene_count, 0)).toBe(16)
    expect(out.find(r => r.category === '6–10')!.gene_count).toBe(3)
  })

  it('passes pre-binned ranges through untouched', () => {
    const hpo = [{ category: '1-5', gene_count: 3 }]
    expect(binCounts(hpo)).toBe(hpo)
  })
})
