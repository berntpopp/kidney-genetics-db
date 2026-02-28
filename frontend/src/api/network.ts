/**
 * Network Analysis and Enrichment API endpoints
 */

import apiClient from './client'

/** Cytoscape.js element data */
export interface CytoscapeElement {
  data: Record<string, unknown>
  position?: { x: number; y: number }
  [key: string]: unknown
}

/** Network build/cluster response containing Cytoscape.js JSON */
export interface NetworkData {
  elements: CytoscapeElement[]
  nodes: CytoscapeElement[]
  edges: CytoscapeElement[]
  stats?: Record<string, unknown>
  [key: string]: unknown
}

/** Enrichment result */
export interface EnrichmentResult {
  terms: Array<{
    term: string
    pvalue: number
    fdr: number
    genes: string[]
    [key: string]: unknown
  }>
  stats?: Record<string, unknown>
  [key: string]: unknown
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
export interface ClusterNetworkParams {
  gene_ids: number[]
  min_string_score?: number
  algorithm?: string
  remove_isolated?: boolean
  min_degree?: number
  min_cluster_size?: number
  largest_component_only?: boolean
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

/** Parameters for enrichGO */
export interface EnrichGOParams {
  cluster_genes: number[]
  gene_set?: string
  fdr_threshold?: number
  timeout_seconds?: number
}

export const networkApi = {
  /**
   * Build protein-protein interaction network
   */
  async buildNetwork({
    gene_ids,
    min_string_score = 400,
    remove_isolated = false,
    min_degree = 0,
    largest_component_only = false
  }: BuildNetworkParams): Promise<NetworkData> {
    const response = await apiClient.post<NetworkData>('/api/network/build', {
      gene_ids,
      min_string_score,
      remove_isolated,
      min_degree,
      largest_component_only
    })
    return response.data
  },

  /**
   * Cluster network using graph algorithms
   */
  async clusterNetwork({
    gene_ids,
    min_string_score = 400,
    algorithm = 'leiden',
    remove_isolated = false,
    min_degree = 0,
    min_cluster_size = 1,
    largest_component_only = false
  }: ClusterNetworkParams): Promise<NetworkData> {
    const response = await apiClient.post<NetworkData>('/api/network/cluster', {
      gene_ids,
      min_string_score,
      algorithm,
      remove_isolated,
      min_degree,
      min_cluster_size,
      largest_component_only
    })
    return response.data
  },

  /**
   * Extract k-hop neighborhood subgraph
   */
  async extractSubgraph({
    seed_gene_ids,
    gene_ids,
    min_string_score = 400,
    k = 2
  }: ExtractSubgraphParams): Promise<NetworkData> {
    const response = await apiClient.post<NetworkData>('/api/network/subgraph', {
      seed_gene_ids,
      gene_ids,
      min_string_score,
      k
    })
    return response.data
  },

  /**
   * Perform HPO term enrichment analysis
   */
  async enrichHPO({
    cluster_genes,
    background_genes = null,
    fdr_threshold = 0.05
  }: EnrichHPOParams): Promise<EnrichmentResult> {
    const response = await apiClient.post<EnrichmentResult>('/api/network/enrich/hpo', {
      cluster_genes,
      background_genes,
      fdr_threshold
    })
    return response.data
  },

  /**
   * Perform GO/KEGG enrichment analysis via GSEApy
   */
  async enrichGO({
    cluster_genes,
    gene_set = 'GO_Biological_Process_2023',
    fdr_threshold = 0.05,
    timeout_seconds = 120
  }: EnrichGOParams): Promise<EnrichmentResult> {
    const response = await apiClient.post<EnrichmentResult>('/api/network/enrich/go', {
      cluster_genes,
      gene_set,
      fdr_threshold,
      timeout_seconds
    })
    return response.data
  }
}

export default networkApi
