/**
 * The pending-staging client sends paging and every filter to the server (#422).
 */

import { describe, it, expect, vi } from 'vitest'

vi.mock('@/api/client', () => ({ default: { get: vi.fn() } }))

import apiClient from '@/api/client'
import { getPendingStaging } from '@/api/admin/staging'

describe('getPendingStaging', () => {
  it('puts offset, limit and filters in the query string', () => {
    getPendingStaging({
      limit: 25,
      offset: 50,
      source_filter: 'ClinGen',
      requires_expert_review: true,
      search: 'PKD'
    })
    expect(apiClient.get).toHaveBeenLastCalledWith(
      '/api/staging/staging/pending?limit=25&offset=50&source_filter=ClinGen&requires_expert_review=true&search=PKD'
    )

    getPendingStaging({ limit: 25 })
    expect(apiClient.get).toHaveBeenLastCalledWith('/api/staging/staging/pending?limit=25')
  })
})
