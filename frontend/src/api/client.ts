/**
 * Axios API client configuration
 *
 * Uses config.ts as single source of truth for API base URL.
 * - Dev (Vite): VITE_API_BASE_URL=http://localhost:8000
 * - Docker/prod: window._env_.API_BASE_URL="" (same-origin, nginx proxies /api/)
 */

import axios from 'axios'
import type { AxiosInstance, InternalAxiosRequestConfig, AxiosError } from 'axios'
import { config } from '@/config'

// Augment Axios to support _retry flag on request config
declare module 'axios' {
  interface InternalAxiosRequestConfig {
    _retry?: boolean
  }
}

/** Response from token refresh endpoint */
interface TokenRefreshResponse {
  access_token: string
  token_type?: string
}

const API_BASE_URL = config.apiBaseUrl

// Module-level token storage (avoids circular dependency with auth store)
let _accessToken: string | null = null

/** Set the current access token (called by auth store) */
export function setClientAccessToken(token: string | null): void {
  _accessToken = token
}

/** Get the current access token */
export function getClientAccessToken(): string | null {
  return _accessToken
}

const apiClient: AxiosInstance = axios.create({
  baseURL: API_BASE_URL,
  headers: {
    'Content-Type': 'application/json'
  },
  withCredentials: true
})

// Request interceptor for auth
apiClient.interceptors.request.use(
  (config: InternalAxiosRequestConfig) => {
    if (_accessToken) {
      config.headers.Authorization = `Bearer ${_accessToken}`
    }
    // Add CSRF header for all requests
    config.headers['X-Requested-With'] = 'XMLHttpRequest'
    return config
  },
  (error: AxiosError) => Promise.reject(error)
)

// Response interceptor for error handling and token refresh
apiClient.interceptors.response.use(
  response => response,
  async (error: AxiosError) => {
    const originalRequest = error.config as InternalAxiosRequestConfig

    // If 401, try to refresh via HttpOnly cookie
    if (error.response?.status === 401 && originalRequest && !originalRequest._retry) {
      originalRequest._retry = true

      try {
        // Cookie is sent automatically with withCredentials
        const response = await axios.post(
          `${API_BASE_URL}/api/auth/refresh`,
          {},
          {
            withCredentials: true,
            headers: { 'X-Requested-With': 'XMLHttpRequest' }
          }
        )

        const tokenData: TokenRefreshResponse = response.data
        const { access_token } = tokenData

        // Update module-level token
        _accessToken = access_token

        // Retry original request with new token
        originalRequest.headers.Authorization = `Bearer ${access_token}`
        return apiClient(originalRequest)
      } catch {
        // Refresh failed — dispatch logout
        _accessToken = null
        localStorage.removeItem('user')
        window.dispatchEvent(new CustomEvent('auth:logout'))
      }
    }

    return Promise.reject(error)
  }
)

export default apiClient
