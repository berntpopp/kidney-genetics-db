/**
 * Expert problem/suggestion reports on curated associations, and notification preferences.
 * Submitting is public; the inbox (with reporter contact details) is curator-only.
 */

import apiClient from './client'

export type ReportKind = 'problem' | 'suggestion'
export type ReportStatus = 'open' | 'resolved' | 'dismissed'

export interface ReportInput {
  gene_symbol: string
  association_id?: number
  kind: ReportKind
  message: string
  reporter_name?: string
  reporter_email?: string
  /** Honeypot: always empty for real users */
  website: string
}

export interface Report {
  id: number
  gene_symbol: string
  association_id: number | null
  kind: ReportKind
  message: string
  reporter_name: string | null
  reporter_email: string | null
  status: ReportStatus
  handled_by: number | null
  handled_at: string | null
  created_at: string
}

export interface ReportList {
  data: Report[]
  meta: { total: number; limit: number; offset: number; open_count: number }
}

export interface NotificationPref {
  event: string
  label: string
  enabled: boolean
}

export const curationReportsApi = {
  async submit(input: ReportInput): Promise<void> {
    await apiClient.post('/api/curation/reports/', input)
  },
  async list(params: { status?: ReportStatus; limit?: number; offset?: number } = {}) {
    return (await apiClient.get<ReportList>('/api/curation/reports/', { params })).data
  },
  async setStatus(id: number, status: ReportStatus): Promise<Report> {
    return (await apiClient.patch<Report>(`/api/curation/reports/${id}`, { status })).data
  }
}

export const notificationPrefsApi = {
  async list(): Promise<NotificationPref[]> {
    return (await apiClient.get<NotificationPref[]>('/api/users/me/notification-prefs')).data
  },
  async update(prefs: Record<string, boolean>): Promise<NotificationPref[]> {
    return (await apiClient.put<NotificationPref[]>('/api/users/me/notification-prefs', prefs)).data
  }
}
