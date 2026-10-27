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

/** Summary from GET /api/datasources/: the one definition of source and gene counts */
export interface DataSourcesSummary {
  sources: DataSource[]
  /** Configured sources with evidence for at least one listed gene */
  total_active: number
  /** All configured sources */
  total_sources: number
  total_unique_genes: number
  /** Listed genes with evidence from two or more sources, and their share in percent */
  multi_source_genes: number
  source_coverage: number
  last_pipeline_run: string | null
  last_data_update: string | null
  explanations: Record<string, string>
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
  async getDataSources(): Promise<DataSourcesSummary> {
    const response = await api.get<{ data: DataSourcesSummary }>('/api/datasources/')
    return response.data.data
  },

  /**
   * Get detailed information about a specific data source
   */
  async getDataSource(sourceName: string): Promise<DataSource> {
    const response = await api.get<DataSourceApiResponse>(`/api/datasources/${sourceName}`)
    return response.data.data as DataSource
  }
}
