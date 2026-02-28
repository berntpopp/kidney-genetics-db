/**
 * Tests for auth.ts API module
 * Mocks the Axios client and verifies correct request construction.
 */

import { describe, it, expect, vi, beforeEach } from 'vitest'
import type { AxiosResponse } from 'axios'

// Mock the API client
vi.mock('@/api/client', () => ({
  default: {
    get: vi.fn(),
    post: vi.fn(),
    put: vi.fn(),
    delete: vi.fn()
  }
}))

// Stub window.logService (used in logout error handler)
vi.stubGlobal('logService', {
  debug: vi.fn(),
  info: vi.fn(),
  warn: vi.fn(),
  error: vi.fn(),
  critical: vi.fn()
})

import apiClient from '@/api/client'
import { login, getCurrentUser, refreshToken, logout, getAllUsers } from '@/api/auth'

const mockApiClient = apiClient as {
  get: ReturnType<typeof vi.fn>
  post: ReturnType<typeof vi.fn>
  put: ReturnType<typeof vi.fn>
  delete: ReturnType<typeof vi.fn>
}

describe('authApi', () => {
  beforeEach(() => {
    vi.clearAllMocks()
  })

  describe('login', () => {
    it('should POST to /api/auth/login with URLSearchParams form data', async () => {
      const mockResponse: Partial<AxiosResponse> = {
        data: { access_token: 'abc', refresh_token: 'xyz', token_type: 'bearer' }
      }
      mockApiClient.post.mockResolvedValue(mockResponse)

      const result = await login('testuser', 'testpass')

      // Verify endpoint
      expect(mockApiClient.post).toHaveBeenCalledWith(
        '/api/auth/login',
        expect.any(URLSearchParams),
        { headers: { 'Content-Type': 'application/x-www-form-urlencoded' } }
      )

      // Verify form data contains correct fields
      const [, body] = mockApiClient.post.mock.calls[0] as [string, URLSearchParams, unknown]
      expect(body.get('username')).toBe('testuser')
      expect(body.get('password')).toBe('testpass')
      expect(body.get('grant_type')).toBe('password')

      // Verify return value
      expect(result.access_token).toBe('abc')
    })
  })

  describe('getCurrentUser', () => {
    it('should GET /api/auth/me and return user data', async () => {
      const mockUser = {
        id: 1,
        email: 'admin@example.com',
        username: 'admin',
        role: 'admin' as const,
        is_active: true,
        created_at: '2024-01-01',
        updated_at: '2024-01-01'
      }
      mockApiClient.get.mockResolvedValue({ data: mockUser })

      const result = await getCurrentUser()

      expect(mockApiClient.get).toHaveBeenCalledWith('/api/auth/me')
      expect(result.id).toBe(1)
      expect(result.email).toBe('admin@example.com')
    })
  })

  describe('refreshToken', () => {
    it('should POST refresh token to /api/auth/refresh', async () => {
      mockApiClient.post.mockResolvedValue({
        data: { access_token: 'new-token', token_type: 'bearer' }
      })

      const result = await refreshToken('old-refresh-token')

      expect(mockApiClient.post).toHaveBeenCalledWith('/api/auth/refresh', {
        refresh_token: 'old-refresh-token'
      })
      expect(result.access_token).toBe('new-token')
    })
  })

  describe('logout', () => {
    it('should POST to /api/auth/logout', async () => {
      mockApiClient.post.mockResolvedValue({ data: {} })

      await logout()

      expect(mockApiClient.post).toHaveBeenCalledWith('/api/auth/logout', {})
    })

    it('should not throw when logout request fails (swallows errors)', async () => {
      mockApiClient.post.mockRejectedValue(new Error('Network error'))

      // Should not throw — logout always completes
      await expect(logout()).resolves.toBeUndefined()
      expect(window.logService.error).toHaveBeenCalled()
    })
  })

  describe('getAllUsers', () => {
    it('should GET /api/auth/users and return user array', async () => {
      const users = [
        {
          id: 1,
          email: 'admin@example.com',
          username: 'admin',
          role: 'admin' as const,
          is_active: true,
          created_at: '2024-01-01',
          updated_at: '2024-01-01'
        }
      ]
      mockApiClient.get.mockResolvedValue({ data: users })

      const result = await getAllUsers()

      expect(mockApiClient.get).toHaveBeenCalledWith('/api/auth/users')
      expect(result).toHaveLength(1)
      expect(result[0].username).toBe('admin')
    })
  })
})
