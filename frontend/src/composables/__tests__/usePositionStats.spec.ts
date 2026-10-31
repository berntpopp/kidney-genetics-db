import { describe, it, expect, vi, beforeEach } from 'vitest'
import { effectScope, nextTick, ref } from 'vue'
import { usePositionStats } from '../usePositionStats'
import apiClient from '@/api/client'

const variantSet = {
  cases: 84,
  controls: 607,
  benign: 6,
  dropped: { clinvar: 0, gnomad: 1 },
  checked: { clinvar: 90, gnomad: 645 }
}
const payload = (o: Record<string, unknown> = {}) => ({
  gene: 'PKD1',
  status: 'ready',
  message: null,
  variantSet,
  linear: { domains: [{ key: 'a', or: null, lo: 2, hi: null, q: 0.01 }], scan: { regions: [] } },
  spatial: { cluster: null, hotspots: { clusters: [], B: 2000, seed: 1, radius: 10 } },
  spatialMessage: null,
  ...o
})

const settle = async () => {
  for (let i = 0; i < 5; i++) await nextTick()
  await new Promise(r => setTimeout(r, 0))
}
function setup(symbol = 'PKD1') {
  const sym = ref(symbol)
  const stats = effectScope().run(() => usePositionStats({ symbol: sym }))!
  return { stats, sym }
}
const get = vi.spyOn(apiClient, 'get')

beforeEach(() => {
  get.mockReset().mockResolvedValue({ data: payload() })
})

describe('usePositionStats', () => {
  it('stays idle without a symbol (lazy trigger) and loads once one is given', async () => {
    const { stats, sym } = setup('')
    expect(stats.status.value).toBe('idle')
    expect(get).not.toHaveBeenCalled()
    sym.value = 'PKD1'
    await settle()
    expect(stats.status.value).toBe('ready')
    expect(stats.variantSet.value?.cases).toBe(84)
  })

  it('maps null OR / upper CI bound to Infinity', async () => {
    const { stats } = setup()
    await settle()
    const d = stats.linear.value!.domains[0]!
    expect(d.or).toBe(Infinity)
    expect(d.hi).toBe(Infinity)
    expect(d.lo).toBe(2)
  })

  it.each(['withheld', 'too-few'])('passes through %s with its message', async status => {
    get.mockResolvedValue({
      data: payload({ status, message: 'nope', linear: null, spatial: null })
    })
    const { stats } = setup()
    await settle()
    expect(stats.status.value).toBe(status)
    expect(stats.message.value).toBe('nope')
    expect(stats.linear.value).toBeNull()
  })

  it('shows the API detail on error and retry() refetches', async () => {
    get.mockRejectedValueOnce({ response: { data: { detail: 'gnomAD responded 429' } } })
    const { stats } = setup()
    await settle()
    expect(stats.status.value).toBe('error')
    expect(stats.message.value).toBe('gnomAD responded 429')
    stats.retry()
    await settle()
    expect(stats.status.value).toBe('ready')
    expect(get).toHaveBeenCalledTimes(2)
  })

  it('reads the detail from the wrapped error shape, with a generic fallback', async () => {
    get.mockRejectedValueOnce({ response: { data: { error: { detail: 'gnomAD responded 429' } } } })
    const { stats } = setup()
    await settle()
    expect(stats.message.value).toBe('gnomAD responded 429')
    get.mockRejectedValueOnce(new Error('Network Error'))
    stats.retry()
    await settle()
    expect(stats.message.value).toBe('Could not load statistics')
  })

  it('refetches with min_stars when minStars changes', async () => {
    const { stats } = setup()
    await settle()
    stats.minStars.value = 0
    await settle()
    expect(get).toHaveBeenLastCalledWith('/api/genes/PKD1/position-statistics', {
      params: { min_stars: 0 }
    })
  })
})
