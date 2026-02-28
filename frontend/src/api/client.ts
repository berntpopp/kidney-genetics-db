/**
 * Axios API client configuration
 */

import axios from 'axios'
import type { AxiosInstance, InternalAxiosRequestConfig, AxiosError } from 'axios'

// Augment Axios to support _retry flag on request config
declare module 'axios' {
  interface InternalAxiosRequestConfig {
    _retry?: boolean
  }
}

const API_BASE_URL =
  window._env_?.API_BASE_URL || import.meta.env.VITE_API_URL || 'http://localhost:8000'

const apiClient: AxiosInstance = axios.create({
  baseURL: API_BASE_URL,
  headers: {
    'Content-Type': 'application/json'
  }
})

// Request interceptor for auth
apiClient.interceptors.request.use(
  (config: InternalAxiosRequestConfig) => {
    // Add auth token if available (only for protected endpoints)
    const token = localStorage.getItem('access_token')
    if (token) {
      config.headers.Authorization = `Bearer ${token}`
    }
    return config
  },
  (error: AxiosError) => Promise.reject(error)
)

// Response interceptor for error handling and token refresh
apiClient.interceptors.response.use(
  response => response,
  async (error: AxiosError) => {
    const originalRequest = error.config as InternalAxiosRequestConfig

    // If 401 and we have a refresh token, try to refresh
    if (error.response?.status === 401 && originalRequest && !originalRequest._retry) {
      originalRequest._retry = true

      const refreshToken = localStorage.getItem('refresh_token')
      if (refreshToken) {
        try {
          const response = await axios.post(`${API_BASE_URL}/api/auth/refresh`, {
            refresh_token: refreshToken
          })

          const { access_token } = (response.data as { access_token: string; refresh_token?: string })
          localStorage.setItem('access_token', access_token)

          // Retry original request with new token
          originalRequest.headers.Authorization = `Bearer ${access_token}`
          return apiClient(originalRequest)
        } catch {
          // Refresh failed, clear tokens and redirect to login
          localStorage.removeItem('access_token')
          localStorage.removeItem('refresh_token')
          localStorage.removeItem('user')

          // Dispatch event for auth store to handle
          window.dispatchEvent(new CustomEvent('auth:logout'))
        }
      }
    }

    return Promise.reject(error)
  }
)

export default apiClient
