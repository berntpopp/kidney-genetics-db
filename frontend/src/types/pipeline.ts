export interface PipelineStatus {
  is_running: boolean
  current_source: string | null
  progress: number
  total_genes: number
  processed_genes: number
  failed_genes: number
  start_time: string | null
  estimated_completion: string | null
}

export interface PipelineSource {
  name: string
  display_name: string
  enabled: boolean
  last_run: string | null
  status: PipelineSourceStatus
}

export type PipelineSourceStatus = 'idle' | 'running' | 'completed' | 'failed' | 'pending'

export interface WebSocketMessage {
  type: string
  data: Record<string, unknown>
}
