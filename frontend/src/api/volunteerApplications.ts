/**
 * Volunteer-curator applications. Applying is public; the review list (with applicant
 * contact details) and decisions are admin-only.
 */

import apiClient from './client'

export type ApplicationStatus = 'pending' | 'approved' | 'rejected'

export interface ApplicationInput {
  gene_symbol: string
  name: string
  email: string
  affiliation?: string
  orcid?: string
  motivation: string
  /** Honeypot: always empty for real users */
  website: string
}

export interface Application {
  id: number
  gene_symbol: string
  name: string
  email: string
  affiliation: string | null
  orcid: string | null
  motivation: string
  status: ApplicationStatus
  decided_by: number | null
  decided_at: string | null
  decision_note: string | null
  user_id: number | null
  created_at: string
}

export interface ApplicationList {
  data: Application[]
  meta: { total: number; limit: number; offset: number; pending_count: number }
}

export interface DecisionInput {
  decision: 'approved' | 'rejected'
  note?: string
  role?: 'viewer' | 'curator'
}

export const volunteerApplicationsApi = {
  async submit(input: ApplicationInput): Promise<void> {
    await apiClient.post('/api/volunteer-applications/', input)
  },
  async list(params: { status?: ApplicationStatus; limit?: number; offset?: number } = {}) {
    return (await apiClient.get<ApplicationList>('/api/volunteer-applications/', { params })).data
  },
  async decide(id: number, input: DecisionInput): Promise<Application> {
    return (await apiClient.post<Application>(`/api/volunteer-applications/${id}/decision`, input))
      .data
  }
}
