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

// Continue with other plugins
app.use(router)
app.use(vuetify)

// Mount application
app.mount('#app')
