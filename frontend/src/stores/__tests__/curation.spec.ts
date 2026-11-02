import { describe, it, expect, vi, beforeEach } from 'vitest'
import { setActivePinia, createPinia } from 'pinia'

vi.mock('@/api/curation', () => ({
  curationApi: {
    listPublished: vi.fn(),
    listWorkflow: vi.fn(),
    create: vi.fn(),
    update: vi.fn(),
    transition: vi.fn()
  }
}))

import { curationApi } from '@/api/curation'
import { useCurationStore } from '@/stores/curation'

const api = vi.mocked(curationApi)
const has = (o: object) => expect.objectContaining(o)
const page = (data: unknown[] = []) => ({
  data,
  meta: { total: data.length, limit: 100, offset: 0 }
})
const rec = { id: 7, status: 'draft' } as never

describe('curation store', () => {
  beforeEach(() => {
    setActivePinia(createPinia())
    vi.clearAllMocks()
    api.listPublished.mockResolvedValue(page() as never)
    api.listWorkflow.mockResolvedValue(page([rec]) as never)
  })

  it('loads one page and keeps search and page when a write refreshes it', async () => {
    const store = useCurationStore()
    api.listPublished.mockResolvedValue({
      data: [rec],
      meta: { total: 60, limit: 25, offset: 25 }
    } as never)
    await store.loadPublished({ q: ' pkd ', page: 1 })
    const params = { q: 'pkd', limit: 25, offset: 25 }
    expect(api.listPublished).toHaveBeenCalledWith(has(params))
    expect(store.publishedTotal).toBe(60)
    api.create.mockResolvedValue(rec)
    await store.create({} as never)
    expect(api.listPublished).toHaveBeenLastCalledWith(has(params))
  })

  it('moves to the new last page when a write empties the current one', async () => {
    const store = useCurationStore()
    api.listPublished
      .mockResolvedValueOnce({ data: [], meta: { total: 25, limit: 25, offset: 25 } } as never)
      .mockResolvedValueOnce({ data: [rec], meta: { total: 25, limit: 25, offset: 0 } } as never)
    await store.loadPublished({ page: 1 })
    expect(api.listPublished).toHaveBeenLastCalledWith(has({ q: undefined, limit: 25, offset: 0 }))
    expect(store.publishedQuery.page).toBe(0)
    expect(store.published).toEqual([rec])
  })

  it('ignores a slower earlier response', async () => {
    const store = useCurationStore()
    let resolveSlow!: (_v: unknown) => void
    api.listPublished
      .mockReturnValueOnce(new Promise(r => (resolveSlow = r)) as never)
      .mockResolvedValueOnce(page([rec]) as never)
    const slow = store.loadPublished({ q: 'p' })
    await store.loadPublished({ q: 'pkd1' })
    resolveSlow(page([{ id: 1 }]))
    await slow
    expect(store.published).toEqual([rec])
  })

  it('pages the workflow, filters pending human review and counts it', async () => {
    const store = useCurationStore()
    api.listWorkflow.mockImplementation((async (p: { pending_human?: boolean }) => ({
      data: [rec],
      meta: { total: p.pending_human ? 3 : 40, limit: 25, offset: 0 }
    })) as never)
    await store.loadWorkflow({ pendingHuman: true, q: 'col4' })
    expect(api.listWorkflow).toHaveBeenCalledWith(
      has({
        q: 'col4',
        limit: 25,
        offset: 0,
        pending_human: true
      })
    )
    expect(api.listWorkflow).toHaveBeenCalledWith({ pending_human: true, limit: 1 })
    expect([store.workflowTotal, store.pendingHumanTotal]).toEqual([3, 3])
  })

  it('exports every matching record across backend pages', async () => {
    const store = useCurationStore()
    await store.loadPublished({ q: 'pkd' })
    api.listPublished
      .mockResolvedValueOnce({
        data: [rec, rec],
        meta: { total: 3, limit: 1000, offset: 0 }
      } as never)
      .mockResolvedValueOnce({
        data: [rec],
        meta: { total: 3, limit: 1000, offset: 1000 }
      } as never)
    expect(await store.fetchAllPublished()).toHaveLength(3)
    expect(api.listPublished).toHaveBeenLastCalledWith(has({ q: 'pkd', limit: 1000, offset: 1000 }))
  })

  it('creates, updates (never the gene) and transitions, then refreshes lists', async () => {
    const store = useCurationStore()
    api.create.mockResolvedValue(rec)
    api.update.mockResolvedValue(rec)
    api.transition.mockResolvedValue(rec)
    await store.create({ gene_symbol: 'PKD1' } as never)
    expect(api.create).toHaveBeenCalledWith({ gene_symbol: 'PKD1' })
    await store.update(7, { gene_symbol: 'PKD1', disease_name: 'x' })
    expect(api.update).toHaveBeenCalledWith(7, { disease_name: 'x' })
    await store.transition(7, 'publish')
    expect(api.transition).toHaveBeenCalledWith(7, 'publish')
    expect(api.listWorkflow).toHaveBeenCalledTimes(6) // each refresh also counts pending review
    expect(store.workflow).toEqual([rec])
  })

  it('surfaces domain and validation errors', async () => {
    const store = useCurationStore()
    api.transition.mockRejectedValue({
      response: { data: { error: { message: 'Permission denied for reviewing this record' } } }
    })
    expect(await store.transition(7, 'publish')).toBeNull()
    expect(store.error).toContain('Permission denied')
    api.create.mockRejectedValue({
      response: { data: { error: { detail: "Validation failed for 'citations'" } } }
    })
    await store.create({} as never)
    expect(store.error).toBe("Validation failed for 'citations'")
  })
})
