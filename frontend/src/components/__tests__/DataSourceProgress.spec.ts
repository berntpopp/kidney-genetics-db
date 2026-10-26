/**
 * The progress WebSocket follows the API base URL and stops reconnecting
 * after the component unmounts (#326).
 */

import { describe, it, expect, vi, afterEach } from 'vitest'
import { flushPromises, mount } from '@vue/test-utils'
import DataSourceProgress from '@/components/DataSourceProgress.vue'

const cfg = vi.hoisted(() => ({ apiBaseUrl: '' }))
vi.mock('@/config', () => ({ config: cfg }))
const statusRows = vi.hoisted(() => ({ value: [] as Record<string, unknown>[] }))
vi.mock('@/api/client', () => ({
  default: { get: vi.fn(async () => ({ data: { data: statusRows.value } })), post: vi.fn() },
  getClientAccessToken: () => 'admin-jwt'
}))
vi.stubGlobal('logService', { info: vi.fn(), warn: vi.fn(), error: vi.fn(), debug: vi.fn() })

const urls: string[] = []
const sockets: FakeWebSocket[] = []
class FakeWebSocket {
  static CONNECTING = 0
  static OPEN = 1
  static CLOSING = 2
  static CLOSED = 3
  readyState = FakeWebSocket.CONNECTING
  onopen: (() => void) | null = null
  onclose: (() => void) | null = null
  onmessage = null
  onerror = null
  sent: string[] = []
  constructor(url: string) {
    urls.push(url)
    sockets.push(this)
  }
  send(data: string) {
    this.sent.push(data)
  }
  open() {
    this.readyState = FakeWebSocket.OPEN
    this.onopen?.()
  }
  drop() {
    this.readyState = FakeWebSocket.CLOSED
    this.onclose?.()
  }
  close() {
    this.readyState = FakeWebSocket.CLOSING
    // Browsers dispatch the close event asynchronously
    setTimeout(() => this.drop(), 0)
  }
}
vi.stubGlobal('WebSocket', FakeWebSocket)

afterEach(() => {
  urls.length = 0
  sockets.length = 0
  statusRows.value = []
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

  it('authenticates with a first message, never with a URL token (#361)', async () => {
    cfg.apiBaseUrl = ''
    const wrapper = mount(DataSourceProgress)
    await flushPromises()
    sockets[0]!.open()

    expect(urls[0]).not.toContain('token')
    expect(sockets[0]!.sent.map(m => JSON.parse(m))).toEqual([{ type: 'auth', token: 'admin-jwt' }])
    wrapper.unmount()
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

  it('never overlaps reconnect attempts and leaves no socket open after unmount', async () => {
    vi.useFakeTimers()
    cfg.apiBaseUrl = ''
    const wrapper = mount(DataSourceProgress)
    await flushPromises()
    sockets[0]!.open()
    sockets[0]!.drop() // server disconnect arms the reconnect interval

    await vi.advanceTimersByTimeAsync(5000)
    expect(sockets).toHaveLength(2) // reconnect attempt, handshake still pending

    await vi.advanceTimersByTimeAsync(15000) // slow handshake spans several ticks
    expect(sockets).toHaveLength(2)

    wrapper.unmount()
    await vi.advanceTimersByTimeAsync(30000)
    expect(sockets).toHaveLength(2)
    expect(sockets.every(s => s.readyState === FakeWebSocket.CLOSED)).toBe(true)
  })
})

describe('DataSourceProgress annotation_pipeline controls (#317)', () => {
  const row = (source_name: string, status: string, category: string) => ({
    source_name,
    status,
    category,
    progress_percentage: 0,
    items_processed: 0
  })

  async function buttonLabels(pipelineStatus: string) {
    // A running data source auto-expands the panel
    statusRows.value = [
      row('PubTator', 'running', 'data_source'),
      row('annotation_pipeline', pipelineStatus, 'internal_process')
    ]
    const wrapper = mount(DataSourceProgress, { attachTo: document.body })
    await flushPromises()
    const labels = wrapper.findAll('button').map(b => b.attributes('aria-label'))
    wrapper.unmount()
    return labels
  }

  it.each(['idle', 'failed'])(
    'offers no unconfirmed Start for a %s pipeline (use AdminAnnotations)',
    async status => {
      expect(await buttonLabels(status)).not.toContain('Start annotation_pipeline')
    }
  )

  it('keeps pause and resume', async () => {
    expect(await buttonLabels('running')).toContain('Pause annotation_pipeline')
    expect(await buttonLabels('paused')).toContain('Resume annotation_pipeline')
  })
})
