/**
 * Version management utilities
 *
 * Provides centralized access to version information for all components.
 * Frontend version is injected by Vite from package.json.
 * Backend and database versions are fetched from the /version API endpoint.
 */

import api from '@/api/client'

/** Frontend version info */
export interface FrontendVersionInfo {
  version: string
  name: string
  type: string
}

/** Complete version response from API + frontend */
export interface AllVersionsResult {
  frontend: FrontendVersionInfo
  backend?: { version: string; [key: string]: unknown }
  database?: { version: string; [key: string]: unknown }
  environment?: string
  timestamp?: string
  [key: string]: unknown
}

/**
 * Get frontend version (injected by Vite at build time)
 * @returns Frontend version (e.g., "0.1.0")
 */
export function getFrontendVersion(): string {
  return __APP_VERSION__ // Injected by Vite via define in vite.config.ts
}

/**
 * Get version information for all components
 *
 * Fetches backend and database versions from the API and combines them
 * with the frontend version.
 *
 * @returns Version information for all components
 * @example
 * const versions = await getAllVersions()
 * // {
 * //   frontend: { version: "0.1.0", name: "kidney-genetics-db-frontend", type: "Vue.js" },
 * //   backend: { version: "0.1.0", name: "kidney-genetics-db", type: "FastAPI" },
 * //   database: { version: "0.1.0", alembic_revision: "...", ... },
 * //   environment: "development",
 * //   timestamp: "2025-10-10T12:00:00Z"
 * // }
 */
export async function getAllVersions(): Promise<AllVersionsResult> {
  try {
    const response = await api.get('/version')

    return {
      ...(response.data as Record<string, unknown>),
      frontend: {
        version: getFrontendVersion(),
        name: 'kidney-genetics-db-frontend',
        type: 'Vue.js'
      }
    }
  } catch (error) {
    console.error('Failed to fetch versions:', error)

    // Return partial data with frontend version on error
    return {
      frontend: {
        version: getFrontendVersion(),
        name: 'kidney-genetics-db-frontend',
        type: 'Vue.js'
      },
      backend: { version: 'unknown' },
      database: { version: 'unknown' },
      environment: 'unknown',
      timestamp: new Date().toISOString()
    }
  }
}
