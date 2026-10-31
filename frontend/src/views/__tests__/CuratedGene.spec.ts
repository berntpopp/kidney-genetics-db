import { describe, it, expect, vi, beforeEach } from 'vitest'
import { h } from 'vue'
import { flushPromises, mount } from '@vue/test-utils'
import { createPinia } from 'pinia'
import { createHead } from '@unhead/vue/client'
import { createRouter, createMemoryHistory } from 'vue-router'

vi.stubGlobal('logService', { info: vi.fn(), warn: vi.fn(), error: vi.fn(), debug: vi.fn() })
vi.mock('@/api/curation', async importOriginal => ({
  ...(await importOriginal<typeof import('@/api/curation')>()),
  curationApi: { listPublished: vi.fn() }
}))

vi.mock('@/api/genes', () => ({
  geneApi: {
    getGene: vi
      .fn()
      .mockResolvedValue({ evidence_score: 87.34, evidence_tier: 'comprehensive_support' })
  }
}))

import { curationApi, type Association } from '@/api/curation'
import { TooltipProvider } from '@/components/ui/tooltip'
import CuratedGene from '@/views/CuratedGene.vue'

const api = vi.mocked(curationApi)
const RECORD = {
  id: 1,
  gene_id: 1,
  gene_symbol: 'CLDN10',
  disease_id: 'MONDO:0060564',
  disease_name: 'HELIX syndrome',
  relationship_type: 'mendelian',
  evidence_strength: 'Definitive',
  moi: 'HP:0000007',
  citations: ['PMID:28686597'],
  evidence_summary: 'Biallelic loss of function causes HELIX syndrome.',
  status: 'published',
  curator_id: 1,
  reviewer_id: 2,
  created_at: '2026-10-31T00:00:00Z',
  updated_at: '2026-10-31T00:00:00Z',
  submitted_at: null,
  reviewed_at: null,
  published_at: '2026-10-31T00:00:00Z'
} as Association

const mountFor = async (symbol: string) => {
  const router = createRouter({
    history: createMemoryHistory(),
    routes: [{ path: '/:rest(.*)', component: { render: () => null } }]
  })
  const wrapper = mount(
    { render: () => h(TooltipProvider, () => h(CuratedGene, { symbol })) },
    {
      global: { plugins: [router, createPinia(), createHead()] }
    }
  )
  await flushPromises()
  return wrapper
}

describe('CuratedGene', () => {
  beforeEach(() => vi.clearAllMocks())

  it("shows only that gene's published associations, linking to the gene page", async () => {
    api.listPublished.mockResolvedValue({
      data: [RECORD],
      meta: { total: 1, limit: 100, offset: 0 }
    })
    const w = await mountFor('CLDN10')
    expect(api.listPublished).toHaveBeenCalledWith({ gene_symbol: 'CLDN10' })
    expect(w.find('h1').text()).toBe('CLDN10')
    expect(w.text()).toContain('HELIX syndrome')
    expect(w.text()).toContain('Biallelic loss of function')
    expect(w.find('a[href="/genes/CLDN10"]').exists()).toBe(true)
    expect(w.find('a[href="/curation/associations"]').text()).toBe('Curated Associations') // breadcrumb only
    expect(w.findAll('h2')).toHaveLength(0)
    const score = w.find('[data-testid="kgdb-score"]').text()
    expect(score).toContain('87.3')
    expect(score).toContain('not changed by these curations')
    expect(w.find('a[href="/about#scoring"]').exists()).toBe(true)
    expect(w.find('a[href="/about#curation"]').exists()).toBe(true)
  })

  it('says so when the gene has no published association', async () => {
    api.listPublished.mockResolvedValue({ data: [], meta: { total: 0, limit: 100, offset: 0 } })
    const w = await mountFor('PKD1')
    expect(w.text()).toContain('No published expert-reviewed associations for PKD1.')
  })
})
