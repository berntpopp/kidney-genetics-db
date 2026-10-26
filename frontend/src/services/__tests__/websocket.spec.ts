/**
 * The admin progress socket authenticates with a first message, not a URL token (#361).
 */

import { describe, it, expect, vi } from 'vitest'
import { WebSocketService } from '@/services/websocket'

vi.mock('@/api/client', () => ({ getClientAccessToken: () => 'admin-jwt' }))
vi.stubGlobal('logService', { info: vi.fn(), warn: vi.fn(), error: vi.fn(), debug: vi.fn() })

class FakeWebSocket {
  static OPEN = 1
  readyState = 0
  sent: string[] = []
  url: string
  onopen: (() => void) | null = null
  constructor(url: string) {
    this.url = url
  }
  send(data: string) {
    this.sent.push(data)
  }
}
vi.stubGlobal('WebSocket', FakeWebSocket)

describe('WebSocketService', () => {
  it('sends the access token as the first message on open', () => {
    const service = new WebSocketService()
    service.connect('ws://api.example.org/api/progress/ws')
    const socket = service.ws as unknown as FakeWebSocket
    socket.readyState = FakeWebSocket.OPEN
    socket.onopen?.()

    expect(socket.url).not.toContain('token')
    expect(JSON.parse(socket.sent[0]!)).toEqual({ type: 'auth', token: 'admin-jwt' })
  })
})
