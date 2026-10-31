/**
 * GeneDetail load states: API failure vs 404 vs success (#316).
 */

import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest'
import { flushPromises, mount } from '@vue/test-utils'
import type { VueWrapper } from '@vue/test-utils'
import { defineComponent, h } from 'vue'
import { createPinia } from 'pinia'
import { createRouter, createMemoryHistory, RouterView } from 'vue-router'
import { TooltipProvider } from '@/components/ui/tooltip'
import GeneDetail from '@/views/GeneDetail.vue'

vi.mock('@unhead/vue', () => ({ useHead: vi.fn() }))
vi.mock('@/api/genes', () => ({
  geneApi: { getGene: vi.fn(), getGeneEvidence: vi.fn(), getGeneAnnotations: vi.fn() }
}))
import { geneApi } from '@/api/genes'
vi.mock('@/api/curation', async importOriginal => ({
  ...(await importOriginal<typeof import('@/api/curation')>()),
  curationApi: { listPublished: vi.fn() }
}))
import { curationApi } from '@/api/curation'

vi.stubGlobal('logService', { info: vi.fn(), warn: vi.fn(), error: vi.fn(), debug: vi.fn() })

const httpError = (status?: number) =>
  Object.assign(new Error(status ? `Request failed with status code ${status}` : 'Network Error'), {
    isAxiosError: true,
    response: status ? { status } : undefined
  })

let wrapper: VueWrapper | undefined

async function mountGene(symbol = 'PKD1') {
  const router = createRouter({
    history: createMemoryHistory(),
    routes: [
      { path: '/genes/:symbol', component: GeneDetail },
      { path: '/genes', component: { render: () => null } }
    ]
  })
  await router.push(`/genes/${symbol}`)
  await router.isReady()
  wrapper = mount(defineComponent({ render: () => h(TooltipProvider, () => h(RouterView)) }), {
    global: { plugins: [router, createPinia()], stubs: { GeneInformationCard: true } }
  })
  await flushPromises()
  return wrapper
}

const retryButton = (w: VueWrapper) => w.findAll('button').find(b => b.text() === 'Retry')

describe('GeneDetail load states (#316)', () => {
  beforeEach(() => {
    vi.mocked(geneApi.getGene).mockReset()
    vi.mocked(geneApi.getGeneEvidence)
      .mockReset()
      .mockResolvedValue({ evidence: [] } as never)
    vi.mocked(geneApi.getGeneAnnotations)
      .mockReset()
      .mockResolvedValue({} as never)
    vi.mocked(curationApi.listPublished)
      .mockReset()
      .mockResolvedValue({ data: [], meta: { total: 0, limit: 100, offset: 0 } } as never)
  })
  afterEach(() => {
    wrapper?.unmount()
    vi.useRealTimers()
  })

  it.each([
    ['500', httpError(500)],
    ['network error', httpError()]
  ])('shows a retryable error, not "not found", on %s', async (_, err) => {
    vi.mocked(geneApi.getGene).mockRejectedValue(err)
    const w = await mountGene()

    expect(w.text()).toContain("Couldn't load gene data from the server.")
    expect(w.text()).not.toContain('could not be found')
    vi.mocked(geneApi.getGene).mockResolvedValue({
      id: 1,
      approved_symbol: 'PKD1'
    } as never)
    await retryButton(w)!.trigger('click')
    await flushPromises()
    expect(geneApi.getGene).toHaveBeenCalledTimes(2)
    expect(w.find('h1').text()).toBe('PKD1')
    // Breadcrumbs are router links, not full page loads
    const crumb = w.get('nav a[href="/genes"]')
    expect(crumb.text()).toBe('Genes')
  })

  it('shows not-found copy only for HTTP 404', async () => {
    vi.mocked(geneApi.getGene).mockRejectedValue(httpError(404))
    const w = await mountGene('NOPE1')

    expect(w.text()).toContain('The gene "NOPE1" could not be found in our database.')
    expect(retryButton(w)).toBeUndefined()
    expect(w.find('h1').text()).toBe('Gene Not Found')
    // #322: link styled as a button, not a button nested inside a link
    const back = w.get('a[href="/genes"]')
    expect(back.text()).toContain('Back to Gene Browser')
    expect(back.find('button').exists()).toBe(false)
  })

  it('tells an evidence failure apart from no evidence', async () => {
    vi.mocked(geneApi.getGene).mockResolvedValue({ id: 1, approved_symbol: 'PKD1' } as never)
    vi.mocked(geneApi.getGeneEvidence).mockRejectedValue(httpError(503))
    const w = await mountGene()

    expect(w.text()).toContain("Couldn't load evidence from the server.")
    expect(w.text()).not.toContain('No evidence records available')
    vi.mocked(geneApi.getGeneEvidence).mockResolvedValue({ evidence: [] } as never)
    await retryButton(w)!.trigger('click')
    await flushPromises()
    expect(geneApi.getGeneEvidence).toHaveBeenCalledTimes(2)
    expect(w.text()).toContain('No evidence records available')
  })

  it('reveals the body once, after annotations and curated records settle', async () => {
    vi.mocked(geneApi.getGene).mockResolvedValue({ id: 1, approved_symbol: 'HNF1B' } as never)
    let resolveAnnotations: (_v: unknown) => void = () => {}
    vi.mocked(geneApi.getGeneAnnotations).mockReturnValue(
      new Promise(r => (resolveAnnotations = r)) as never
    )
    const w = await mountGene('HNF1B')

    // Evidence starts with the gene call; the body waits for the above-the-fold calls
    expect(geneApi.getGeneEvidence).toHaveBeenCalledWith('HNF1B')
    expect(curationApi.listPublished).toHaveBeenCalledWith({ gene_symbol: 'HNF1B' })
    expect(w.text()).not.toContain('Evidence by source')

    resolveAnnotations({})
    await flushPromises()
    expect(w.text()).toContain('Evidence by source')
  })

  it('shows no curated card when the curated request fails', async () => {
    vi.mocked(geneApi.getGene).mockResolvedValue({ id: 1, approved_symbol: 'PKD1' } as never)
    vi.mocked(curationApi.listPublished).mockRejectedValue(httpError(503))
    const w = await mountGene()

    expect(w.text()).toContain('Evidence by source')
    expect(w.text()).not.toContain('Expert-reviewed')
  })

  it('renders the gene progressively when annotations exceed the reveal budget', async () => {
    vi.useFakeTimers({ toFake: ['setTimeout'] })
    vi.mocked(geneApi.getGene).mockResolvedValue({
      id: 1,
      approved_symbol: 'HNF1B',
      hgnc_id: 'HGNC:11630'
    } as never)
    let resolveAnnotations: (_v: unknown) => void = () => {}
    vi.mocked(geneApi.getGeneAnnotations).mockReturnValue(
      new Promise(r => (resolveAnnotations = r)) as never
    )
    const w = await mountGene('HNF1B')
    await vi.advanceTimersByTimeAsync(1000)
    await flushPromises()

    expect(w.find('h1').text()).toBe('HNF1B')
    expect(w.text()).toContain('No evidence records available')
    expect(w.findAll('[data-state="loading"]').length).toBeGreaterThan(0)

    resolveAnnotations({
      annotations: { hgnc: [{ data: { name: 'HNF1 homeobox B', hgnc_id: 'HGNC:11630' } }] }
    })
    await flushPromises()
    expect(w.get('[data-testid="gene-identity"]').text()).toContain('HNF1 homeobox B')
  })
})
