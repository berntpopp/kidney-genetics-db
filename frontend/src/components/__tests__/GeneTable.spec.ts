/**
 * GeneTable interaction tests with real controls and a real router.
 */

import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest'
import { flushPromises, mount } from '@vue/test-utils'
import type { VueWrapper } from '@vue/test-utils'
import { defineComponent, h } from 'vue'
import { createRouter, createMemoryHistory, RouterView } from 'vue-router'
import GeneTable from '@/components/GeneTable.vue'

vi.mock('@/api/genes', () => ({ geneApi: { getGenes: vi.fn() } }))
import { geneApi } from '@/api/genes'

vi.stubGlobal('logService', { info: vi.fn(), warn: vi.fn(), error: vi.fn(), debug: vi.fn() })
vi.stubGlobal(
  'ResizeObserver',
  class {
    observe() {}
    unobserve() {}
    disconnect() {}
  }
)

const getGenes = vi.mocked(geneApi.getGenes)

const listResult = (items: Record<string, unknown>[] = []) =>
  ({
    items,
    total: items.length,
    page: 1,
    perPage: 10,
    pageCount: 1,
    meta: { filters: { available_sources: ['ClinGen', 'GenCC'] } }
  }) as never

let wrapper: VueWrapper | undefined

async function mountAt(path = '/genes') {
  const router = createRouter({
    history: createMemoryHistory(),
    routes: [
      { path: '/genes', component: GeneTable },
      { path: '/genes/:symbol', component: { render: () => null } }
    ]
  })
  await router.push(path)
  await router.isReady()
  wrapper = mount(defineComponent({ render: () => h(RouterView) }), {
    global: { plugins: [router] },
    attachTo: document.body
  })
  await flushPromises()
  await new Promise(r => setTimeout(r, 120)) // GeneTable ends initialization after 100 ms
  return { router, wrapper }
}

describe('GeneTable', () => {
  beforeEach(() => {
    getGenes.mockReset()
    getGenes.mockResolvedValue(listResult())
  })

  afterEach(() => {
    wrapper?.unmount()
    document.body.innerHTML = ''
  })

  it('source checkbox updates the filter, request and URL (#299)', async () => {
    const { router } = await mountAt()
    const sourcesButton = wrapper!.findAll('button').find(b => b.text().startsWith('Sources'))!
    await sourcesButton.trigger('click')
    await flushPromises()

    const box = document.getElementById('source-ClinGen')!
    box.click()
    await flushPromises()

    expect(box.getAttribute('aria-checked')).toBe('true')
    expect(getGenes).toHaveBeenLastCalledWith(expect.objectContaining({ source: 'ClinGen' }))
    expect(router.currentRoute.value.query.source).toBe('ClinGen')
  })
  it('runs the latest search after an in-flight request and drops the stale rows (#300)', async () => {
    const { router } = await mountAt()
    const gene = (symbol: string) => ({ id: symbol.length, approved_symbol: symbol, hgnc_id: 'x' })
    let releasePkd1!: () => void
    getGenes.mockImplementation(async params => {
      if (params?.search === 'PKD1') {
        await new Promise<void>(r => (releasePkd1 = r))
        return listResult([gene('PKD1')])
      }
      return listResult([gene(String(params?.search))])
    })

    const input = wrapper!.find('input[placeholder^="PKD1"]')
    await input.setValue('PKD1')
    await new Promise(r => setTimeout(r, 350)) // debounce -> PKD1 request in flight
    await input.setValue('PKD2')
    await new Promise(r => setTimeout(r, 350)) // debounce -> PKD2 requested while PKD1 runs
    releasePkd1()
    await flushPromises()
    await new Promise(r => setTimeout(r, 150))
    await flushPromises()

    expect(getGenes).toHaveBeenLastCalledWith(expect.objectContaining({ search: 'PKD2' }))
    expect(router.currentRoute.value.query.search).toBe('PKD2')
    expect(getGenes.mock.calls.filter(([p]) => p?.search === 'PKD2')).toHaveLength(1)
    const symbols = wrapper!.findAll('a[href^="/genes/"]').map(a => a.text())
    expect(symbols).toEqual(['PKD2'])
  })
  it('shows source presence without inventing per-source percentages (#301)', async () => {
    getGenes.mockResolvedValue(
      listResult([
        {
          id: 1,
          approved_symbol: 'PKD1',
          hgnc_id: 'HGNC:9008',
          evidence_score: 50,
          sources: ['ClinGen', 'GenCC']
        }
      ])
    )
    await mountAt()
    const scoreBadge = wrapper!.findAll('[data-slot="badge"]').find(b => b.text() === '50.0')!
    await scoreBadge.trigger('click')
    await flushPromises()

    expect(document.body.textContent).toContain('Score: 50.0%')
    expect(document.body.textContent).not.toMatch(/100\.0%/)
  })
})

describe('GeneTable load states (#316)', () => {
  beforeEach(() => {
    getGenes.mockReset()
  })
  afterEach(() => {
    wrapper?.unmount()
    document.body.innerHTML = ''
  })

  it.each([
    ['500', Object.assign(new Error('Request failed'), { response: { status: 500 } })],
    ['network error', new Error('Network Error')]
  ])('shows a retryable error, not "No genes found", on %s', async (_, err) => {
    getGenes.mockRejectedValue(err)
    await mountAt()

    expect(wrapper!.text()).toContain("Couldn't load genes from the server.")
    expect(wrapper!.text()).not.toContain('No genes found')
    expect(wrapper!.text()).not.toMatch(/0\/0 genes/)
    getGenes.mockResolvedValue(listResult([{ id: 1, approved_symbol: 'PKD1', hgnc_id: 'x' }]))
    await wrapper!
      .findAll('button')
      .find(b => b.text() === 'Try again')!
      .trigger('click')
    await flushPromises()
    expect(getGenes).toHaveBeenCalledTimes(2)
    expect(wrapper!.findAll('a[href^="/genes/"]').map(a => a.text())).toEqual(['PKD1'])
  })

  it('shows "No genes found" only for a successful empty response', async () => {
    getGenes.mockResolvedValue(listResult())
    await mountAt()

    expect(wrapper!.text()).toContain('No genes found')
    expect(wrapper!.text()).not.toContain("Couldn't load")
  })
})
