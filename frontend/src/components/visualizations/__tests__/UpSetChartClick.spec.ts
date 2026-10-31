import { describe, it, expect, vi } from 'vitest'

vi.mock('vue-router', () => import('@/test/routerStub'))
import { mount, flushPromises } from '@vue/test-utils'

const overlaps = {
  sets: [
    { name: 'A', size: 5 },
    { name: 'B', size: 3 }
  ],
  intersections: [
    { sets: ['A'], size: 3 },
    { sets: ['A', 'B'], size: 2 },
    { sets: ['B'], size: 1 }
  ],
  total_unique_genes: 6,
  overlap_statistics: {
    genes_in_all_sources: 2,
    single_source_combinations: 2,
    single_source_genes: 4
  }
}

vi.mock('@/api/statistics', () => ({
  statisticsApi: { getSourceOverlaps: vi.fn(async () => ({ data: overlaps })) }
}))

// Capture the props UpSet.js is rendered with
const rendered: { onClick?: (_item: unknown) => void; sets?: unknown[]; combinations?: unknown[] } =
  {}
vi.mock('@upsetjs/bundle', async importOriginal => ({
  ...(await importOriginal<object>()),
  renderUpSet: (_el: unknown, props: typeof rendered) => Object.assign(rendered, props)
}))

vi.stubGlobal('logService', { info: vi.fn(), error: vi.fn(), warn: vi.fn() })
vi.stubGlobal(
  'ResizeObserver',
  class {
    observe() {}
    unobserve() {}
    disconnect() {}
  }
)
// jsdom has no layout; a desktop width selects the UpSet plot instead of the mobile table
Object.defineProperty(HTMLElement.prototype, 'clientWidth', { configurable: true, value: 1200 })

import UpSetChart from '../UpSetChart.vue'

describe('UpSetChart selection (#315)', () => {
  it('ignores clicks on whole-set rows (their size is not an exclusive count)', async () => {
    const wrapper = mount(UpSetChart)
    await flushPromises()
    const setA = (rendered.sets as { name: string }[]).find(s => s.name === 'A')
    rendered.onClick?.(setA)
    await flushPromises()
    expect(wrapper.text()).not.toContain('Selected Intersection')
    expect(wrapper.text()).not.toContain('5 genes found only')
  })

  it('counts single-source genes, not single-source combinations', async () => {
    const wrapper = mount(UpSetChart)
    await flushPromises()
    const stat = wrapper
      .findAll('dl > div')
      .find(d => d.text().includes('Genes in One Source Only'))
    expect(stat?.find('dd').text()).toBe('4')
  })

  it('shows the exclusive count for a clicked intersection bar', async () => {
    const wrapper = mount(UpSetChart)
    await flushPromises()
    const aOnly = (rendered.combinations as { name: string; cardinality: number }[]).find(
      c => c.name === 'A'
    )
    rendered.onClick?.(aOnly)
    await flushPromises()
    // Unselected sources are dropped before intersecting, so exclusivity is relative (#315)
    expect(wrapper.text()).toContain(
      '3 genes found only in these sources, among the selected sources'
    )
    expect(wrapper.text()).toContain(
      'each gene is counted once, under exactly the selected sources it is found in'
    )
  })
})
