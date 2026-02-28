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

interface Window {
  /** Global logging service — singleton instance of LogService from @/services/logService */
  logService: import('@/services/logService').LogService
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
