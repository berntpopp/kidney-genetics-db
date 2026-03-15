// Runtime configuration from window._env_ (injected at container startup)
// Falls back to Vite environment variables for local development

/** Application runtime configuration */
export interface AppConfig {
  apiBaseUrl: string
  wsUrl: string
  environment: string
  version: string
}

// Guard window access for SSR/SSG compatibility
const env =
  typeof window !== 'undefined'
    ? ((window as Record<string, unknown>)._env_ as Record<string, string> | undefined)
    : undefined

export const config: AppConfig = {
  // Dev: VITE_API_BASE_URL=http://localhost:8000 (cross-origin)
  // Docker/prod: window._env_.API_BASE_URL="" (same-origin, nginx proxies /api/)
  // Fallback: empty string (same-origin)
  apiBaseUrl: env?.API_BASE_URL ?? import.meta.env.VITE_API_BASE_URL ?? '',
  wsUrl: env?.WS_URL ?? import.meta.env.VITE_WS_URL ?? '/ws',
  environment: env?.ENVIRONMENT ?? import.meta.env.MODE ?? 'development',
  version: env?.VERSION ?? '0.2.0'
}

// Log configuration in development mode for debugging
if (typeof window !== 'undefined' && config.environment === 'development') {
  window.logService?.info('Runtime configuration:', config)
}
