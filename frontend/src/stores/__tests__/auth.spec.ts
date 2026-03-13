/**
 * Auth Store Tests
 *
 * Tests for authentication state management:
 * - Initial state
 * - Login success/failure
 * - Logout behavior
 * - Initialize with silent refresh
 * - isAdmin / hasRole computed properties
 */

import { describe, it, expect, vi, beforeEach } from 'vitest'
import { setActivePinia, createPinia } from 'pinia'

// Stub window.logService before store import
vi.stubGlobal('logService', {
  debug: vi.fn(),
  info: vi.fn(),
  warn: vi.fn(),
  error: vi.fn(),
  critical: vi.fn()
})

// Mock the auth API module
vi.mock('@/api/auth', () => ({
  login: vi.fn(),
  logout: vi.fn(),
  getCurrentUser: vi.fn(),
  refreshToken: vi.fn(),
  requestPasswordReset: vi.fn(),
  resetPassword: vi.fn(),
  changePassword: vi.fn(),
  registerUser: vi.fn(),
  getAllUsers: vi.fn(),
  updateUser: vi.fn(),
  deleteUser: vi.fn(),
  default: {}
}))

// Mock the client module
vi.mock('@/api/client', () => ({
  default: {
    get: vi.fn(),
    post: vi.fn(),
    put: vi.fn(),
    delete: vi.fn()
  },
  setClientAccessToken: vi.fn(),
  getClientAccessToken: vi.fn()
}))

import * as authApi from '@/api/auth'
import { useAuthStore } from '@/stores/auth'
import type { User } from '@/types/auth'

const mockAuthApi = authApi as {
  login: ReturnType<typeof vi.fn>
  logout: ReturnType<typeof vi.fn>
  getCurrentUser: ReturnType<typeof vi.fn>
  refreshToken: ReturnType<typeof vi.fn>
  getAllUsers: ReturnType<typeof vi.fn>
  registerUser: ReturnType<typeof vi.fn>
}

const mockAdminUser: User = {
  id: 1,
  email: 'admin@example.com',
  username: 'admin',
  role: 'admin',
  is_active: true,
  created_at: '2024-01-01T00:00:00Z',
  updated_at: '2024-01-01T00:00:00Z'
}

const mockCuratorUser: User = {
  id: 2,
  email: 'curator@example.com',
  username: 'curator',
  role: 'curator',
  is_active: true,
  created_at: '2024-01-01T00:00:00Z',
  updated_at: '2024-01-01T00:00:00Z'
}

