import api from './client'

export const datasourceApi = {
  /**
   * Get all data sources with their status and statistics
   */
  async getDataSources() {
    const response = await api.get('/api/datasources/')
    return response.data
  },

  /**
   * Get detailed information about a specific data source
   */
  async getDataSource(sourceName) {
    const response = await api.get(`/api/datasources/${sourceName}`)
    return response.data
  }
}