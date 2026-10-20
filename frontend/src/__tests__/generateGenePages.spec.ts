/**
 * Gene-page generator must page through the gene list within the API limit (#304).
 */

import { describe, it, expect, vi } from 'vitest'
import { fetchAllGenes } from '../../scripts/generate-gene-pages'

describe('fetchAllGenes', () => {
  it('fetches every page of a >100 gene list with page[size] <= 100', async () => {
    const total = 250
    const fetchFn = vi.fn(async (url: string) => {
      const params = new URL(url).searchParams
      const size = Number(params.get('page[size]'))
      const page = Number(params.get('page[number]'))
      if (!size || size > 100)
        return new globalThis.Response('page[size] too large', { status: 422 })
      const start = (page - 1) * size
      const data = Array.from({ length: Math.max(0, Math.min(size, total - start)) }, (_, i) => ({
        id: String(start + i),
        type: 'genes',
        attributes: { approved_symbol: `GENE${start + i}` }
      }))
      return globalThis.Response.json({
        data,
        meta: { total, page_count: Math.ceil(total / size) }
      })
    })

    const genes = await fetchAllGenes(fetchFn as unknown as typeof fetch)

    expect(fetchFn).toHaveBeenCalledTimes(3)
    expect(genes).toHaveLength(total)
    expect(new Set(genes.map(g => g.attributes.approved_symbol)).size).toBe(total)
  })

  it('surfaces API errors', async () => {
    const fetchFn = vi.fn(async () => new globalThis.Response('boom', { status: 500 }))
    await expect(fetchAllGenes(fetchFn as unknown as typeof fetch)).rejects.toThrow(
      'API returned 500: boom'
    )
  })
  it('refuses to guess when meta.page_count is missing', async () => {
    const fetchFn = vi.fn(async () => globalThis.Response.json({ data: [], meta: {} }))
    await expect(fetchAllGenes(fetchFn as unknown as typeof fetch)).rejects.toThrow(
      'meta.page_count'
    )
  })
})
