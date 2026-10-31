/**
 * Expert-reviewed gene-disease associations (#26)
 * Public reads return published records only; writes require a curator or admin.
 */

import apiClient from './client'

export const MENDELIAN_STRENGTHS = [
  'Definitive',
  'Strong',
  'Moderate',
  'Limited',
  'Disputed',
  'Refuted',
  'No Known Disease Relationship'
] as const
/** Alpha draft modelled on the ClinGen risk-allele tiers (#437); never a Mendelian class */
export const SUSCEPTIBILITY_STRENGTHS = [
  'Established association',
  'Likely association',
  'Uncertain association'
] as const
export const EVIDENCE_STRENGTHS = [...MENDELIAN_STRENGTHS, ...SUSCEPTIBILITY_STRENGTHS] as const
export type EvidenceStrength = (typeof EVIDENCE_STRENGTHS)[number]

export const RELATIONSHIP_TYPES = ['mendelian', 'susceptibility'] as const
export type RelationshipType = (typeof RELATIONSHIP_TYPES)[number]
export const RELATIONSHIP_LABELS: Record<RelationshipType, string> = {
  mendelian: 'Mendelian gene–disease validity',
  susceptibility: 'Susceptibility (risk) association'
}
export const strengthsFor = (type: RelationshipType): readonly EvidenceStrength[] =>
  type === 'susceptibility' ? SUSCEPTIBILITY_STRENGTHS : MENDELIAN_STRENGTHS

/** HPO mode-of-inheritance terms accepted by the API (labels from the pinned hp.json) */
export const MOI_TERMS: Record<string, string> = {
  'HP:0000006': 'Autosomal dominant inheritance',
  'HP:0000007': 'Autosomal recessive inheritance',
  'HP:0001417': 'X-linked inheritance',
  'HP:0001419': 'X-linked recessive inheritance',
  'HP:0001423': 'X-linked dominant inheritance',
  'HP:0032113': 'Semidominant inheritance',
  'HP:0001427': 'Mitochondrial inheritance',
  'HP:0001450': 'Y-linked inheritance',
  'HP:0010984': 'Digenic inheritance',
  'HP:0001426': 'Non-Mendelian inheritance'
}

/** Conventional short forms for the MOI chip (full HPO label in the tooltip) */
export const MOI_ABBREVIATIONS: Record<string, string> = {
  'HP:0000006': 'AD',
  'HP:0000007': 'AR',
  'HP:0001417': 'XL',
  'HP:0001419': 'XLR',
  'HP:0001423': 'XLD',
  'HP:0032113': 'SD',
  'HP:0001427': 'MT',
  'HP:0001450': 'YL',
  'HP:0010984': 'DG',
  'HP:0001426': 'NM'
}

/** A negative short-read result does not exclude a variant in this gene (issue 439) */
export const hasShortReadLimit = (d: Diagnostics | null | undefined): boolean =>
  !!d?.detectability?.some(x => x.negative_report_does_not_exclude)

export type AssociationSource = 'kgdb' | 'gene_curator'
export const MANE_STATUSES = ['select', 'plus_clinical', 'none', 'not_checked'] as const
export const RESOURCE_TYPES = [
  'patient_organisation',
  'registry',
  'variant_database',
  'guideline',
  'other'
] as const
export const MANE_LABELS: Record<string, string> = {
  select: 'MANE Select',
  plus_clinical: 'MANE Plus Clinical',
  none: 'No MANE transcript',
  not_checked: 'MANE status not checked'
}
export const RESOURCE_LABELS: Record<string, string> = {
  patient_organisation: 'Patient organisation',
  registry: 'Registry',
  variant_database: 'Variant database',
  guideline: 'Guideline',
  other: 'Other resource'
}
export const VERIFIED_METHODS = ['fetched', 'api', 'captcha_title_only'] as const

export interface Scores {
  genetic?: number | null
  experimental?: number | null
  total?: number | null
}

export interface RecommendedTranscript {
  refseq: string | null
  ensembl: string | null
  mane_status: (typeof MANE_STATUSES)[number]
  legacy_transcript: string | null
  numbering_conversion: string | null
  /** Absent on records saved before issue 474 */
  verified_via?: string | null
}

export interface DetectabilityTool {
  name: string
  url: string | null
  pmid_or_doi: string | null
}

export interface Detectability {
  challenge: string
  share_of_variants: string | null
  affected_variants: string | null
  methods: string[]
  tools: DetectabilityTool[]
  negative_report_does_not_exclude: boolean
  sources: string[]
}

export interface Resource {
  type: (typeof RESOURCE_TYPES)[number]
  name: string
  url: string
  language: string | null
  audiences: string[]
  maintainer: string | null
  conflict_of_interest: string | null
  country_or_scope?: string | null
  verified: { method: (typeof VERIFIED_METHODS)[number]; date: string }
}

/** Non-scoring clinical diagnostics section (#439) */
export interface Diagnostics {
  recommended_transcript: RecommendedTranscript | null
  detectability: Detectability[]
  detectability_note?: string | null
  resources: Resource[]
}

/** Provenance and classification fields shared by records and editor input (#437) */
export interface AssociationDetails {
  relationship_type: RelationshipType
  moi: string | null
  methodology: string | null
  methodology_version: string | null
  source: AssociationSource
  external_id: string | null
  external_url: string | null
  external_curator: string | null
  external_reviewer: string | null
  scores: Scores | null
  diagnostics: Diagnostics | null
}
export type AssociationStatus = 'draft' | 'in_review' | 'published'
export type WorkflowAction = 'submit' | 'publish' | 'return-to-draft'

export interface Association extends AssociationDetails {
  id: number
  gene_id: number
  gene_symbol: string
  disease_id: string
  disease_name: string
  evidence_strength: EvidenceStrength
  citations: string[]
  evidence_summary: string | null
  moi_label: string | null
  status: AssociationStatus
  curator_id: number
  /** A Gene Curator import no KGDB curator has edited: any curator may act on it (#448) */
  imported_unclaimed?: boolean
  reviewer_id: number | null
  created_at: string
  updated_at: string
  submitted_at: string | null
  reviewed_at: string | null
  published_at: string | null
}

export interface AssociationInput extends Partial<AssociationDetails> {
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

/** Only http(s) links are rendered as anchors (the API enforces the same) */
export const isHttpUrl = (url: string | null | undefined): url is string =>
  !!url && /^https?:\/\/\S+$/.test(url)
