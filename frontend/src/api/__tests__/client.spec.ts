/**
 * Tests for Axios API client (client.ts)
 * Verifies that apiClient is configured correctly and interceptors behave as expected.
 */

import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest'

// Mock localStorage for interceptor tests
const localStorageMock = {
  store: {} as Record<string, string>,
  getItem(key: string) {
    return this.store[key] ?? null
  },
  setItem(key: string, value: string) {
    this.store[key] = value
  },
  removeItem(key: string) {
    delete this.store[key]
  },
  clear() {
    this.store = {}
  }
}

// Mock window.logService so auth.ts imports don't fail
vi.stubGlobal('logService', {
  debug: vi.fn(),
  info: vi.fn(),
  warn: vi.fn(),
  error: vi.fn(),
  critical: vi.fn()
})

// Mock window._env_ to control API_BASE_URL
vi.stubGlobal('_env_', { API_BASE_URL: 'http://test-api:8000' })

Object.defineProperty(global, 'localStorage', { value: localStorageMock, writable: true })

// Import after mocks are set up
import apiClient from '@/api/client'

describe('apiClient', () => {
  beforeEach(() => {
    localStorageMock.clear()
    vi.clearAllMocks()
  })

  afterEach(() => {
    localStorageMock.clear()
  })

  it('should be an Axios instance with get, post, put, delete methods', () => {
    expect(typeof apiClient.get).toBe('function')
    expect(typeof apiClient.post).toBe('function')
    expect(typeof apiClient.put).toBe('function')
    expect(typeof apiClient.delete).toBe('function')
  })

  it('should have request and response interceptors registered', () => {
    // Verify interceptors exist on the apiClient instance
    // Axios stores handlers in an internal array accessible via interceptors.request.handlers
    // We check that interceptors were added (length > 0 means handlers are registered)
    const requestHandlers = (apiClient.interceptors.request as unknown as { handlers: unknown[] }).handlers
    const responseHandlers = (apiClient.interceptors.response as unknown as { handlers: unknown[] }).handlers

    expect(requestHandlers).toBeDefined()
    expect(requestHandlers.length).toBeGreaterThan(0)
    expect(responseHandlers).toBeDefined()
    expect(responseHandlers.length).toBeGreaterThan(0)
  })

  it('should set Authorization header when access_token is in localStorage', () => {
    // Simulate a stored token
    localStorageMock.setItem('access_token', 'test-jwt-token')

    // Manually invoke the request interceptor
    const requestInterceptor = (apiClient.interceptors.request as unknown as {
      handlers: Array<{ fulfilled: (config: Record<string, unknown>) => Record<string, unknown> }>
    }).handlers[0]

    if (!requestInterceptor) {
      // If running in environment where interceptors aren't accessible, skip
      return
    }

    const config = { headers: {} as Record<string, string> }
    const result = requestInterceptor.fulfilled(config)

    expect(result.headers).toBeDefined()
    expect((result.headers as Record<string, string>)['Authorization']).toBe('Bearer test-jwt-token')
  })
})
