/**
 * Network Analysis and Enrichment API endpoints
 *
 * Types mirror the response models in backend/app/schemas/network.py.
 * Every call accepts an AbortSignal so the view can cancel a superseded request.
 */

import type { GenericAbortSignal } from 'axios'
import apiClient from './client'

// Per-call timeouts (ms); GO enrichment waits on an external service (backend timeout 120 s)
const NETWORK_TIMEOUT_MS = 120_000
const HPO_TIMEOUT_MS = 60_000
const GO_TIMEOUT_MS = 150_000

/** Cytoscape.js element data */
export interface CytoscapeElement {
  data: Record<string, unknown>
  position?: { x: number; y: number }
  [key: string]: unknown
}

/** Cytoscape.js JSON as produced by the backend */
export interface CytoscapeJson {
  elements: CytoscapeElement[]
  [key: string]: unknown
}

/** NetworkBuildResponse */
export interface NetworkBuildResponse {
  nodes: number
  edges: number
  components: number
  cytoscape_json: CytoscapeJson
  /** Submitted gene IDs the backend could not place in the network (newer backends) */
  unknown_gene_ids?: number[]
}

/** NetworkClusterResponse */
export interface NetworkClusterResponse extends NetworkBuildResponse {
  /** gene ID -> cluster ID (JSON object keys are strings) */
  clusters: Record<string, number>
  num_clusters: number
  modularity: number
  algorithm: string
  /** Clustering parameters used, e.g. objective, resolution, iterations, seed */
  parameters: Record<string, unknown>
  /** Optional top-level resolution (newer backends); fall back to parameters.resolution */
  resolution?: number | null
}

/** EnrichmentResult (one significant term) */
export interface EnrichmentTerm {
  term_id: string
  term_name: string
  p_value: number
  fdr: number
  gene_count: number
  cluster_size: number
  background_count?: number | null
  genes: string[]
  enrichment_score: number
  odds_ratio: number
}

/** HPOEnrichmentResponse / GOEnrichmentResponse */
export interface EnrichmentResponse {
  results: EnrichmentTerm[]
  total_terms: number
  cluster_size: number
  fdr_threshold: number
  /** GO only */
  gene_set?: string
  /** HPO only: submitted gene IDs not tested (no kidney HPO annotation or outside the background) */
  excluded_genes?: number[]
  /** Optional: size of the background the backend actually used */
  background_size?: number | null
}

/** HPOBatchEnrichmentResponse */
export interface HPOBatchEnrichmentResponse {
  results: EnrichmentTerm[][]
  total_tests: number
  fdr_threshold: number
  excluded_genes?: number[][]
  background_size?: number | null
}

/** Parameters for buildNetwork */
export interface BuildNetworkParams {
  gene_ids: number[]
  min_string_score?: number
  remove_isolated?: boolean
  min_degree?: number
  largest_component_only?: boolean
}

/** Parameters for clusterNetwork */
export interface ClusterNetworkParams extends BuildNetworkParams {
  algorithm?: string
  min_cluster_size?: number
}

/** Parameters for extractSubgraph */
export interface ExtractSubgraphParams {
  seed_gene_ids: number[]
  gene_ids: number[]
  min_string_score?: number
  k?: number
}

/** Parameters for enrichHPO */
export interface EnrichHPOParams {
  cluster_genes: number[]
  background_genes?: number[] | null
  fdr_threshold?: number
}

/** Parameters for enrichHPOBatch */
export interface EnrichHPOBatchParams {
  communities: number[][]
  background_genes?: number[] | null
  fdr_threshold?: number
}

/** Parameters for enrichGO */
export interface EnrichGOParams {
  cluster_genes: number[]
  background_genes?: number[] | null
  gene_set?: string
  fdr_threshold?: number
  timeout_seconds?: number
}

export const networkApi = {
  /** Build protein-protein interaction network */
  async buildNetwork(
    {
      gene_ids,
      min_string_score = 400,
      remove_isolated = false,
      min_degree = 0,
      largest_component_only = false
    }: BuildNetworkParams,
    signal?: GenericAbortSignal
  ): Promise<NetworkBuildResponse> {
    const response = await apiClient.post<NetworkBuildResponse>(
      '/api/network/build',
      { gene_ids, min_string_score, remove_isolated, min_degree, largest_component_only },
      { signal, timeout: NETWORK_TIMEOUT_MS }
    )
    return response.data
  },

  /** Cluster network using graph algorithms */
  async clusterNetwork(
    {
      gene_ids,
      min_string_score = 400,
      algorithm = 'leiden',
      remove_isolated = false,
      min_degree = 0,
      min_cluster_size = 1,
      largest_component_only = false
    }: ClusterNetworkParams,
    signal?: GenericAbortSignal
  ): Promise<NetworkClusterResponse> {
    const response = await apiClient.post<NetworkClusterResponse>(
      '/api/network/cluster',
      {
        gene_ids,
        min_string_score,
        algorithm,
        remove_isolated,
        min_degree,
        min_cluster_size,
        largest_component_only
      },
      { signal, timeout: NETWORK_TIMEOUT_MS }
    )
    return response.data
  },

  /** Extract k-hop neighborhood subgraph */
  async extractSubgraph(
    { seed_gene_ids, gene_ids, min_string_score = 400, k = 2 }: ExtractSubgraphParams,
    signal?: GenericAbortSignal
  ): Promise<NetworkBuildResponse> {
    const response = await apiClient.post<NetworkBuildResponse>(
      '/api/network/subgraph',
      { seed_gene_ids, gene_ids, min_string_score, k },
      { signal, timeout: NETWORK_TIMEOUT_MS }
    )
    return response.data
  },

  /** HPO term enrichment of one gene set against background_genes (default: all annotated) */
  async enrichHPO(
    { cluster_genes, background_genes = null, fdr_threshold = 0.05 }: EnrichHPOParams,
    signal?: GenericAbortSignal
  ): Promise<EnrichmentResponse> {
    const response = await apiClient.post<EnrichmentResponse>(
      '/api/network/enrich/hpo',
      { cluster_genes, background_genes, fdr_threshold },
      { signal, timeout: HPO_TIMEOUT_MS }
    )
    return response.data
  },

  /** HPO enrichment of several communities with pooled FDR */
  async enrichHPOBatch(
    { communities, background_genes = null, fdr_threshold = 0.05 }: EnrichHPOBatchParams,
    signal?: GenericAbortSignal
  ): Promise<HPOBatchEnrichmentResponse> {
    const response = await apiClient.post<HPOBatchEnrichmentResponse>(
      '/api/network/enrich/hpo/batch',
      { communities, background_genes, fdr_threshold },
      { signal, timeout: HPO_TIMEOUT_MS }
    )
    return response.data
  },

  /** GO/KEGG enrichment via GSEApy against background_genes */
  async enrichGO(
    {
      cluster_genes,
      background_genes = null,
      gene_set = 'GO_Biological_Process_2023',
      fdr_threshold = 0.05,
      timeout_seconds = 120
    }: EnrichGOParams,
    signal?: GenericAbortSignal
  ): Promise<EnrichmentResponse> {
    const response = await apiClient.post<EnrichmentResponse>(
      '/api/network/enrich/go',
      { cluster_genes, background_genes, gene_set, fdr_threshold, timeout_seconds },
      { signal, timeout: GO_TIMEOUT_MS }
    )
    return response.data
  }
}

export default networkApi
