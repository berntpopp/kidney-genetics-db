/**
 * DataSources load states: API failure vs successful empty result (#316, #324).
 */

import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest'
import { flushPromises, mount } from '@vue/test-utils'
import type { VueWrapper } from '@vue/test-utils'
import { createRouter, createMemoryHistory } from 'vue-router'
import DataSources from '@/views/DataSources.vue'

vi.mock('@unhead/vue', () => ({ useHead: vi.fn() }))
vi.mock('@/api/datasources', () => ({ datasourceApi: { getDataSources: vi.fn() } }))
import { datasourceApi } from '@/api/datasources'

vi.stubGlobal('logService', { info: vi.fn(), warn: vi.fn(), error: vi.fn(), debug: vi.fn() })

const getDataSources = vi.mocked(datasourceApi.getDataSources)
let wrapper: VueWrapper | undefined

function mountView() {
  const router = createRouter({
    history: createMemoryHistory(),
    routes: [{ path: '/:p(.*)*', component: { render: () => null } }]
  })
  wrapper = mount(DataSources, { global: { plugins: [router] } })
  return wrapper
}

describe('DataSources load states (#316)', () => {
  beforeEach(() => {
    getDataSources.mockReset()
  })
  afterEach(() => wrapper?.unmount())

  it('renders no invented zeros while loading', async () => {
    getDataSources.mockReturnValue(new Promise(() => {}))
    const w = mountView()
    await flushPromises()

    expect(w.text()).not.toContain('Never')
    expect(w.text()).not.toContain('Active Sources')
    expect(w.find('[aria-busy="true"]').exists()).toBe(true)
  })

  it('shows a retryable error without zeros on API failure', async () => {
    getDataSources.mockRejectedValue(
      Object.assign(new Error('Network Error'), { isAxiosError: true })
    )
    const w = mountView()
    await flushPromises()

    expect(w.text()).toContain("Couldn't load data sources from the server.")
    expect(w.text()).not.toContain('Active Sources')
    expect(w.text()).not.toContain('Never')
    getDataSources.mockResolvedValue({
      total_active: 1,
      total_unique_genes: 42,
      sources: [{ name: 'ClinGen', status: 'active', stats: { gene_count: 42 } }]
    } as never)
    await w
      .findAll('button')
      .find(b => b.text() === 'Try again')!
      .trigger('click')
    await flushPromises()
    expect(getDataSources).toHaveBeenCalledTimes(2)
    expect(w.text()).toContain('ClinGen')
    expect(w.text()).toContain('Active Sources')
  })

  it('shows empty copy for a successful empty response', async () => {
    getDataSources.mockResolvedValue({ total_active: 0, sources: [] } as never)
    const w = mountView()
    await flushPromises()

    expect(w.text()).toContain('No data sources available.')
    expect(w.text()).not.toContain("Couldn't load")
  })
})

describe('DataSources loading layout (#324)', () => {
  afterEach(() => wrapper?.unmount())

  it('reserves the final layout while loading: source-card grid and summary card', async () => {
    getDataSources.mockReset()
    getDataSources.mockReturnValue(new Promise(() => {}))
    const w = mountView()
    await flushPromises()

    const busy = w.find('[aria-busy="true"]')
    expect(busy.findAll('.grid > [data-slot="card"]')).toHaveLength(7)
    expect(busy.text()).toContain('Database Summary')
    // The API sends no source.type, so loaded headers have the name row only
    const header = busy.find('.grid > [data-slot="card"] > div')
    expect(header.findAll('div')).toHaveLength(1)
  })
})

describe('DataSources counts', () => {
  afterEach(() => wrapper?.unmount())

  it('shows API counts with their denominators and literature publications', async () => {
    getDataSources.mockReset()
    getDataSources.mockResolvedValue({
      total_active: 6,
      total_sources: 7,
      source_coverage: 35,
      total_unique_genes: 2045,
      sources: [
        {
          name: 'Literature',
          status: 'active',
          stats: { gene_count: 814, metadata: { publications: 12 } }
        },
        {
          name: 'DiagnosticPanels',
          status: 'active',
          stats: { gene_count: 965, metadata: { providers: 1, panels: 32 } }
        },
        { name: 'PubTator', status: 'inactive', stats: null }
      ]
    } as never)
    const w = mountView()
    await flushPromises()

    expect(w.text()).toContain('6 of 7')
    expect(w.text()).toMatch(/35%\s*of Genes with 2\+ Sources/)
    expect(w.text()).toContain('12Publications')
    expect(w.text()).toContain('1Provider')
    expect(w.text()).not.toContain('Providers')
    expect(w.text()).toContain('Inactive')
  })
})
