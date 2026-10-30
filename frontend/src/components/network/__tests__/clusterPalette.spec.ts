import { describe, it, expect } from 'vitest'
import { CLUSTER_PALETTE, SMALL_CLUSTER_STYLE, clusterStyle } from '../clusterPalette'

describe('cluster palette', () => {
  it('has 12 distinct colours', () => {
    expect(new Set(CLUSTER_PALETTE.map(c => c.toLowerCase())).size).toBe(12)
  })

  it('gives every one of 24 clusters its own colour+shape pair', () => {
    const pairs = Array.from({ length: 24 }, (_, rank) => {
      const { color, shape } = clusterStyle(rank, 10, 3)
      return `${color}/${shape}`
    })
    expect(new Set(pairs).size).toBe(24)
    expect(pairs.some(p => p.startsWith(SMALL_CLUSTER_STYLE.color))).toBe(false)
  })

  it('greys only clusters below the minimum size', () => {
    expect(clusterStyle(0, 2, 3)).toEqual(SMALL_CLUSTER_STYLE)
    expect(clusterStyle(0, 3, 3).color).toBe(CLUSTER_PALETTE[0])
  })
})
