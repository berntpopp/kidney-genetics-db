/**
 * Network Analysis and Enrichment API endpoints
 */

import apiClient from './client'

export const networkApi = {
  /**
   * Build protein-protein interaction network
   * @param {Object} params Network parameters
   * @param {Array<number>} params.gene_ids Gene IDs to include
   * @param {number} params.min_string_score Minimum STRING confidence (0-1000)
   * @returns {Promise} Network data with Cytoscape.js JSON
   */
  async buildNetwork({ gene_ids, min_string_score = 400 }) {
    const response = await apiClient.post('/api/network/build', {
      gene_ids,
      min_string_score
    })
    return response.data
  },

  /**
   * Cluster network using graph algorithms
   * @param {Object} params Clustering parameters
   * @param {Array<number>} params.gene_ids Gene IDs in network
   * @param {number} params.min_string_score Minimum STRING confidence
   * @param {string} params.algorithm Clustering algorithm (leiden, louvain, walktrap)
   * @returns {Promise} Clustering results with Cytoscape.js JSON
   */
  async clusterNetwork({ gene_ids, min_string_score = 400, algorithm = 'leiden' }) {
    const response = await apiClient.post('/api/network/cluster', {
      gene_ids,
      min_string_score,
      algorithm
    })
    return response.data
  },

  /**
   * Extract k-hop neighborhood subgraph
   * @param {Object} params Subgraph parameters
   * @param {Array<number>} params.seed_gene_ids Seed genes to center around
   * @param {Array<number>} params.gene_ids Full network gene IDs
   * @param {number} params.min_string_score Minimum STRING confidence
   * @param {number} params.k Number of hops (1-5)
   * @returns {Promise} Subgraph with Cytoscape.js JSON
   */
  async extractSubgraph({ seed_gene_ids, gene_ids, min_string_score = 400, k = 2 }) {
    const response = await apiClient.post('/api/network/subgraph', {
      seed_gene_ids,
      gene_ids,
      min_string_score,
      k
    })
    return response.data
  },

  /**
   * Perform HPO term enrichment analysis
   * @param {Object} params Enrichment parameters
   * @param {Array<number>} params.cluster_genes Gene IDs in cluster
   * @param {Array<number>} params.background_genes Background gene set (optional)
   * @param {number} params.fdr_threshold FDR significance threshold
   * @returns {Promise} Enrichment results
   */
  async enrichHPO({ cluster_genes, background_genes = null, fdr_threshold = 0.05 }) {
    const response = await apiClient.post('/api/network/enrich/hpo', {
      cluster_genes,
      background_genes,
      fdr_threshold
    })
    return response.data
  },

  /**
   * Perform GO/KEGG enrichment analysis via GSEApy
   * @param {Object} params Enrichment parameters
   * @param {Array<number>} params.cluster_genes Gene IDs in cluster
   * @param {string} params.gene_set Gene set name (GO_Biological_Process_2023, etc.)
   * @param {number} params.fdr_threshold FDR significance threshold
   * @param {number} params.timeout_seconds API timeout in seconds
   * @returns {Promise} Enrichment results
   */
  async enrichGO({
    cluster_genes,
    gene_set = 'GO_Biological_Process_2023',
    fdr_threshold = 0.05,
    timeout_seconds = 120
  }) {
    const response = await apiClient.post('/api/network/enrich/go', {
      cluster_genes,
      gene_set,
      fdr_threshold,
      timeout_seconds
    })
    return response.data
  }
}

export default networkApi
