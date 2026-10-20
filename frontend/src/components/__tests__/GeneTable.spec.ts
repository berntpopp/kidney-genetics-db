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
    routes: [{ path: '/genes', component: GeneTable }]
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
})
