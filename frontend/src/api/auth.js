/**
 * Authentication API endpoints
 */

import apiClient from './client'

/**
 * Login with username/email and password
 * @param {string} username - Username or email
 * @param {string} password - Password
 * @returns {Promise} Authentication tokens and user info
 */
export const login = async (username, password) => {
  // Use URLSearchParams for OAuth2 password flow
  const formData = new URLSearchParams()
  formData.append('username', username)
  formData.append('password', password)
  formData.append('grant_type', 'password')

  const response = await apiClient.post('/api/auth/login', formData, {
    headers: {
      'Content-Type': 'application/x-www-form-urlencoded'
    }
  })

  return response.data
}

/**
 * Logout current user
 * @returns {Promise}
 */
export const logout = async () => {
  try {
    await apiClient.post('/api/auth/logout', {})
  } catch (error) {
    // Logout anyway even if request fails
    window.logService.error('Logout request failed:', error)
  }
}

/**
 * Get current user information
 * @returns {Promise} Current user data
 */
export const getCurrentUser = async () => {
  const response = await apiClient.get('/api/auth/me')

  return response.data
}

/**
 * Refresh access token
 * @param {string} refreshToken - Refresh token
 * @returns {Promise} New access token
 */
export const refreshToken = async refreshToken => {
  const response = await apiClient.post('/api/auth/refresh', {
    refresh_token: refreshToken
  })

  return response.data
}

/**
 * Request password reset
 * @param {string} email - User email
 * @returns {Promise}
 */
export const requestPasswordReset = async email => {
  const response = await apiClient.post('/api/auth/forgot-password', {
    email
  })

  return response.data
}

/**
 * Reset password with token
 * @param {string} token - Reset token
 * @param {string} newPassword - New password
 * @returns {Promise}
 */
export const resetPassword = async (token, newPassword) => {
  const response = await apiClient.post('/api/auth/reset-password', {
    token,
    new_password: newPassword
  })

  return response.data
}

/**
 * Change password for current user
 * @param {string} currentPassword - Current password
 * @param {string} newPassword - New password
 * @returns {Promise}
 */
export const changePassword = async (currentPassword, newPassword) => {
  const response = await apiClient.post('/api/auth/change-password', {
    current_password: currentPassword,
    new_password: newPassword
  })

  return response.data
}

// Admin endpoints

/**
 * Register new user (admin only)
 * @param {Object} userData - User registration data
 * @returns {Promise} Created user
 */
export const registerUser = async userData => {
  const response = await apiClient.post('/api/auth/register', userData)

  return response.data
}

/**
 * Get all users (admin only)
 * @returns {Promise} List of users
 */
export const getAllUsers = async () => {
  const response = await apiClient.get('/api/auth/users')

  return response.data
}

/**
 * Update user (admin only)
 * @param {number} userId - User ID
 * @param {Object} updates - User updates
 * @returns {Promise} Updated user
 */
export const updateUser = async (userId, updates) => {
  const response = await apiClient.put(`/api/auth/users/${userId}`, updates)

  return response.data
}

/**
 * Delete user (admin only)
 * @param {number} userId - User ID
 * @returns {Promise}
 */
export const deleteUser = async userId => {
  const response = await apiClient.delete(`/api/auth/users/${userId}`)

  return response.data
}

export default {
  login,
  logout,
  getCurrentUser,
  refreshToken,
  requestPasswordReset,
  resetPassword,
  changePassword,
  registerUser,
  getAllUsers,
  updateUser,
  deleteUser
}
