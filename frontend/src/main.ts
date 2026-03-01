import './assets/main.css'
import { createApp } from 'vue'
import { createPinia } from 'pinia'
import { createHead } from '@unhead/vue/client'
import App from './App.vue'
import router from './router'

// Import logging system
import { logService } from './services/logService'
import { useLogStore } from './stores/logStore'

const app = createApp(App)
const pinia = createPinia()

// Initialize Pinia first (required for stores)
app.use(pinia)

// Initialize @unhead/vue for SEO meta management
const head = createHead()
app.use(head)

// Initialize logging system after Pinia is available
const logStore = useLogStore()
logService.initStore(logStore)

// Make logService globally available
app.config.globalProperties['$log'] = logService
// Also make it available on window for non-component code
window.logService = logService

// Log application startup
logService.info('Kidney Genetics Database application starting', {
  timestamp: new Date().toISOString(),
  environment: import.meta.env.MODE,
  userAgent: navigator.userAgent,
  url: window.location.href
})

// Bridge window.snackbar to vue-sonner toast
import { toast } from 'vue-sonner'

window.snackbar = {
  success: (msg: string) => toast.success(msg, { duration: 5000 }),
  error: (msg: string) => toast.error(msg, { duration: Infinity })
}

// Continue with other plugins
app.use(router)

// Mount application
app.mount('#app')

// Log successful mount
logService.info('Application mounted successfully')
