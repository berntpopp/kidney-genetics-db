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

  it('loads published records filtered by gene and keeps the filter on refresh', async () => {
    const store = useCurationStore()
    await store.loadPublished('PKD1')
    expect(api.listPublished).toHaveBeenCalledWith({ gene_symbol: 'PKD1', limit: 1000 })
    api.create.mockResolvedValue(rec)
    await store.create({} as never)
    expect(api.listPublished).toHaveBeenLastCalledWith({ gene_symbol: 'PKD1', limit: 1000 })
  })

  it('requests the backend maximum and keeps the server totals', async () => {
    const store = useCurationStore()
    api.listPublished.mockResolvedValue({
      data: [rec],
      meta: { total: 1500, limit: 1000, offset: 0 }
    } as never)
    await store.loadPublished()
    await store.loadWorkflow()
    expect(api.listWorkflow).toHaveBeenCalledWith({ limit: 1000 })
    expect(store.publishedTotal).toBe(1500)
    expect(store.workflowTotal).toBe(1)
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
    expect(api.listWorkflow).toHaveBeenCalledTimes(3)
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
