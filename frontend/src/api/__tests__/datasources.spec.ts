/**
 * The DiagnosticPanels laboratory registry is requested once per session; a failed request
 * is retried by the next caller.
 */

import { describe, it, expect, vi } from 'vitest'

vi.mock('@/api/client', () => ({ default: { get: vi.fn() } }))

import apiClient from '@/api/client'
import { datasourceApi } from '@/api/datasources'

const get = vi.mocked(apiClient.get)

describe('getDiagnosticPanelsProviders', () => {
  it('retries after a failure, then caches the registry', async () => {
    get.mockRejectedValueOnce(new Error('offline'))
    await expect(datasourceApi.getDiagnosticPanelsProviders()).rejects.toThrow('offline')

    const data = [{ provider_name: 'Natera' }]
    get.mockResolvedValueOnce({ data: { data, meta: { count: 1 } } })
    expect(await datasourceApi.getDiagnosticPanelsProviders()).toEqual(data)
    expect(await datasourceApi.getDiagnosticPanelsProviders()).toEqual(data)
    expect(get).toHaveBeenCalledTimes(2)
    expect(get).toHaveBeenLastCalledWith('/api/datasources/DiagnosticPanels/providers')
  })
})
