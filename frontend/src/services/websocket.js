/**
 * WebSocket Service for real-time updates
 * Implements event-driven architecture for pipeline progress monitoring
 */

import { ref } from 'vue'

class WebSocketService {
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
   * @param {string} url - WebSocket URL (defaults to progress endpoint)
   */
  connect(url = null) {
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

    window.logService.info('Connecting to WebSocket', { url })
    this.ws = new WebSocket(url)

    this.ws.onopen = () => {
      window.logService.info('WebSocket connected')
      this.connected.value = true
      this.reconnectAttempts = 0

      // Notify handlers of connection
      this.handleMessage({ type: 'connected' })
    }

    this.ws.onmessage = event => {
      try {
        const data = JSON.parse(event.data)
        this.handleMessage(data)
      } catch (error) {
        window.logService.error('Failed to parse WebSocket message:', error)
      }
    }

    this.ws.onerror = error => {
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
        setTimeout(() => this.connect(url), this.reconnectInterval)
      }
    }
  }

  /**
   * Handle incoming WebSocket message
   * @param {Object} message - Parsed message object
   */
  handleMessage(message) {
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
        handler(message.data || message)
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
   * @param {string} messageType - Type of message to subscribe to (* for all)
   * @param {Function} handler - Handler function to call
   * @returns {Function} Unsubscribe function
   */
  subscribe(messageType, handler) {
    if (!this.messageHandlers.has(messageType)) {
      this.messageHandlers.set(messageType, [])
    }
    this.messageHandlers.get(messageType).push(handler)

    // Return unsubscribe function
    return () => this.unsubscribe(messageType, handler)
  }

  /**
   * Unsubscribe from message type
   * @param {string} messageType - Type of message to unsubscribe from
   * @param {Function} handler - Handler function to remove
   */
  unsubscribe(messageType, handler) {
    const handlers = this.messageHandlers.get(messageType) || []
    const index = handlers.indexOf(handler)
    if (index > -1) {
      handlers.splice(index, 1)
    }
  }

  /**
   * Send message through WebSocket
   * @param {Object} message - Message to send
   */
  send(message) {
    if (this.ws?.readyState === WebSocket.OPEN) {
      this.ws.send(JSON.stringify(message))
    } else {
      window.logService.warn('WebSocket not connected, cannot send message:', message)
    }
  }

  /**
   * Disconnect WebSocket
   * @param {boolean} allowReconnect - Whether to allow automatic reconnection
   */
  disconnect(allowReconnect = false) {
    this.shouldReconnect = allowReconnect
    if (this.ws) {
      this.ws.close()
      this.ws = null
    }
  }

  /**
   * Get connection status
   * @returns {boolean} Whether WebSocket is connected
   */
  isConnected() {
    return this.connected.value
  }

  /**
   * Reset reconnection attempts
   */
  resetReconnectAttempts() {
    this.reconnectAttempts = 0
  }
}

// Create singleton instance
export const wsService = new WebSocketService()

// Helper composable for Vue components
export function useWebSocket() {
  const connected = wsService.connected

  const connect = url => wsService.connect(url)
  const disconnect = allowReconnect => wsService.disconnect(allowReconnect)
  const subscribe = (messageType, handler) => wsService.subscribe(messageType, handler)
  const send = message => wsService.send(message)

  return {
    connected,
    connect,
    disconnect,
    subscribe,
    send
  }
}

export default wsService
