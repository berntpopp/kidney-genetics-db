import { describe, it, expect, vi, beforeEach } from 'vitest'
import { flushPromises, mount } from '@vue/test-utils'
import { createPinia, setActivePinia } from 'pinia'
import { createRouter, createMemoryHistory } from 'vue-router'

vi.stubGlobal('logService', { info: vi.fn(), warn: vi.fn(), error: vi.fn(), debug: vi.fn() })
vi.mock('@/api/curation', async importOriginal => ({
  ...(await importOriginal<typeof import('@/api/curation')>()),
  curationApi: {
    listPublished: vi.fn(),
    listWorkflow: vi.fn(),
    create: vi.fn(),
    update: vi.fn(),
    transition: vi.fn()
  }
}))

import { curationApi, type Association } from '@/api/curation'
import { useAuthStore } from '@/stores/auth'
import CuratedAssociations from '@/views/CuratedAssociations.vue'

const api = vi.mocked(curationApi)
const base = {
  gene_id: 1,
  gene_symbol: 'PKD1',
  disease_name: 'ADPKD',
  evidence_strength: 'Definitive',
  citations: ['PMID:1'],
  evidence_summary: null,
  reviewer_id: null,
  created_at: '2026-10-26T00:00:00Z',
  updated_at: '2026-10-26T00:00:00Z',
  submitted_at: null,
  reviewed_at: null,
  published_at: null
} as const
const RECORDS: Association[] = [
  { ...base, id: 1, disease_id: 'MONDO:0000001', status: 'draft', curator_id: 10 },
  { ...base, id: 2, disease_id: 'MONDO:0000002', status: 'in_review', curator_id: 10 },
  { ...base, id: 3, disease_id: 'MONDO:0000003', status: 'in_review', curator_id: 20 },
  { ...base, id: 4, disease_id: 'OMIM:173900', status: 'published', curator_id: 20 }
]
const page = (data: Association[]) => ({
  data,
  meta: { total: data.length, limit: 100, offset: 0 }
})

async function mountAs(role: 'curator' | 'public' | null) {
  const pinia = createPinia()
  setActivePinia(pinia)
  if (role) {
    const auth = useAuthStore()
    auth.user = { id: 10, username: 'me', email: 'm@x', role } as never
    auth.accessToken = 'token'
  }
  const router = createRouter({
    history: createMemoryHistory(),
    routes: [{ path: '/:rest(.*)', component: { render: () => null } }]
  })
  const wrapper = mount(CuratedAssociations, { global: { plugins: [router, pinia] } })
  await flushPromises()
  return wrapper
}

const labels = (w: Awaited<ReturnType<typeof mountAs>>, id: number) =>
  w
    .find(`[data-testid="wf-${id}"]`)
    .findAll('button')
    .map(b => b.text())

describe('CuratedAssociations', () => {
  beforeEach(() => {
    vi.clearAllMocks()
    api.listPublished.mockResolvedValue(page([RECORDS[3]!]))
    api.listWorkflow.mockResolvedValue(page(RECORDS))
  })

  it('shows anonymous visitors published records with outbound links and no form', async () => {
    const w = await mountAs(null)
    expect(api.listWorkflow).not.toHaveBeenCalled()
    expect(w.find('form #gda-disease_id').exists()).toBe(false)
    const hrefs = w.findAll('a').map(a => a.attributes('href'))
    expect(hrefs).toContain('https://omim.org/entry/173900')
    expect(hrefs).toContain('https://pubmed.ncbi.nlm.nih.gov/1/')
  })

  it('gates workflow buttons by authorship and status', async () => {
    const w = await mountAs('curator')
    expect(labels(w, 1)).toEqual(['Edit', 'Submit for review'])
    expect(labels(w, 2)).toEqual([]) // own record awaiting someone else's review
    expect(labels(w, 3)).toEqual(['Publish', 'Return to draft'])
    expect(labels(w, 4)).toEqual(['Return to draft'])
  })

  it('publishes through the store', async () => {
    api.transition.mockResolvedValue(RECORDS[2]!)
    const w = await mountAs('curator')
    await w.find('[data-testid="wf-3"]').findAll('button')[0]!.trigger('click')
    await flushPromises()
    expect(api.transition).toHaveBeenCalledWith(RECORDS[2], 'publish')
  })

  it('shows the reviewer the evidence they approve (#376)', async () => {
    const reviewed = { ...RECORDS[2]!, evidence_summary: 'Three families', citations: ['PMID:7'] }
    api.listWorkflow.mockResolvedValue(page([reviewed]))
    const row = (await mountAs('curator')).find('[data-testid="wf-3"]')
    expect(row.text()).toContain('Definitive')
    expect(row.text()).toContain('Three families')
    expect(row.find('a[href*="pubmed"]').attributes('href')).toBe(
      'https://pubmed.ncbi.nlm.nih.gov/7/'
    )
  })

  it('reloads the current version and keeps the error when a decision is refused', async () => {
    api.transition.mockRejectedValue({
      response: {
        status: 409,
        data: { error: { detail: 'the record changed since you loaded it' } }
      }
    })
    const w = await mountAs('curator')
    api.listWorkflow.mockClear()
    await w.find('[data-testid="wf-3"]').findAll('button')[0]!.trigger('click')
    await flushPromises()
    expect(api.listWorkflow).toHaveBeenCalled()
    expect(w.find('[role="alert"]').text()).toContain('changed since you loaded it')
  })

  it('says when a list is truncated at the server maximum', async () => {
    api.listPublished.mockResolvedValue({
      data: [RECORDS[3]!],
      meta: { total: 1500, limit: 1000, offset: 0 }
    })
    const w = await mountAs(null)
    expect(w.text()).toContain('Showing 1 of 1500')
  })
})
