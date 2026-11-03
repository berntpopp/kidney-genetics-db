/**
 * Curated gene-disease association state (#26)
 */

import { defineStore } from 'pinia'
import { ref } from 'vue'
import {
  curationApi,
  type Association,
  type AssociationInput,
  type SortKey,
  type WorkflowAction
} from '@/api/curation'

type ApiError = {
  response?: { data?: { detail?: unknown; error?: { message?: string; detail?: string } } }
}

/** Readable message from the app's error envelopes ({error: {message|detail}}) or FastAPI {detail} */
export function errorMessage(err: unknown): string {
  const data = (err as ApiError).response?.data
  const detail = typeof data?.detail === 'string' ? data.detail : undefined
  return data?.error?.message ?? data?.error?.detail ?? detail ?? 'Request failed'
}

/** Rows per page of the curation lists */
export const PAGE_SIZES = [25, 50, 100]

export interface PageQuery {
  q: string
  /** Zero-based */
  page: number
  size: number
  /** Classifications to show; empty shows all */
  strengths: string[]
  sortBy: SortKey
  sortOrder: 'asc' | 'desc'
}

/** A list's state before any search, filter, sort or paging */
export const defaultQuery = (): PageQuery => ({
  q: '',
  page: 0,
  size: PAGE_SIZES[0]!,
  strengths: [],
  sortBy: 'gene',
  sortOrder: 'asc'
})

export const useCurationStore = defineStore('curation', () => {
  const published = ref<Association[]>([])
  const workflow = ref<Association[]>([])
  const publishedTotal = ref(0)
  const workflowTotal = ref(0)
  const loading = ref(false)
  const error = ref<string | null>(null)

  async function run<T>(fn: () => Promise<T>): Promise<T | null> {
    loading.value = true
    error.value = null
    try {
      return await fn()
    } catch (err: unknown) {
      error.value = errorMessage(err)
      return null
    } finally {
      loading.value = false
    }
  }

  /** Server-side page state of each list; writes and the URL reuse it */
  const publishedQuery = ref<PageQuery>(defaultQuery())
  const workflowQuery = ref<PageQuery & { pendingHuman: boolean }>({
    ...defaultQuery(),
    pendingHuman: false
  })
  const pendingHumanTotal = ref(0)

  const pageParams = ({ q, page, size, strengths, sortBy, sortOrder }: PageQuery) => ({
    q: q.trim() || undefined,
    evidence_strength: strengths.length ? strengths : undefined,
    sort_by: sortBy,
    sort_order: sortOrder,
    limit: size,
    offset: page * size
  })

  // Only the latest request of a list may write it, so a slow earlier search never wins
  let publishedSeq = 0
  async function loadPublished(query: Partial<PageQuery> = {}): Promise<void> {
    publishedQuery.value = { ...publishedQuery.value, ...query }
    const seq = ++publishedSeq
    const res = await run(() => curationApi.listPublished(pageParams(publishedQuery.value)))
    if (!res || seq !== publishedSeq) return
    ;[published.value, publishedTotal.value] = [res.data, res.meta.total]
    // A write emptied the last page: show the new last page instead
    const last = Math.max(0, Math.ceil(res.meta.total / publishedQuery.value.size) - 1)
    if (!res.data.length && publishedQuery.value.page > last) await loadPublished({ page: last })
  }

  let workflowSeq = 0
  /** Without run(), so a refused decision can refresh the list and keep its error */
  async function fetchWorkflow(): Promise<void> {
    const seq = ++workflowSeq
    const query = workflowQuery.value
    const [res, pending] = await Promise.all([
      curationApi.listWorkflow({
        ...pageParams(query),
        pending_human: query.pendingHuman || undefined
      }),
      curationApi.listWorkflow({ pending_human: true, limit: 1 })
    ])
    if (seq !== workflowSeq) return
    ;[workflow.value, workflowTotal.value] = [res.data, res.meta.total]
    pendingHumanTotal.value = pending.meta.total
    const last = Math.max(0, Math.ceil(res.meta.total / query.size) - 1)
    if (!res.data.length && query.page > last) {
      workflowQuery.value = { ...query, page: last }
      await fetchWorkflow()
    }
  }

  async function loadWorkflow(
    query: Partial<PageQuery & { pendingHuman: boolean }> = {}
  ): Promise<void> {
    workflowQuery.value = { ...workflowQuery.value, ...query }
    await run(fetchWorkflow)
  }

  /** Every published record matching the current search, for exports (not just one page) */
  async function fetchAllPublished(): Promise<Association[] | null> {
    return run(async () => {
      const all: Association[] = []
      const params = { ...pageParams(publishedQuery.value), limit: 1000 } // the backend maximum
      for (let offset = 0; ; offset += params.limit) {
        const res = await curationApi.listPublished({ ...params, offset })
        all.push(...res.data)
        if (!res.data.length || all.length >= res.meta.total) return all
      }
    })
  }

  /** Apply a write, then refresh both lists so status changes show everywhere */
  async function write(fn: () => Promise<Association>): Promise<Association | null> {
    const record = await run(fn)
    if (record) await Promise.all([loadWorkflow(), loadPublished()])
    return record
  }

  const create = (input: AssociationInput) => write(() => curationApi.create(input))
  const update = (id: number, input: Partial<AssociationInput>) => {
    const changes = { ...input }
    delete changes.gene_symbol // the gene is fixed once a record exists
    return write(() => curationApi.update(id, changes))
  }
  async function transition(record: Association, action: WorkflowAction) {
    const saved = await write(() => curationApi.transition(record, action))
    // A refused decision (e.g. 409: changed since loaded) shows the current version, keeping the error
    if (!saved) await fetchWorkflow().catch(() => null)
    return saved
  }

  return {
    published,
    workflow,
    publishedTotal,
    workflowTotal,
    publishedQuery,
    workflowQuery,
    pendingHumanTotal,
    loading,
    error,
    loadPublished,
    loadWorkflow,
    fetchAllPublished,
    create,
    update,
    transition
  }
})
