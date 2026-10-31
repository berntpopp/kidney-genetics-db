/**
 * One-shot Gene Curator export import (#448)
 * Admin module: functions return Promise<AxiosResponse<T>> (callers use .data)
 */

import apiClient from '@/api/client'
import type { AxiosResponse } from 'axios'

export interface ImportRow {
  curation_id: string
  gene_symbol: string
  hgnc_id: string
  entity_key: string
  record_id?: number
  reason?: string
  existing_record_id?: number
  existing_source?: string
  existing_status?: string
  fields?: string[]
}

export interface ImportReport {
  rows: number
  created: ImportRow[]
  already_imported: ImportRow[]
  conflicts: ImportRow[]
  rejected: ImportRow[]
  genes_not_in_kgdb: ImportRow[]
  dropped_fields: ImportRow[]
}

/** Upload an export page (or a JSON list of pages); every new curation becomes a draft */
export const importGeneCuratorExport = (file: File): Promise<AxiosResponse<ImportReport>> => {
  const formData = new FormData()
  formData.append('file', file)
  return apiClient.post('/api/admin/gene-curator/import', formData, {
    headers: { 'Content-Type': 'multipart/form-data' }
  })
}
