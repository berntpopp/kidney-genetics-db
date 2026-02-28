/**
 * WebSocket Service for real-time updates
 * Implements event-driven architecture for pipeline progress monitoring
 */

import { ref, type Ref } from 'vue'
import type { WebSocketMessage } from '@/types/pipeline'

/** Handler for typed WebSocket messages */
export type MessageHandler = (data: unknown) => void

/** Wildcard handler receives the full message */
export type WildcardHandler = (message: WebSocketMessage | { type: string }) => void

export class WebSocketService {
  ws: WebSocket | null
  reconnectInterval: number
  shouldReconnect: boolean
  messageHandlers: Map<string, MessageHandler[]>
  connected: Ref<boolean>
  reconnectAttempts: number
  maxReconnectAttempts: number

  constructor() {
    this.ws = null
    this.reconnectInterval = 5000
    this.shouldReconnect = true
    this.messageHandlers = new Map()
    this.connected = ref(false)
    this.reconnectAttempts = 0
    this.maxReconnectAttempts = 10
  }

  /**
   * Connect to WebSocket server
   */
  connect(url: string | null = null): void {
    if (this.ws?.readyState === WebSocket.OPEN) {
      window.logService.debug('WebSocket already connected')
      return
    }

    // Construct WebSocket URL
    if (!url) {
      const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:'
      const host = import.meta.env.VITE_API_URL?.replace(/^https?:\/\//, '') || 'localhost:8000'
      url = `${protocol}//${host}/api/progress/ws`
    }

    const resolvedUrl = url

    window.logService.info('Connecting to WebSocket', { url: resolvedUrl })
    this.ws = new WebSocket(resolvedUrl)

    this.ws.onopen = () => {
      window.logService.info('WebSocket connected')
      this.connected.value = true
      this.reconnectAttempts = 0

      // Notify handlers of connection
      this.handleMessage({ type: 'connected' })
    }

    this.ws.onmessage = (event: MessageEvent) => {
      try {
        const data = JSON.parse(event.data as string) as WebSocketMessage
        this.handleMessage(data)
      } catch (error) {
        window.logService.error('Failed to parse WebSocket message:', error)
      }
    }

    this.ws.onerror = (error: Event) => {
      window.logService.error('WebSocket error:', error)
      this.connected.value = false
    }

    this.ws.onclose = () => {
      window.logService.info('WebSocket disconnected')
      this.connected.value = false

      // Notify handlers of disconnection
      this.handleMessage({ type: 'disconnected' })

      // Attempt reconnection if enabled
      if (this.shouldReconnect && this.reconnectAttempts < this.maxReconnectAttempts) {
        this.reconnectAttempts++
        window.logService.info(`Reconnecting in ${this.reconnectInterval}ms...`, {
          attempt: this.reconnectAttempts,
          maxAttempts: this.maxReconnectAttempts
        })
        setTimeout(() => this.connect(resolvedUrl), this.reconnectInterval)
      }
    }
  }

  /**
   * Handle incoming WebSocket message
   */
  handleMessage(message: WebSocketMessage | { type: string }): void {
    // Log all messages in development
    if (import.meta.env.DEV) {
      window.logService.debug('WebSocket message:', message)
    }

    // Handle ping/pong for keepalive
    if (message.type === 'ping') {
      this.send({ type: 'pong' })
      return
    }

    // Dispatch to registered handlers based on message type
    const handlers = this.messageHandlers.get(message.type) || []
    handlers.forEach(handler => {
      try {
        const data = 'data' in message ? message.data : message
        handler(data)
      } catch (error) {
        window.logService.error('Error in WebSocket message handler:', error)
      }
    })

    // Also dispatch to wildcard handlers
    const wildcardHandlers = this.messageHandlers.get('*') || []
    wildcardHandlers.forEach(handler => {
      try {
        handler(message)
      } catch (error) {
        window.logService.error('Error in WebSocket wildcard handler:', error)
      }
    })
  }

  /**
   * Subscribe to specific message type
   * @returns Unsubscribe function
   */
  subscribe(messageType: string, handler: MessageHandler): () => void {
    if (!this.messageHandlers.has(messageType)) {
      this.messageHandlers.set(messageType, [])
    }
    this.messageHandlers.get(messageType)!.push(handler)

    // Return unsubscribe function
    return () => this.unsubscribe(messageType, handler)
  }

  /**
   * Unsubscribe from message type
   */
  unsubscribe(messageType: string, handler: MessageHandler): void {
    const handlers = this.messageHandlers.get(messageType) || []
    const index = handlers.indexOf(handler)
    if (index > -1) {
      handlers.splice(index, 1)
    }
  }

  /**
   * Send message through WebSocket
   */
  send(message: Record<string, unknown>): void {
    if (this.ws?.readyState === WebSocket.OPEN) {
      this.ws.send(JSON.stringify(message))
    } else {
      window.logService.warn('WebSocket not connected, cannot send message:', message)
    }
  }

  /**
   * Disconnect WebSocket
   */
  disconnect(allowReconnect = false): void {
    this.shouldReconnect = allowReconnect
    if (this.ws) {
      this.ws.close()
      this.ws = null
    }
  }

  /**
   * Get connection status
   */
  isConnected(): boolean {
    return this.connected.value
  }

  /**
   * Reset reconnection attempts
   */
  resetReconnectAttempts(): void {
    this.reconnectAttempts = 0
  }
}

// Create singleton instance
export const wsService = new WebSocketService()

// Helper composable for Vue components
export function useWebSocket() {
  const connected = wsService.connected

  const connect = (url?: string | null) => wsService.connect(url ?? null)
  const disconnect = (allowReconnect?: boolean) => wsService.disconnect(allowReconnect)
  const subscribe = (messageType: string, handler: MessageHandler) =>
    wsService.subscribe(messageType, handler)
  const send = (message: Record<string, unknown>) => wsService.send(message)

  return {
    connected,
    connect,
    disconnect,
    subscribe,
    send
  }
}

export default wsService
