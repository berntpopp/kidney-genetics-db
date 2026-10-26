/**
 * Expert-reviewed gene-disease associations (#26)
 * Public reads return published records only; writes require a curator or admin.
 */

import apiClient from './client'

export const EVIDENCE_STRENGTHS = [
  'Definitive',
  'Strong',
  'Moderate',
  'Limited',
  'Disputed',
  'Refuted'
] as const
export type EvidenceStrength = (typeof EVIDENCE_STRENGTHS)[number]
export type AssociationStatus = 'draft' | 'in_review' | 'published'
export type WorkflowAction = 'submit' | 'publish' | 'return-to-draft'

export interface Association {
  id: number
  gene_id: number
  gene_symbol: string
  disease_id: string
  disease_name: string
  evidence_strength: EvidenceStrength
  citations: string[]
  evidence_summary: string | null
  status: AssociationStatus
  curator_id: number
  reviewer_id: number | null
  created_at: string
  updated_at: string
  submitted_at: string | null
  reviewed_at: string | null
  published_at: string | null
}

export interface AssociationInput {
  gene_symbol: string
  disease_id: string
  disease_name: string
  evidence_strength: EvidenceStrength
  citations: string[]
  evidence_summary?: string | null
}

export interface AssociationList {
  data: Association[]
  meta: { total: number; limit: number; offset: number }
}

export interface ListParams {
  gene_symbol?: string
  status?: AssociationStatus
  limit?: number
  offset?: number
}

const BASE = '/api/curation/associations'

export const curationApi = {
  async listPublished(params: ListParams = {}): Promise<AssociationList> {
    return (await apiClient.get<AssociationList>(`${BASE}/`, { params })).data
  },
  async listWorkflow(params: ListParams = {}): Promise<AssociationList> {
    return (await apiClient.get<AssociationList>(`${BASE}/workflow`, { params })).data
  },
  async create(input: AssociationInput): Promise<Association> {
    return (await apiClient.post<Association>(`${BASE}/`, input)).data
  },
  async update(
    id: number,
    input: Partial<Omit<AssociationInput, 'gene_symbol'>>
  ): Promise<Association> {
    return (await apiClient.patch<Association>(`${BASE}/${id}`, input)).data
  },
  /** Review actions confirm the version the reviewer saw; a changed record answers 409 */
  async transition(record: Association, action: WorkflowAction): Promise<Association> {
    const body = action === 'submit' ? undefined : { expected_updated_at: record.updated_at }
    return (await apiClient.post<Association>(`${BASE}/${record.id}/${action}`, body)).data
  }
}

/** Outbound link for a MONDO/OMIM identifier (IDs and links only; no OMIM text) */
export function diseaseUrl(diseaseId: string): string {
  const [prefix, local] = diseaseId.split(':')
  return prefix === 'OMIM'
    ? `https://omim.org/entry/${local}`
    : `https://monarchinitiative.org/${diseaseId}`
}

export function pubmedUrl(pmid: string): string {
  return `https://pubmed.ncbi.nlm.nih.gov/${pmid.replace(/^PMID:/, '')}/`
}
