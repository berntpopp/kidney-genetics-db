import { createApp } from 'vue'
import { createPinia } from 'pinia'
import App from './App.vue'
import router from './router'
import vuetify from './plugins/vuetify'

// Import logging system
import { logService } from './services/logService'
import { useLogStore } from './stores/logStore'

const app = createApp(App)
const pinia = createPinia()

// Initialize Pinia first (required for stores)
app.use(pinia)

// Initialize logging system after Pinia is available
const logStore = useLogStore()
logService.initStore(logStore)

// Make logService globally available
app.config.globalProperties.$log = logService
// Also make it available on window for non-component code
window.logService = logService

// Log application startup
logService.info('Kidney Genetics Database application starting', {
  timestamp: new Date().toISOString(),
  environment: import.meta.env.MODE,
  userAgent: navigator.userAgent,
  url: window.location.href
})

// Continue with other plugins
app.use(router)
app.use(vuetify)

// Mount application
app.mount('#app')

// Log successful mount
logService.info('Application mounted successfully')
