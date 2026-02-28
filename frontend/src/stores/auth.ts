/**
 * Authentication Store
 * Manages user authentication state and operations
 * Following Pinia best practices and Vue 3 composition API
 */

import { defineStore } from 'pinia'
import { ref, computed } from 'vue'
import type { User, UserRole } from '@/types/auth'
import * as authApi from '@/api/auth'

export const useAuthStore = defineStore('auth', () => {
  // State - using refs for reactivity
  const user = ref<User | null>(null)
  const accessToken = ref<string | null>(localStorage.getItem('access_token'))
  const refreshToken = ref<string | null>(localStorage.getItem('refresh_token'))
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

      // Store tokens
      accessToken.value = response.access_token
      refreshToken.value = response.refresh_token
      localStorage.setItem('access_token', response.access_token)
      localStorage.setItem('refresh_token', response.refresh_token)

      // Fetch user info
      await fetchCurrentUser()

      return true
    } catch (err: unknown) {
      const apiErr = err as { response?: { data?: { detail?: string } } }
      error.value = apiErr.response?.data?.detail ?? 'Login failed'
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
      // Clear local state
      user.value = null
      accessToken.value = null
      refreshToken.value = null
      localStorage.removeItem('access_token')
      localStorage.removeItem('refresh_token')
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
   * Initialize auth state from localStorage
   */
  async function initialize(): Promise<void> {
    // Try to restore user from localStorage
    const storedUser = localStorage.getItem('user')
    if (storedUser) {
      try {
        user.value = JSON.parse(storedUser) as User
      } catch (err: unknown) {
        window.logService.error('Failed to parse stored user:', err)
      }
    }

    // If we have a token but no user, fetch user info
    if (accessToken.value && !user.value) {
      await fetchCurrentUser()
    }
  }

  /**
   * Refresh access token using refresh token
   */
  async function refreshAccessToken(): Promise<boolean> {
    if (!refreshToken.value) return false

    try {
      const response = await authApi.refreshToken(refreshToken.value)
      accessToken.value = response.access_token
      localStorage.setItem('access_token', response.access_token)
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
      const apiErr = err as { response?: { data?: { detail?: string } } }
      error.value = apiErr.response?.data?.detail ?? 'Failed to send reset email'
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
      const apiErr = err as { response?: { data?: { detail?: string } } }
      error.value = apiErr.response?.data?.detail ?? 'Failed to reset password'
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
      const apiErr = err as { response?: { data?: { detail?: string } } }
      error.value = apiErr.response?.data?.detail ?? 'Failed to change password'
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
      const apiErr = err as { response?: { data?: { detail?: string } } }
      error.value = apiErr.response?.data?.detail ?? 'Failed to register user'
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
