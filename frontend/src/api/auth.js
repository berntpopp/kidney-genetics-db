/**
 * Authentication API endpoints
 */

import axios from 'axios'

const API_BASE_URL = import.meta.env.VITE_API_URL || 'http://localhost:8000'

// Create separate axios instance for auth to avoid circular dependencies
const authClient = axios.create({
  baseURL: API_BASE_URL,
  headers: {
    'Content-Type': 'application/json'
  }
})

/**
 * Login with username/email and password
 * @param {string} username - Username or email
 * @param {string} password - Password
 * @returns {Promise} Authentication tokens and user info
 */
export const login = async (username, password) => {
  // Use URLSearchParams for OAuth2 password flow
  const formData = new URLSearchParams() // eslint-disable-line no-undef
  formData.append('username', username)
  formData.append('password', password)
  formData.append('grant_type', 'password')

  const response = await authClient.post('/api/auth/login', formData, {
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
  const token = localStorage.getItem('access_token')
  if (!token) return

  try {
    await authClient.post(
      '/api/auth/logout',
      {},
      {
        headers: {
          Authorization: `Bearer ${token}`
        }
      }
    )
  } catch (error) {
    // Logout anyway even if request fails
    console.error('Logout request failed:', error)
  }
}

/**
 * Get current user information
 * @returns {Promise} Current user data
 */
export const getCurrentUser = async () => {
  const token = localStorage.getItem('access_token')
  if (!token) throw new Error('No authentication token')

  const response = await authClient.get('/api/auth/me', {
    headers: {
      Authorization: `Bearer ${token}`
    }
  })

  return response.data
}

/**
 * Refresh access token
 * @param {string} refreshToken - Refresh token
 * @returns {Promise} New access token
 */
export const refreshToken = async refreshToken => {
  const response = await authClient.post('/api/auth/refresh', {
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
  const response = await authClient.post('/api/auth/forgot-password', {
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
  const response = await authClient.post('/api/auth/reset-password', {
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
  const token = localStorage.getItem('access_token')
  if (!token) throw new Error('No authentication token')

  const response = await authClient.post(
    '/api/auth/change-password',
    {
      current_password: currentPassword,
      new_password: newPassword
    },
    {
      headers: {
        Authorization: `Bearer ${token}`
      }
    }
  )

  return response.data
}

// Admin endpoints

/**
 * Register new user (admin only)
 * @param {Object} userData - User registration data
 * @returns {Promise} Created user
 */
export const registerUser = async userData => {
  const token = localStorage.getItem('access_token')
  if (!token) throw new Error('No authentication token')

  const response = await authClient.post('/api/auth/register', userData, {
    headers: {
      Authorization: `Bearer ${token}`
    }
  })

  return response.data
}

/**
 * Get all users (admin only)
 * @returns {Promise} List of users
 */
export const getAllUsers = async () => {
  const token = localStorage.getItem('access_token')
  if (!token) throw new Error('No authentication token')

  const response = await authClient.get('/api/auth/users', {
    headers: {
      Authorization: `Bearer ${token}`
    }
  })

  return response.data
}

/**
 * Update user (admin only)
 * @param {number} userId - User ID
 * @param {Object} updates - User updates
 * @returns {Promise} Updated user
 */
export const updateUser = async (userId, updates) => {
  const token = localStorage.getItem('access_token')
  if (!token) throw new Error('No authentication token')

  const response = await authClient.put(`/api/auth/users/${userId}`, updates, {
    headers: {
      Authorization: `Bearer ${token}`
    }
  })

  return response.data
}

/**
 * Delete user (admin only)
 * @param {number} userId - User ID
 * @returns {Promise}
 */
export const deleteUser = async userId => {
  const token = localStorage.getItem('access_token')
  if (!token) throw new Error('No authentication token')

  const response = await authClient.delete(`/api/auth/users/${userId}`, {
    headers: {
      Authorization: `Bearer ${token}`
    }
  })

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
