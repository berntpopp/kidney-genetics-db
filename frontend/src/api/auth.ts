/**
 * Authentication API endpoints
 */

import apiClient from './client'
import type { User } from '@/types/auth'

/** Response from login endpoint */
export interface LoginResponse {
  access_token: string
  refresh_token: string
  token_type: string
  user?: User
}

/** Response from token refresh endpoint */
export interface RefreshResponse {
  access_token: string
  token_type: string
}

/**
 * Login with username/email and password
 */
export const login = async (username: string, password: string): Promise<LoginResponse> => {
  // Use URLSearchParams for OAuth2 password flow
  const formData = new URLSearchParams()
  formData.append('username', username)
  formData.append('password', password)
  formData.append('grant_type', 'password')

  const response = await apiClient.post<LoginResponse>('/api/auth/login', formData, {
    headers: {
      'Content-Type': 'application/x-www-form-urlencoded'
    }
  })

  return response.data
}

/**
 * Logout current user
 */
export const logout = async (): Promise<void> => {
  try {
    await apiClient.post('/api/auth/logout', {})
  } catch (error) {
    // Logout anyway even if request fails
    window.logService.error('Logout request failed:', error)
  }
}

/**
 * Get current user information
 */
export const getCurrentUser = async (): Promise<User> => {
  const response = await apiClient.get<User>('/api/auth/me')

  return response.data
}

/**
 * Refresh access token
 */
export const refreshToken = async (token: string): Promise<RefreshResponse> => {
  const response = await apiClient.post<RefreshResponse>('/api/auth/refresh', {
    refresh_token: token
  })

  return response.data
}

/**
 * Request password reset
 */
export const requestPasswordReset = async (email: string): Promise<{ detail: string }> => {
  const response = await apiClient.post<{ detail: string }>('/api/auth/forgot-password', {
    email
  })

  return response.data
}

/**
 * Reset password with token
 */
export const resetPassword = async (token: string, newPassword: string): Promise<{ detail: string }> => {
  const response = await apiClient.post<{ detail: string }>('/api/auth/reset-password', {
    token,
    new_password: newPassword
  })

  return response.data
}

/**
 * Change password for current user
 */
export const changePassword = async (currentPassword: string, newPassword: string): Promise<{ detail: string }> => {
  const response = await apiClient.post<{ detail: string }>('/api/auth/change-password', {
    current_password: currentPassword,
    new_password: newPassword
  })

  return response.data
}

// Admin endpoints

/**
 * Register new user (admin only)
 */
export const registerUser = async (userData: Record<string, unknown>): Promise<User> => {
  const response = await apiClient.post<User>('/api/auth/register', userData)

  return response.data
}

/**
 * Get all users (admin only)
 */
export const getAllUsers = async (): Promise<User[]> => {
  const response = await apiClient.get<User[]>('/api/auth/users')

  return response.data
}

/**
 * Update user (admin only)
 */
export const updateUser = async (userId: number, updates: Partial<User>): Promise<User> => {
  const response = await apiClient.put<User>(`/api/auth/users/${userId}`, updates)

  return response.data
}

/**
 * Delete user (admin only)
 */
export const deleteUser = async (userId: number): Promise<{ detail: string }> => {
  const response = await apiClient.delete<{ detail: string }>(`/api/auth/users/${userId}`)

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
