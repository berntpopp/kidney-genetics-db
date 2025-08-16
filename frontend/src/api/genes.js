/**
 * Gene API endpoints
 */

import apiClient from './client'

export const geneApi = {
  // Get paginated list of genes
  async getGenes(params = {}) {
    const { 
      page = 1, 
      perPage = 25, 
      search = '', 
      minScore = null,
      sortBy = null,
      sortDesc = false 
    } = params
    const skip = (page - 1) * perPage

    const response = await apiClient.get('/api/genes/', {
      params: {
        skip,
        limit: perPage,
        search: search || undefined,
        min_score: minScore || undefined,
        sort_by: sortBy || undefined,
        sort_desc: sortDesc || undefined
      }
    })
    return response.data
  },

  // Get single gene by symbol
  async getGene(symbol) {
    const response = await apiClient.get(`/api/genes/${symbol}`)
    return response.data
  },

  // Get evidence for a gene
  async getGeneEvidence(symbol) {
    const response = await apiClient.get(`/api/genes/${symbol}/evidence`)
    return response.data
  }
}
