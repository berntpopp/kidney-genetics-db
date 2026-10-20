/**
 * The progress WebSocket follows the API base URL and stops reconnecting
 * after the component unmounts (#326).
 */

import { describe, it, expect, vi, afterEach } from 'vitest'
import { flushPromises, mount } from '@vue/test-utils'
import DataSourceProgress from '@/components/DataSourceProgress.vue'

const cfg = vi.hoisted(() => ({ apiBaseUrl: '' }))
vi.mock('@/config', () => ({ config: cfg }))
vi.mock('@/api/client', () => ({
  default: { get: vi.fn(async () => ({ data: { data: [] } })), post: vi.fn() }
}))
vi.stubGlobal('logService', { info: vi.fn(), warn: vi.fn(), error: vi.fn(), debug: vi.fn() })

const urls: string[] = []
class FakeWebSocket {
  onopen: (() => void) | null = null
  onclose: (() => void) | null = null
  onmessage = null
  onerror = null
  constructor(url: string) {
    urls.push(url)
  }
  close() {
    // Browsers dispatch the close event asynchronously
    setTimeout(() => this.onclose?.(), 0)
  }
}
vi.stubGlobal('WebSocket', FakeWebSocket)

afterEach(() => {
  urls.length = 0
  vi.useRealTimers()
})

async function connectedUrl(apiBaseUrl: string) {
  cfg.apiBaseUrl = apiBaseUrl
  const wrapper = mount(DataSourceProgress)
  await flushPromises()
  wrapper.unmount()
  return urls.at(-1)
}

describe('DataSourceProgress WebSocket', () => {
  it('derives ws:// from an http API base', async () => {
    expect(await connectedUrl('http://api.example.org:8000')).toBe(
      'ws://api.example.org:8000/api/progress/ws'
    )
  })

  it('derives wss:// from an https API base, keeping its path', async () => {
    expect(await connectedUrl('https://kidney.example.org/backend/')).toBe(
      'wss://kidney.example.org/backend/api/progress/ws'
    )
  })

  it('uses the page origin for a relative (same-origin) API base', async () => {
    expect(await connectedUrl('')).toBe(`ws://${window.location.host}/api/progress/ws`)
  })

  it('opens no new socket after unmount', async () => {
    vi.useFakeTimers()
    cfg.apiBaseUrl = ''
    const wrapper = mount(DataSourceProgress)
    await flushPromises()
    expect(urls).toHaveLength(1)

    wrapper.unmount()
    await vi.advanceTimersByTimeAsync(30000)
    expect(urls).toHaveLength(1)
  })
})
