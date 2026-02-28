import api from './client'

/** Data source status item returned from the API */
export interface DataSource {
  name: string
  display_name: string
  enabled: boolean
  last_run: string | null
  status: string
  gene_count: number
  [key: string]: unknown
}

/** JSON:API data wrapper for datasource endpoint */
interface DataSourceApiResponse {
  data: DataSource | DataSource[]
  meta?: Record<string, unknown>
}

export const datasourceApi = {
  /**
   * Get all data sources with their status and statistics
   */
  async getDataSources(): Promise<DataSource[]> {
    const response = await api.get<DataSourceApiResponse>('/api/datasources/')
    return response.data.data as DataSource[]
  },

  /**
   * Get detailed information about a specific data source
   */
  async getDataSource(sourceName: string): Promise<DataSource> {
    const response = await api.get<DataSourceApiResponse>(`/api/datasources/${sourceName}`)
    return response.data.data as DataSource
  }
}
