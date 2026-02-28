/// <reference types="vite/client" />

declare module '*.vue' {
  import type { DefineComponent } from 'vue'
  const component: DefineComponent<Record<string, unknown>, Record<string, unknown>, unknown>
  export default component
}

interface ImportMetaEnv {
  readonly VITE_API_BASE_URL?: string
  readonly VITE_API_URL?: string
  readonly VITE_WS_URL?: string
  readonly MODE: string
  readonly DEV: boolean
  readonly PROD: boolean
}

interface ImportMeta {
  readonly env: ImportMetaEnv
}

declare const __APP_VERSION__: string

/**
 * Minimal public API of window.logService.
 * Will be refined once logService.js is migrated to TypeScript in Plan 02.
 */
interface WindowLogService {
  debug(message: string, data?: unknown): void
  info(message: string, data?: unknown): void
  warn(message: string, data?: unknown): void
  error(message: string, data?: unknown): void
  critical(message: string, data?: unknown): void
  logPerformance(operation: string, duration: number, data?: unknown): void
  logApiCall(
    method: string,
    url: string,
    status: number,
    duration: number,
    data?: unknown
  ): void
  initStore(store: unknown): void
  setCorrelationId(id: string): void
  clearCorrelationId(): void
  setMetadata(metadata: Record<string, unknown>): void
  clearMetadata(): void
  setConsoleEcho(enabled: boolean): void
  setMaxEntries(max: number): void
  setMinLogLevel(level: string): void
  clearLogs(): void
  exportLogs(): string
}

interface Window {
  logService: WindowLogService
  _env_?: {
    API_BASE_URL?: string
    WS_URL?: string
    ENVIRONMENT?: string
    VERSION?: string
  }
  snackbar?: {
    success(msg: string, opts?: Record<string, unknown>): void
    error(msg: string, opts?: Record<string, unknown>): void
  }
}
