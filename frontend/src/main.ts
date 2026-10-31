import './assets/main.css'
import { ViteSSG } from 'vite-ssg'
import { createPinia } from 'pinia'
import App from './App.vue'
import { routes } from './router'

export const createApp = ViteSSG(
  App,
  {
    routes,
    base: import.meta.env.BASE_URL,
    // Honour #hash links across routes (e.g. /faq -> /about#faq); 80px clears the sticky header
    scrollBehavior: (to, _from, saved) => saved ?? (to.hash ? { el: to.hash, top: 80 } : undefined)
  },
  async ({ app, router }) => {
    // vite-ssg (28.3.0, latest) registers its state guard with the deprecated next() callback
    // right after this hook, which logs VUE_ROUTER_R0025 on every navigation. Adapt such
    // guards to the return style: next(x) resolves the guard's result with x.
    const beforeEach = router!.beforeEach
    router!.beforeEach = guard =>
      beforeEach(
        guard.length > 2
          ? (to, from) => new Promise(resolve => guard.call(undefined, to, from, resolve as never))
          : guard
      )

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
        if (to.meta.requiresAuth || to.meta.requiresAdmin || to.meta.requiresCurator) {
          await authStore.initReady
        }

        if (to.meta.requiresAuth && !authStore.isAuthenticated) {
          return '/login?redirect=' + to.fullPath
        } else if (to.meta.requiresAdmin && !authStore.isAdmin) {
          return '/'
        } else if (to.meta.requiresCurator && !authStore.isCurator) {
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

      // Start auth before the first navigation: guards await initReady and
      // vite-ssg awaits router.isReady() before mounting, so App cannot do it.
      void useAuthStore().initialize()

      logService.info('Kidney Genetics Database application starting', {
        timestamp: new Date().toISOString(),
        environment: import.meta.env.MODE,
        userAgent: navigator.userAgent,
        url: window.location.href
      })

      // Route Vue warnings through our logging system (visible in the Log Viewer)
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
