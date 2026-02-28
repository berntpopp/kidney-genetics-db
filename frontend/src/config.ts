// Runtime configuration from window._env_ (injected at container startup)
// Falls back to Vite environment variables for local development

/** Application runtime configuration */
export interface AppConfig {
  apiBaseUrl: string
  wsUrl: string
  environment: string
  version: string
}

export const config: AppConfig = {
  // Dev: VITE_API_BASE_URL=http://localhost:8000 (cross-origin)
  // Docker/prod: window._env_.API_BASE_URL="" (same-origin, nginx proxies /api/)
  // Fallback: empty string (same-origin)
  apiBaseUrl: window._env_?.API_BASE_URL ?? import.meta.env.VITE_API_BASE_URL ?? '',
  wsUrl: window._env_?.WS_URL ?? import.meta.env.VITE_WS_URL ?? '/ws',
  environment: window._env_?.ENVIRONMENT ?? import.meta.env.MODE ?? 'development',
  version: window._env_?.VERSION ?? '0.2.0'
}

// Log configuration in development mode for debugging
if (config.environment === 'development') {
  console.log('Runtime configuration:', config)
}
