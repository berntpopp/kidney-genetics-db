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
    .find(`[data-testid="wf-${id}"] [data-testid="wf-actions"]`)
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
    const row = w.find('[data-testid="gda-row"]')
    // The row counts the citations; the PMID links are in the details row
    expect(row.text()).toContain('1 PubMed citation')
    await row
      .findAll('button')
      .find(b => b.text().includes('Details'))!
      .trigger('click')
    const hrefs = w.findAll('a').map(a => a.attributes('href'))
    expect(hrefs).toContain('https://omim.org/entry/173900')
    expect(hrefs).toContain('https://pubmed.ncbi.nlm.nih.gov/1/')
  })

  it('fetches only the workflow list when the session resolves after mount', async () => {
    const w = await mountAs(null)
    const auth = useAuthStore()
    auth.user = { id: 10, username: 'me', email: 'm@x', role: 'curator' } as never
    auth.accessToken = 'token'
    await flushPromises()
    expect(api.listPublished).toHaveBeenCalledTimes(1)
    expect(api.listWorkflow).toHaveBeenCalledTimes(1)
    expect(w.text()).toContain('Curation workflow')
  })

  it('shows points and AI assistance on the row, not only behind Details', async () => {
    api.listPublished.mockResolvedValue(
      page([
        {
          ...RECORDS[3]!,
          scores: { genetic: 10, experimental: 6, total: 16 },
          external_curator: 'Alice Smith',
          ai_agents: ['model-x']
        }
      ])
    )
    const row = (await mountAs(null)).find('[data-testid="gda-row"]')
    expect(row.text()).toContain('16 points')
    expect(row.text()).toContain('AI-assisted curation')
  })

  it('gates workflow buttons by authorship and status', async () => {
    const w = await mountAs('curator')
    expect(labels(w, 1)).toEqual(['Edit', 'Submit for review'])
    expect(labels(w, 2)).toEqual([]) // own record awaiting someone else's review
    expect(w.find('[data-testid="wf-2"]').text()).toContain('Awaiting review by another curator')
    expect(w.find('[data-testid="wf-3"]').text()).not.toContain('Awaiting review')
    expect(labels(w, 3)).toEqual(['Publish', 'Return to draft'])
    expect(labels(w, 4)).toEqual(['Return to draft'])
  })

  it('lets any curator take over an unedited Gene Curator import (#448)', async () => {
    const imported = { ...RECORDS[0]!, id: 5, curator_id: 99, imported_unclaimed: true }
    const claimed = { ...imported, id: 6, disease_id: 'MONDO:0000006', imported_unclaimed: false }
    api.listWorkflow.mockResolvedValue(page([imported, claimed]))
    const w = await mountAs('curator')
    expect(labels(w, 5)).toEqual(['Edit', 'Submit for review'])
    expect(labels(w, 6)).toEqual([])
    const gc = { source: 'gene_curator' } as const
    api.listWorkflow.mockResolvedValue(
      page([
        { ...imported, ...gc },
        { ...claimed, ...gc }
      ])
    )
    const w2 = await mountAs('curator')
    expect(w2.find('[data-testid="wf-5"]').text()).toContain('Gene Curator import, unclaimed')
    expect(w2.find('[data-testid="wf-6"]').text()).not.toContain('unclaimed')
  })

  it('says a gene filter matched nothing rather than that nothing is published', async () => {
    api.listPublished.mockResolvedValue(page([]))
    const w = await mountAs(null)
    expect(w.text()).toContain('No published associations yet.')
    await w.find('#gda-filter').setValue('PKD1')
    await w.find('#gda-filter').element.form!.dispatchEvent(new Event('submit'))
    await flushPromises()
    expect(api.listPublished).toHaveBeenLastCalledWith({ gene_symbol: 'PKD1', limit: 1000 })
    expect(w.text()).toContain('No published associations for PKD1.')
  })

  it('renders a record without citations without an empty citation list', async () => {
    api.listPublished.mockResolvedValue(page([{ ...RECORDS[3]!, citations: [] }]))
    const w = await mountAs(null)
    const row = w.find('[data-testid="gda-row"]')
    expect(row.exists()).toBe(true)
    expect(row.find('[data-slot="ontology-term-list"]').exists()).toBe(false)
    expect(row.text()).not.toContain('adopted from ClinGen')
  })

  it('says an adopted ClinGen record without PMIDs points to ClinGen', async () => {
    const adopted = {
      ...RECORDS[3]!,
      citations: [],
      methodology: 'ClinGen gene-disease validity (adopted)',
      adopted_clingen: { id: 'CGGV:a' }
    }
    api.listPublished.mockResolvedValue(page([adopted as unknown as Association]))
    const w = await mountAs(null)
    expect(w.find('[data-testid="gda-row"]').text()).toContain(
      'Classification adopted from ClinGen'
    )
  })

  it('cites ClinGen beside our own curation and marks a different class', async () => {
    const ours = {
      ...RECORDS[3]!,
      relationship_type: 'mendelian',
      evidence_strength: 'Strong',
      methodology: 'KGDB Gene-Disease Validity',
      adopted_clingen: { id: 'CGGV:a', classification: 'Definitive' }
    }
    api.listPublished.mockResolvedValue(page([ours as unknown as Association]))
    const text = (await mountAs(null)).find('[data-testid="gda-row"]').text()
    expect(text).toContain('ClinGen: Definitive (differs)')
    expect(text).not.toContain('adopted from ClinGen')
  })

  it('publishes through the store', async () => {
    api.transition.mockResolvedValue(RECORDS[2]!)
    const w = await mountAs('curator')
    await w.find('[data-testid="wf-3"] [data-testid="wf-actions"] button').trigger('click')
    await flushPromises()
    expect(api.transition).toHaveBeenCalledWith(RECORDS[2], 'publish')
  })

  it('shows the reviewer the evidence they approve (#376)', async () => {
    const reviewed = { ...RECORDS[2]!, evidence_summary: 'Three families', citations: ['PMID:7'] }
    api.listWorkflow.mockResolvedValue(page([reviewed]))
    const w = await mountAs('curator')
    const row = w.find('[data-testid="wf-3"]')
    expect(row.text()).toContain('Definitive')
    expect(row.text()).toContain('Three families')
    await row
      .findAll('button')
      .find(b => b.text().includes('Details'))!
      .trigger('click')
    const details = w.find('[data-testid="wf-3-details"]')
    expect(details.find('a[href*="pubmed"]').attributes('href')).toBe(
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
    await w.find('[data-testid="wf-3"] [data-testid="wf-actions"] button').trigger('click')
    await flushPromises()
    expect(api.listWorkflow).toHaveBeenCalled()
    expect(w.find('[role="alert"]').text()).toContain('changed since you loaded it')
  })

  it('lists susceptibility records in their own table, not as a Mendelian class', async () => {
    const risk = {
      ...RECORDS[3]!,
      id: 5,
      disease_id: 'MONDO:0000005',
      relationship_type: 'susceptibility',
      evidence_strength: 'Likely association'
    } as Association
    api.listPublished.mockResolvedValue(page([RECORDS[3]!, risk]))
    const w = await mountAs(null)
    const mendelian = w.find('[data-testid="published-mendelian"]')
    const susceptibility = w.find('[data-testid="published-susceptibility"]')
    expect(mendelian.text()).toContain('OMIM:173900')
    expect(mendelian.text()).not.toContain('Likely association')
    expect(susceptibility.text()).toContain('Likely association')
  })

  it('shows one class chip per susceptibility row, with or without a risk allele', async () => {
    const risk = (id: number, risk_allele: string | null) =>
      ({
        ...RECORDS[3]!,
        id,
        disease_id: 'MONDO:0013860',
        relationship_type: 'susceptibility',
        evidence_strength: 'Likely association',
        risk_allele
      }) as Association
    api.listPublished.mockResolvedValue(page([risk(5, null), risk(6, 'rs17831251 C')]))
    const rows = (await mountAs(null)).findAll('[data-testid="gda-row"]')
    expect(rows.map(r => r.text().split('Likely association').length - 1)).toEqual([1, 1])
    expect(rows[1]!.text()).toContain('rs17831251 C')
  })

  it('marks Gene Curator imports in the workflow and shows their provenance', async () => {
    const imported = {
      ...RECORDS[2]!,
      source: 'gene_curator',
      external_id: 'GC-7',
      external_url: 'https://example.org/c/7',
      moi: 'HP:0000006',
      moi_label: 'Autosomal dominant inheritance'
    } as Association
    api.listWorkflow.mockResolvedValue(page([imported]))
    const w = await mountAs('curator')
    const row = w.find('[data-testid="wf-3"]')
    expect(row.text()).toContain('Gene Curator import')
    expect(row.find('[data-testid="moi"]').text()).toContain('AD')
    expect(row.find('[data-testid="moi"]').text()).toContain('Autosomal dominant inheritance')
    // Provenance sits behind the row's Details toggle
    const toggle = row.findAll('button').find(b => b.text().includes('Details'))!
    expect(toggle.attributes('aria-expanded')).toBe('false')
    await toggle.trigger('click')
    const details = w.find('[data-testid="wf-3-details"]')
    expect(toggle.attributes('aria-expanded')).toBe('true')
    expect(details.find('a[href="https://example.org/c/7"]').exists()).toBe(true)
  })

  it('lets long evidence and disease cells wrap instead of widening the table', async () => {
    // TableCell defaults to whitespace-nowrap; long diagnostics pushed Actions off-screen
    const w = await mountAs('curator')
    const cells = w.find('[data-testid="wf-3"]').findAll('td')
    // MOI, Classification, Evidence, Status, Actions (gene and disease are in the pair header)
    expect(cells[2]!.classes()).toContain('whitespace-normal')
    expect(cells[4]!.classes()).not.toContain('whitespace-nowrap')
  })

  it('groups records of one gene-disease pair under one header with MOI per row', async () => {
    const pair = (id: number, moi: string, label: string) =>
      ({
        ...RECORDS[3]!,
        id,
        disease_id: 'MONDO:0004691',
        disease_name: 'autosomal dominant polycystic kidney disease',
        moi,
        moi_label: label
      }) as Association
    api.listPublished.mockResolvedValue(
      page([
        pair(11, 'HP:0000006', 'Autosomal dominant inheritance'),
        pair(12, 'HP:0000007', 'Autosomal recessive inheritance')
      ])
    )
    const w = await mountAs(null)
    const table = w.find('[data-testid="published-mendelian"]')
    const headers = table.findAll('[data-testid="gda-pair"]')
    expect(headers).toHaveLength(1)
    expect(headers[0]!.text()).toContain('PKD1')
    expect(headers[0]!.text()).toContain('autosomal dominant polycystic kidney disease')
    const rows = table.findAll('[data-testid="gda-row"]')
    expect(rows.map(r => r.find('[data-testid="moi"] [aria-hidden="true"]').text())).toEqual([
      'AD',
      'AR'
    ])
    expect(headers[0]!.text()).toContain('2 records')
  })

  it('says when a list is truncated at the server maximum', async () => {
    api.listPublished.mockResolvedValue({
      data: [RECORDS[3]!],
      meta: { total: 1500, limit: 1000, offset: 0 }
    })
    const w = await mountAs(null)
    expect(w.text()).toContain('Showing 1 of 1500')
  })

  it('marks AI-approved imports and lets a curator mark them human-reviewed (#639)', async () => {
    const ai = {
      ...RECORDS[3]!,
      id: 5,
      disease_id: 'MONDO:0000005',
      source: 'gene_curator',
      approval_kind: 'ai',
      approval_model: 'model-x'
    } as Association
    const reviewed = { ...ai, id: 6, disease_id: 'MONDO:0000006', human_reviewed_at: '2026-10-31' }
    api.listPublished.mockResolvedValue(page([ai, reviewed, RECORDS[3]!]))
    api.listWorkflow.mockResolvedValue(page([...RECORDS, ai]))
    api.transition.mockResolvedValue(ai)
    const w = await mountAs('curator')
    const rows = w.findAll('[data-testid="gda-row"]').map(r => r.text())
    expect(rows.filter(t => t.includes('AI-reviewed · pending human review'))).toHaveLength(1)
    expect(rows.filter(t => t.includes('Human-reviewed'))).toHaveLength(1)
    expect(labels(w, 5)).toEqual(['Mark human-reviewed', 'Return to draft'])
    expect(labels(w, 4)).toEqual(['Return to draft'])

    const filter = w.find('[data-testid="wf-pending-human"]')
    expect(filter.text()).toBe('Pending human review (1)')
    await filter.trigger('click')
    expect(filter.attributes('aria-pressed')).toBe('true')
    expect(w.find('[data-testid="wf-4"]').exists()).toBe(false)
    await w.find('[data-testid="wf-5"] [data-testid="wf-actions"] button').trigger('click')
    await flushPromises()
    expect(api.transition).toHaveBeenCalledWith(ai, 'human-review')
  })
})
