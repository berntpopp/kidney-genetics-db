/**
 * Admin API credential tests (#303): every admin consumer must go through the
 * shared client so an expired token is refreshed once and new credentials are
 * used for all following requests, including blob downloads.
 */

import { describe, it, expect, vi, beforeEach } from 'vitest'
import axios, { AxiosError } from 'axios'
import type { InternalAxiosRequestConfig } from 'axios'
import { setActivePinia, createPinia } from 'pinia'
import apiClient, { setClientAccessToken } from '@/api/client'
import { useSettingsApi } from '@/composables/useSettingsApi'
import { useBackupApi } from '@/composables/useBackupApi'
import * as releasesApi from '@/api/admin/releases'

const seen: { url?: string; baseURL?: string; auth: unknown }[] = []

apiClient.defaults.adapter = async (config: InternalAxiosRequestConfig) => {
  const auth = config.headers.Authorization
  seen.push({ url: config.url, baseURL: config.baseURL, auth })
  const respond = (status: number, data: unknown) => ({
    data,
    status,
    statusText: String(status),
    headers: {},
    config
  })
  if (auth !== 'Bearer fresh') {
    throw new AxiosError('Unauthorized', 'ERR_BAD_REQUEST', config, null, respond(401, {}))
  }
  if (config.url?.includes('bad')) {
    const res = respond(400, { detail: 'Invalid setting value' })
    throw new AxiosError('Bad', 'ERR_BAD_REQUEST', config, null, res)
  }
  return respond(200, config.responseType === 'blob' ? new Blob(['x']) : { data: [], ok: true })
}

describe('admin requests after token expiry', () => {
  let refresh: ReturnType<typeof vi.spyOn>

  beforeEach(() => {
    setActivePinia(createPinia())
    seen.length = 0
    setClientAccessToken('expired')
    refresh = vi.spyOn(axios, 'post').mockResolvedValue({ data: { access_token: 'fresh' } })
    Object.assign(URL, { createObjectURL: () => 'blob:x', revokeObjectURL: () => {} })
  })

  it('refreshes once, then every admin module sends the new token', async () => {
    const settings = useSettingsApi()
    const backups = useBackupApi()

    await expect(settings.loadSettings()).resolves.toEqual({ data: [], ok: true })
    await backups.loadStats()
    await expect(backups.downloadBackup({ id: 1, filename: 'b.dump' })).resolves.toBe(true)
    await releasesApi.listReleases()
    const exported = await releasesApi.downloadReleaseExport('2026.1')

    expect(exported.data).toBeInstanceOf(Blob)
    expect(refresh).toHaveBeenCalledTimes(1)
    // Only the very first request used the expired token; its retry and all later ones are fresh
    expect(seen.map(r => r.auth)).toEqual([
      'Bearer expired',
      'Bearer fresh',
      'Bearer fresh',
      'Bearer fresh',
      'Bearer fresh',
      'Bearer fresh'
    ])
    expect(seen.every(r => r.baseURL === apiClient.defaults.baseURL)).toBe(true)
  })

  it('reports the API detail message on failure', async () => {
    setClientAccessToken('fresh')
    const settings = useSettingsApi()
    await expect(settings.updateSetting('bad', 1)).rejects.toThrow('Invalid setting value')
    expect(settings.error.value).toBe('Invalid setting value')
  })
})
