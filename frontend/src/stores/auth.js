/**
 * Authentication Store
 * Manages user authentication state and operations
 * Following Pinia best practices and Vue 3 composition API
 */

import { defineStore } from 'pinia'
import { ref, computed } from 'vue'
import * as authApi from '@/api/auth'

export const useAuthStore = defineStore('auth', () => {
  // State - using refs for reactivity
  const user = ref(null)
  const accessToken = ref(localStorage.getItem('access_token'))
  const refreshToken = ref(localStorage.getItem('refresh_token'))
  const isLoading = ref(false)
  const error = ref(null)

  // Getters - computed properties
  const isAuthenticated = computed(() => !!accessToken.value && !!user.value)
  const isAdmin = computed(() => user.value?.role === 'admin')
  const isCurator = computed(() => user.value?.role === 'curator' || isAdmin.value)
  const userRole = computed(() => user.value?.role || 'anonymous')
  const userPermissions = computed(() => user.value?.permissions || [])

  // Check if user has specific permission
  const hasPermission = computed(() => permission => {
    return userPermissions.value.includes(permission)
  })

  // Check if user has any of the required roles
  const hasRole = computed(() => role => {
    if (!user.value) return false
    if (Array.isArray(role)) {
      return role.includes(user.value.role)
    }
    return user.value.role === role
  })

  // Actions

  /**
   * Login user with credentials
   * @param {string} username - Username or email
   * @param {string} password - Password
   * @returns {Promise<boolean>} Success status
   */
  async function login(username, password) {
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
    } catch (err) {
      error.value = err.response?.data?.detail || 'Login failed'
      window.logService.error('Login error:', err)
      return false
    } finally {
      isLoading.value = false
    }
  }

  /**
   * Logout current user
   */
  async function logout() {
    try {
      // Call logout endpoint (will invalidate refresh token on server)
      await authApi.logout()
    } catch (err) {
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
  async function fetchCurrentUser() {
    if (!accessToken.value) return

    try {
      const userData = await authApi.getCurrentUser()
      user.value = userData
      localStorage.setItem('user', JSON.stringify(userData))
    } catch (err) {
      window.logService.error('Failed to fetch user:', err)
      // If fetch fails, token might be invalid
      if (err.response?.status === 401) {
        await logout()
      }
    }
  }

  /**
   * Initialize auth state from localStorage
   */
  async function initialize() {
    // Try to restore user from localStorage
    const storedUser = localStorage.getItem('user')
    if (storedUser) {
      try {
        user.value = JSON.parse(storedUser)
      } catch (err) {
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
  async function refreshAccessToken() {
    if (!refreshToken.value) return false

    try {
      const response = await authApi.refreshToken(refreshToken.value)
      accessToken.value = response.access_token
      localStorage.setItem('access_token', response.access_token)
      return true
    } catch (err) {
      window.logService.error('Token refresh failed:', err)
      // Refresh failed, logout user
      await logout()
      return false
    }
  }

  /**
   * Request password reset
   * @param {string} email - User email
   */
  async function requestPasswordReset(email) {
    isLoading.value = true
    error.value = null

    try {
      await authApi.requestPasswordReset(email)
      return true
    } catch (err) {
      error.value = err.response?.data?.detail || 'Failed to send reset email'
      return false
    } finally {
      isLoading.value = false
    }
  }

  /**
   * Reset password with token
   * @param {string} token - Reset token
   * @param {string} newPassword - New password
   */
  async function resetPassword(token, newPassword) {
    isLoading.value = true
    error.value = null

    try {
      await authApi.resetPassword(token, newPassword)
      return true
    } catch (err) {
      error.value = err.response?.data?.detail || 'Failed to reset password'
      return false
    } finally {
      isLoading.value = false
    }
  }

  /**
   * Change password for current user
   * @param {string} currentPassword - Current password
   * @param {string} newPassword - New password
   */
  async function changePassword(currentPassword, newPassword) {
    isLoading.value = true
    error.value = null

    try {
      await authApi.changePassword(currentPassword, newPassword)
      return true
    } catch (err) {
      error.value = err.response?.data?.detail || 'Failed to change password'
      return false
    } finally {
      isLoading.value = false
    }
  }

  // Admin actions

  /**
   * Register new user (admin only)
   * @param {Object} userData - User registration data
   */
  async function registerUser(userData) {
    if (!isAdmin.value) {
      throw new Error('Admin access required')
    }

    isLoading.value = true
    error.value = null

    try {
      const newUser = await authApi.registerUser(userData)
      return newUser
    } catch (err) {
      error.value = err.response?.data?.detail || 'Failed to register user'
      throw err
    } finally {
      isLoading.value = false
    }
  }

  /**
   * Get all users (admin only)
   */
  async function getAllUsers() {
    if (!isAdmin.value) {
      throw new Error('Admin access required')
    }

    return await authApi.getAllUsers()
  }

  /**
   * Update user (admin only)
   * @param {number} userId - User ID
   * @param {Object} updates - User updates
   */
  async function updateUser(userId, updates) {
    if (!isAdmin.value) {
      throw new Error('Admin access required')
    }

    return await authApi.updateUser(userId, updates)
  }

  /**
   * Delete user (admin only)
   * @param {number} userId - User ID
   */
  async function deleteUser(userId) {
    if (!isAdmin.value) {
      throw new Error('Admin access required')
    }

    return await authApi.deleteUser(userId)
  }

  /**
   * Clear error state
   */
  function clearError() {
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
