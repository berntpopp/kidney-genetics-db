/**
 * Authentication Store
 * Manages user authentication state and operations
 * Following Pinia best practices and Vue 3 composition API
 */

import { defineStore } from 'pinia'
import { ref, computed, watch } from 'vue'
import type { User, UserRole } from '@/types/auth'
import * as authApi from '@/api/auth'
import { setClientAccessToken } from '@/api/client'

/** Extract detail message from API error responses (supports JSON:API wrapper format) */
type ApiError = { response?: { data?: { detail?: string; error?: { detail?: string } } } }
function extractErrorDetail(err: unknown, fallback: string): string {
  const apiErr = err as ApiError
  return apiErr.response?.data?.error?.detail ?? apiErr.response?.data?.detail ?? fallback
}

export const useAuthStore = defineStore('auth', () => {
  // State - using refs for reactivity
  // Access token is memory-only (not persisted to localStorage)
  // Refresh token is now in HttpOnly cookie — not accessible from JS
  const user = ref<User | null>(null)
  const accessToken = ref<string | null>(null)
  const refreshToken = ref<string | null>(null)
  const isLoading = ref(false)
  const error = ref<string | null>(null)

  // Getters - computed properties
  const isAuthenticated = computed<boolean>(() => !!accessToken.value && !!user.value)
  const isAdmin = computed<boolean>(() => user.value?.role === 'admin')
  const isCurator = computed<boolean>(() => user.value?.role === 'curator' || isAdmin.value)
  const userRole = computed<UserRole | 'anonymous'>(() => user.value?.role ?? 'anonymous')
  const userPermissions = computed<string[]>(() => [])

  // Check if user has specific permission
  // eslint-disable-next-line no-unused-vars
  const hasPermission = computed<(permission: string) => boolean>(() => (permission: string) => {
    return userPermissions.value.includes(permission)
  })

  // Check if user has any of the required roles
  // eslint-disable-next-line no-unused-vars
  const hasRole = computed<(role: UserRole | UserRole[]) => boolean>(
    () => (role: UserRole | UserRole[]) => {
      if (!user.value) return false
      if (Array.isArray(role)) {
        return role.includes(user.value.role)
      }
      return user.value.role === role
    }
  )

  // Actions

  /**
   * Login user with credentials
   * @param username - Username or email
   * @param password - Password
   * @returns Success status
   */
  async function login(username: string, password: string): Promise<boolean> {
    isLoading.value = true
    error.value = null

    try {
      const response = await authApi.login(username, password)

      // Store access token in memory only (refresh token is in HttpOnly cookie)
      accessToken.value = response.access_token

      // Fetch user info
      await fetchCurrentUser()

      return true
    } catch (err: unknown) {
      error.value = extractErrorDetail(err, 'Login failed')
      window.logService.error('Login error:', err)
      return false
    } finally {
      isLoading.value = false
    }
  }

  /**
   * Logout current user
   */
  async function logout(): Promise<void> {
    try {
      // Call logout endpoint (will invalidate refresh token on server)
      await authApi.logout()
    } catch (err: unknown) {
      // Continue with logout even if request fails
      window.logService.error('Logout request failed:', err)
    } finally {
      // Clear local state (refresh token cookie is cleared by server)
      user.value = null
      accessToken.value = null
      refreshToken.value = null
      localStorage.removeItem('user')

      // Redirect to home (let router handle this via navigation guard)
      window.location.href = '/'
    }
  }

  /**
   * Fetch current user information
   */
  async function fetchCurrentUser(): Promise<void> {
    if (!accessToken.value) return

    try {
      const userData = await authApi.getCurrentUser()
      user.value = userData
      localStorage.setItem('user', JSON.stringify(userData))
    } catch (err: unknown) {
      window.logService.error('Failed to fetch user:', err)
      // If fetch fails, token might be invalid
      const apiErr = err as { response?: { status?: number } }
      if (apiErr.response?.status === 401) {
        await logout()
      }
    }
  }

  /**
   * Initialize auth state — attempts silent refresh only if a prior session exists.
   *
   * A stored 'user' in localStorage signals the user was previously logged in,
   * meaning an HttpOnly refresh cookie may still be valid. Without this guard,
   * every anonymous page load would fire a failing POST /api/auth/refresh.
   */
  async function initialize(): Promise<void> {
    const storedUser = localStorage.getItem('user')
    if (!storedUser) {
      // Never logged in — skip the network request entirely
      return
    }

    // Restore cached user as optimistic state while we verify the session
    try {
      user.value = JSON.parse(storedUser) as User
    } catch {
      localStorage.removeItem('user')
      return
    }

    // Attempt silent refresh to get a fresh access token from the cookie
    try {
      const response = await authApi.refreshToken()
      accessToken.value = response.access_token
      await fetchCurrentUser()
    } catch {
      // Cookie expired or was cleared — clean up stale local state
      accessToken.value = null
      user.value = null
      localStorage.removeItem('user')
    }
  }

  /**
   * Refresh access token using HttpOnly cookie
   */
  async function refreshAccessToken(): Promise<boolean> {
    try {
      const response = await authApi.refreshToken()
      accessToken.value = response.access_token
      return true
    } catch (err: unknown) {
      window.logService.error('Token refresh failed:', err)
      // Refresh failed, logout user
      await logout()
      return false
    }
  }

  /**
   * Request password reset
   * @param email - User email
   */
  async function requestPasswordReset(email: string): Promise<boolean> {
    isLoading.value = true
    error.value = null

    try {
      await authApi.requestPasswordReset(email)
      return true
    } catch (err: unknown) {
      error.value = extractErrorDetail(err, 'Failed to send reset email')
      return false
    } finally {
      isLoading.value = false
    }
  }

  /**
   * Reset password with token
   * @param token - Reset token
   * @param newPassword - New password
   */
  async function resetPassword(token: string, newPassword: string): Promise<boolean> {
    isLoading.value = true
    error.value = null

    try {
      await authApi.resetPassword(token, newPassword)
      return true
    } catch (err: unknown) {
      error.value = extractErrorDetail(err, 'Failed to reset password')
      return false
    } finally {
      isLoading.value = false
    }
  }

  /**
   * Change password for current user
   * @param currentPassword - Current password
   * @param newPassword - New password
   */
  async function changePassword(currentPassword: string, newPassword: string): Promise<boolean> {
    isLoading.value = true
    error.value = null

    try {
      await authApi.changePassword(currentPassword, newPassword)
      return true
    } catch (err: unknown) {
      error.value = extractErrorDetail(err, 'Failed to change password')
      return false
    } finally {
      isLoading.value = false
    }
  }

  // Admin actions

  /**
   * Register new user (admin only)
   * @param userData - User registration data
   */
  async function registerUser(userData: Record<string, unknown>): Promise<User> {
    if (!isAdmin.value) {
      throw new Error('Admin access required')
    }

    isLoading.value = true
    error.value = null

    try {
      const newUser = await authApi.registerUser(userData)
      return newUser
    } catch (err: unknown) {
      error.value = extractErrorDetail(err, 'Failed to register user')
      throw err
    } finally {
      isLoading.value = false
    }
  }

  /**
   * Get all users (admin only)
   */
  async function getAllUsers(): Promise<User[]> {
    if (!isAdmin.value) {
      throw new Error('Admin access required')
    }

    return await authApi.getAllUsers()
  }

  /**
   * Update user (admin only)
   * @param userId - User ID
   * @param updates - User updates
   */
  async function updateUser(userId: number, updates: Partial<User>): Promise<User> {
    if (!isAdmin.value) {
      throw new Error('Admin access required')
    }

    return await authApi.updateUser(userId, updates)
  }

  /**
   * Delete user (admin only)
   * @param userId - User ID
   */
  async function deleteUser(userId: number): Promise<{ detail: string }> {
    if (!isAdmin.value) {
      throw new Error('Admin access required')
    }

    return await authApi.deleteUser(userId)
  }

  /**
   * Clear error state
   */
  function clearError(): void {
    error.value = null
  }

  // Sync access token to API client module-level variable
  watch(accessToken, newToken => {
    setClientAccessToken(newToken)
  })

  // Listen for logout event from API client
  window.addEventListener('auth:logout', logout)

  // Return store properties and methods
  return {
    // State
    user,
    accessToken,
    refreshToken,
    isLoading,
    error,

    // Getters
    isAuthenticated,
    isAdmin,
    isCurator,
    userRole,
    userPermissions,
    hasPermission,
    hasRole,

    // Actions
    login,
    logout,
    fetchCurrentUser,
    initialize,
    refreshAccessToken,
    requestPasswordReset,
    resetPassword,
    changePassword,
    registerUser,
    getAllUsers,
    updateUser,
    deleteUser,
    clearError
  }
})
