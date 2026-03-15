import './assets/main.css'
import { ViteSSG } from 'vite-ssg'
import { createPinia } from 'pinia'
import App from './App.vue'
import { routes } from './router'

// Intercept console.warn to catch Vue Router warnings from vite-ssg internals
// and route them through our logging system instead of polluting the console.
// vite-ssg v28.3.0 uses the deprecated next() callback pattern internally.
if (typeof window !== 'undefined') {
  const origWarn = console.warn
  console.warn = (...args: unknown[]) => {
    const msg = typeof args[0] === 'string' ? args[0] : ''
    if (msg.includes('[Vue Router warn]')) {
      // Route to our logging system once available, suppress from console
      window.logService?.warn(msg)
      return
    }
    origWarn.apply(console, args)
  }
}

export const createApp = ViteSSG(
  App,
  {
    routes,
    base: import.meta.env.BASE_URL
  },
  async ({ app, router }) => {
    // Create and install Pinia (vite-ssg does NOT do this automatically)
    const pinia = createPinia()
    app.use(pinia)

    if (!import.meta.env.SSR) {
      // Navigation guards (client-only — SSG doesn't need auth)
      const { useAuthStore } = await import('./stores/auth')

      router!.beforeEach(async to => {
        const authStore = useAuthStore()

        // Wait for the silent token refresh to complete before evaluating guards.
        // This prevents redirecting to /login on page refresh while the HttpOnly
        // cookie refresh is still in-flight.
        if (to.meta.requiresAuth || to.meta.requiresAdmin) {
          await authStore.initReady
        }

        if (to.meta.requiresAuth && !authStore.isAuthenticated) {
          return '/login?redirect=' + to.fullPath
        } else if (to.meta.requiresAdmin && !authStore.isAdmin) {
          return '/'
        }
      })

      // Browser-only initialization
      const { logService } = await import('./services/logService')
      const { useLogStore } = await import('./stores/logStore')
      const { toast } = await import('vue-sonner')

      const logStore = useLogStore()
      logService.initStore(logStore)

      app.config.globalProperties['$log'] = logService
      window.logService = logService

      logService.info('Kidney Genetics Database application starting', {
        timestamp: new Date().toISOString(),
        environment: import.meta.env.MODE,
        userAgent: navigator.userAgent,
        url: window.location.href
      })

      // Catch Vue warnings and route them through our logging system
      // instead of console.warn — this captures the vite-ssg next() deprecation
      // warning and any other Vue warnings in the Log Viewer
      app.config.warnHandler = (msg, _instance, trace) => {
        logService.warn(`[Vue warn]: ${msg}`, { trace })
      }

      window.snackbar = {
        success: (msg: string) => toast.success(msg, { duration: 5000 }),
        error: (msg: string) => toast.error(msg, { duration: Infinity })
      }

      app.config.errorHandler = (err, instance, info) => {
        const ls = window.logService
        if (ls) {
          ls.error('Unhandled Vue error', {
            error: err instanceof Error ? err.message : String(err),
            stack: err instanceof Error ? err.stack : undefined,
            info,
            component:
              (instance as { $options?: { name?: string } } | null)?.$options?.name || 'unknown'
          })
        }
      }

      // Handle chunk load failures and other navigation errors
      router!.onError((error, to) => {
        if (error.message.includes('Failed to fetch dynamically imported module')) {
          window.location.href = to.fullPath
        } else {
          window.logService?.error('Navigation error', {
            error: error.message,
            stack: error.stack,
            route: to.fullPath
          })
        }
      })

      window.addEventListener('unhandledrejection', event => {
        const ls = window.logService
        if (ls) {
          ls.error('Unhandled promise rejection', {
            reason:
              event.reason instanceof Error
                ? { message: event.reason.message, stack: event.reason.stack }
                : String(event.reason)
          })
        }
      })

      logService.info('Application mounted successfully')
    }
  }
)