describe('useAuthStore', () => {
  beforeEach(() => {
    // Fresh Pinia for each test
    setActivePinia(createPinia())
    vi.clearAllMocks()

    // Clear localStorage
    localStorage.clear()
  })

  describe('initial state', () => {
    it('starts unauthenticated with null user and no tokens', () => {
      const store = useAuthStore()

      expect(store.user).toBeNull()
      expect(store.accessToken).toBeNull()
      expect(store.refreshToken).toBeNull()
      expect(store.isLoading).toBe(false)
      expect(store.error).toBeNull()
    })

    it('tokens are memory-only (not read from localStorage)', () => {
      localStorage.setItem('access_token', 'stored-access')
      localStorage.setItem('refresh_token', 'stored-refresh')

      const store = useAuthStore()

      // Tokens should be null — no longer read from localStorage
      expect(store.accessToken).toBeNull()
      expect(store.refreshToken).toBeNull()
    })

    it('isAuthenticated is false when user is null even with token', () => {
      const store = useAuthStore()
      store.accessToken = 'some-token'
      // user is null, so not authenticated
      expect(store.isAuthenticated).toBe(false)
    })
  })

  describe('login', () => {
    it('returns true and sets access token on successful login', async () => {
      mockAuthApi.login.mockResolvedValue({
        access_token: 'new-access',
        token_type: 'bearer'
      })
      mockAuthApi.getCurrentUser.mockResolvedValue(mockAdminUser)

      const store = useAuthStore()
      const result = await store.login('admin', 'password')

      expect(result).toBe(true)
      expect(store.accessToken).toBe('new-access')
      expect(store.user).toEqual(mockAdminUser)
      expect(store.error).toBeNull()
      // Access token should NOT be in localStorage
      expect(localStorage.getItem('access_token')).toBeNull()
    })

    it('returns false and sets error on failed login', async () => {
      mockAuthApi.login.mockRejectedValue({
        response: { data: { detail: 'Invalid credentials' } }
      })

      const store = useAuthStore()
      const result = await store.login('bad', 'creds')

      expect(result).toBe(false)
      expect(store.error).toBe('Invalid credentials')
      expect(store.user).toBeNull()
    })

    it('sets isLoading during login and resets after', async () => {
      let loadingDuringCall = false
      mockAuthApi.login.mockImplementation(async () => {
        loadingDuringCall = true
        return {
          access_token: 'tok',
          token_type: 'bearer'
        }
      })
      mockAuthApi.getCurrentUser.mockResolvedValue(mockAdminUser)

      const store = useAuthStore()
      const loginPromise = store.login('user', 'pass')

      // isLoading set synchronously before await resolves
      expect(store.isLoading).toBe(true)
      await loginPromise
      expect(loadingDuringCall).toBe(true)
      expect(store.isLoading).toBe(false)
    })
  })

  describe('computed getters', () => {
    it('isAdmin is true for admin user', async () => {
      mockAuthApi.login.mockResolvedValue({
        access_token: 'tok',
        token_type: 'bearer'
      })
      mockAuthApi.getCurrentUser.mockResolvedValue(mockAdminUser)

      const store = useAuthStore()
      await store.login('admin', 'pass')

      expect(store.isAdmin).toBe(true)
      expect(store.isCurator).toBe(true) // admin is also curator
    })

    it('isAdmin is false for curator user', async () => {
      mockAuthApi.login.mockResolvedValue({
        access_token: 'tok',
        token_type: 'bearer'
      })
      mockAuthApi.getCurrentUser.mockResolvedValue(mockCuratorUser)

      const store = useAuthStore()
      await store.login('curator', 'pass')

      expect(store.isAdmin).toBe(false)
      expect(store.isCurator).toBe(true)
    })

    it('hasRole returns true when role matches', async () => {
      mockAuthApi.login.mockResolvedValue({
        access_token: 'tok',
        token_type: 'bearer'
      })
      mockAuthApi.getCurrentUser.mockResolvedValue(mockAdminUser)

      const store = useAuthStore()
      await store.login('admin', 'pass')

      expect(store.hasRole('admin')).toBe(true)
      expect(store.hasRole(['admin', 'curator'])).toBe(true)
      expect(store.hasRole('curator')).toBe(false)
    })

    it('userRole returns "anonymous" when not logged in', () => {
      const store = useAuthStore()
      expect(store.userRole).toBe('anonymous')
    })
  })

  describe('initialize', () => {
    it('skips refresh when no prior session exists (no stored user)', async () => {
      // No 'user' in localStorage → anonymous visitor, should not call refresh
      const store = useAuthStore()
      await store.initialize()

      expect(mockAuthApi.refreshToken).not.toHaveBeenCalled()
      expect(store.user).toBeNull()
      expect(store.accessToken).toBeNull()
    })

    it('restores user from localStorage and attempts silent refresh', async () => {
      localStorage.setItem('user', JSON.stringify(mockAdminUser))
      mockAuthApi.refreshToken.mockResolvedValue({ access_token: 'refreshed-token' })
      mockAuthApi.getCurrentUser.mockResolvedValue(mockAdminUser)

      const store = useAuthStore()
      await store.initialize()

      expect(store.user).toEqual(mockAdminUser)
      // Should attempt silent refresh via cookie
      expect(mockAuthApi.refreshToken).toHaveBeenCalled()
      expect(store.accessToken).toBe('refreshed-token')
    })

    it('clears auth state when silent refresh fails', async () => {
      localStorage.setItem('user', JSON.stringify(mockAdminUser))
      mockAuthApi.refreshToken.mockRejectedValue(new Error('No cookie'))

      const store = useAuthStore()
      await store.initialize()

      // User should be cleared since refresh failed
      expect(store.user).toBeNull()
      expect(store.accessToken).toBeNull()
    })
  })

  describe('clearError', () => {
    it('clears error state', async () => {
      mockAuthApi.login.mockRejectedValue({
        response: { data: { detail: 'Bad credentials' } }
      })

      const store = useAuthStore()
      await store.login('bad', 'creds')
      expect(store.error).toBe('Bad credentials')

      store.clearError()
      expect(store.error).toBeNull()
    })
  })
})
