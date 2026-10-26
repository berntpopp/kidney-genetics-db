/**
 * Curated gene-disease association state (#26)
 */

import { defineStore } from 'pinia'
import { ref } from 'vue'
import {
  curationApi,
  type Association,
  type AssociationInput,
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

  let lastGene: string | undefined
  // ponytail: one page at the backend maximum; the view says when more exist. Paginate if lists grow.
  const LIMIT = 1000

  async function loadPublished(geneSymbol: string | undefined = lastGene): Promise<void> {
    lastGene = geneSymbol || undefined
    const res = await run(() => curationApi.listPublished({ gene_symbol: lastGene, limit: LIMIT }))
    if (res) [published.value, publishedTotal.value] = [res.data, res.meta.total]
  }

  async function loadWorkflow(): Promise<void> {
    const res = await run(() => curationApi.listWorkflow({ limit: LIMIT }))
    if (res) [workflow.value, workflowTotal.value] = [res.data, res.meta.total]
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
    if (!saved) {
      const res = await curationApi.listWorkflow({ limit: LIMIT }).catch(() => null)
      if (res) [workflow.value, workflowTotal.value] = [res.data, res.meta.total]
    }
    return saved
  }

  return {
    published,
    workflow,
    publishedTotal,
    workflowTotal,
    loading,
    error,
    loadPublished,
    loadWorkflow,
    create,
    update,
    transition
  }
})
