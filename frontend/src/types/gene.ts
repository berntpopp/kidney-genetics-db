export interface Gene {
  id: number
  hgnc_id: string
  gene_symbol: string
  gene_name: string | null
  entrez_id: number | null
  ensembl_id: string | null
  omim_id: string | null
  gene_score: number | null
  evidence_count: number | null
  tier: string | null
  created_at: string
  updated_at: string
}

export interface GeneDetail extends Gene {
  annotations: Record<string, unknown>
  evidence_sources: EvidenceSource[]
}

export interface EvidenceSource {
  source_name: string
  source_data: Record<string, unknown>
  last_updated: string | null
}

export interface GeneListParams {
  page?: number
  perPage?: number
  search?: string
  minScore?: number | null
  maxScore?: number | null
  minCount?: number | null
  maxCount?: number | null
  source?: string | null
  tiers?: string[] | null
  sortBy?: string | null
  sortDesc?: boolean
  hideZeroScores?: boolean
}
