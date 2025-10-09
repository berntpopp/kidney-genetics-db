/**
 * Gene API endpoints - JSON:API compliant
 */

import apiClient from './client'

export const geneApi = {
  /**
   * Get paginated list of genes
   * @param {Object} params Query parameters
   * @returns {Promise} JSON:API response with genes
   */
  async getGenes(params = {}) {
    const {
      page = 1,
      perPage = 20,
      search = '',
      minScore = null,
      maxScore = null,
      minCount = null,
      maxCount = null,
      source = null,
      tiers = null,
      sortBy = null,
      sortDesc = false,
      hideZeroScores = true
    } = params

    // Build JSON:API query parameters
    const queryParams = {
      'page[number]': page,
      'page[size]': perPage
    }

    // Add filters (only if values are provided)
    if (search) queryParams['filter[search]'] = search
    if (minScore !== null) queryParams['filter[min_score]'] = minScore
    if (maxScore !== null) queryParams['filter[max_score]'] = maxScore
    if (minCount !== null) queryParams['filter[min_count]'] = minCount
    if (maxCount !== null) queryParams['filter[max_count]'] = maxCount
    if (source) queryParams['filter[source]'] = source
    if (tiers && tiers.length > 0) {
      // Join multiple tiers with commas for OR logic
      queryParams['filter[tier]'] = tiers.join(',')
    }

    // Hide zero scores filter (explicitly set to control default behavior)
    queryParams['filter[hide_zero_scores]'] = hideZeroScores

    // Build sort parameter (JSON:API spec: prefix with - for descending)
    if (sortBy) {
      const sortPrefix = sortDesc ? '-' : ''
      queryParams.sort = `${sortPrefix}${sortBy}`
    }

    const response = await apiClient.get('/api/genes/', {
      params: queryParams
    })

    // Transform JSON:API response to simpler format for Vue components
    return {
      items: response.data.data.map(item => ({
        id: item.id,
        ...item.attributes
      })),
      total: response.data.meta.total,
      page: response.data.meta.page,
      perPage: response.data.meta.per_page,
      pageCount: response.data.meta.page_count,
      meta: response.data.meta
    }
  },

  /**
   * Get single gene by symbol
   * @param {String} symbol Gene symbol
   * @returns {Promise} Gene data
   */
  async getGene(symbol) {
    const response = await apiClient.get(`/api/genes/${symbol}`)

    // Transform JSON:API response
    return {
      id: response.data.data.id,
      ...response.data.data.attributes
    }
  },

  /**
   * Get evidence for a gene
   * @param {String} symbol Gene symbol
   * @returns {Promise} Evidence data
   */
  async getGeneEvidence(symbol) {
    const response = await apiClient.get(`/api/genes/${symbol}/evidence`)

    // Transform JSON:API response
    return {
      evidence: response.data.data.map(item => ({
        id: item.id,
        ...item.attributes
      })),
      meta: response.data.meta
    }
  },

  /**
   * Get annotations for a gene (including gnomAD data)
   * @param {Number} geneId Gene ID
   * @returns {Promise} Annotations data
   */
  async getGeneAnnotations(geneId) {
    const response = await apiClient.get(`/api/annotations/genes/${geneId}/annotations`)
    return response.data
  },

  /**
   * Get HPO classifications for multiple genes
   * @param {Array<Number>} geneIds Array of gene IDs (max 1000)
   * @returns {Promise} HPO classifications data with clinical_group, onset_group, is_syndromic
   */
  async getHPOClassifications(geneIds) {
    if (!geneIds || geneIds.length === 0) {
      return { data: [], metadata: { cached: false, gene_count: 0, fetch_time_ms: 0 } }
    }

    const response = await apiClient.post('/api/genes/hpo-classifications', {
      gene_ids: geneIds
    })

    return response.data
  }
}
