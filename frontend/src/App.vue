<template>
  <v-app>
    <!-- Navigation Bar -->
    <v-app-bar
      app
      elevation="0"
      class="border-b"
      :class="{ 'bg-surface': !isDark, 'bg-surface-bright': isDark }"
    >
      <!-- Logo and Title -->
      <div class="d-flex align-center">
        <KidneyGeneticsLogo
          :size="40"
          variant="kidneys"
          :animated="false"
          interactive
          class="mr-3 cursor-pointer"
          @click="$router.push('/')"
        />
        <v-app-bar-title class="text-h6 font-weight-medium">
          Kidney Genetics Database
        </v-app-bar-title>
      </div>

      <v-spacer />

      <!-- Navigation Links -->
      <div class="d-none d-md-flex align-center ga-2">
        <v-btn
          :to="'/'"
          variant="text"
          :color="$route.path === '/' ? 'primary' : ''"
          class="text-none"
        >
          <v-icon icon="mdi-home" size="small" class="mr-1" />
          Home
        </v-btn>
        <v-btn
          :to="'/genes'"
          variant="text"
          :color="$route.path.startsWith('/genes') ? 'primary' : ''"
          class="text-none"
        >
          <v-icon icon="mdi-dna" size="small" class="mr-1" />
          Gene Browser
        </v-btn>
        <v-btn
          :to="'/dashboard'"
          variant="text"
          :color="$route.path === '/dashboard' ? 'primary' : ''"
          class="text-none"
        >
          <v-icon icon="mdi-view-dashboard" size="small" class="mr-1" />
          Dashboard
        </v-btn>
        <v-btn
          :to="'/data-sources'"
          variant="text"
          :color="$route.path === '/data-sources' ? 'primary' : ''"
          class="text-none"
        >
          <v-icon icon="mdi-database-sync" size="small" class="mr-1" />
          Data Sources
        </v-btn>
        <v-btn
          :to="'/about'"
          variant="text"
          :color="$route.path === '/about' ? 'primary' : ''"
          class="text-none"
        >
          <v-icon icon="mdi-information" size="small" class="mr-1" />
          About
        </v-btn>
      </div>

      <!-- Auth Controls -->
      <div class="d-flex align-center ga-2">
        <!-- User Menu for authenticated users -->
        <UserMenu v-if="authStore.isAuthenticated" />

        <!-- Login button for unauthenticated users -->
        <v-btn v-else :to="'/login'" color="primary" size="small" variant="tonal">
          <v-icon start>mdi-login</v-icon>
          Login
        </v-btn>

        <!-- Theme Toggle -->
        <v-btn
          icon
          class="ml-2"
          :title="isDark ? 'Switch to light mode' : 'Switch to dark mode'"
          @click="toggleTheme"
        >
          <v-icon :icon="isDark ? 'mdi-weather-sunny' : 'mdi-weather-night'" />
        </v-btn>
      </div>

      <!-- Mobile Menu -->
      <v-app-bar-nav-icon class="d-md-none" @click="drawer = !drawer" />
    </v-app-bar>

    <!-- Mobile Navigation Drawer -->
    <v-navigation-drawer v-model="drawer" temporary location="right">
      <v-list density="comfortable" nav>
        <v-list-item prepend-icon="mdi-home" title="Home" :to="'/'" :active="$route.path === '/'" />
        <v-list-item
          prepend-icon="mdi-dna"
          title="Gene Browser"
          :to="'/genes'"
          :active="$route.path.startsWith('/genes')"
        />
        <v-list-item
          prepend-icon="mdi-view-dashboard"
          title="Dashboard"
          :to="'/dashboard'"
          :active="$route.path === '/dashboard'"
        />
        <v-list-item
          prepend-icon="mdi-database-sync"
          title="Data Sources"
          :to="'/data-sources'"
          :active="$route.path === '/data-sources'"
        />
        <v-list-item
          prepend-icon="mdi-information"
          title="About"
          :to="'/about'"
          :active="$route.path === '/about'"
        />
        <v-divider class="my-2" />
        <v-list-item
          prepend-icon="mdi-text-box-search-outline"
          title="Log Viewer"
          @click="logStore.showViewer"
        >
          <template v-if="logStore.errorCount > 0" #append>
            <v-chip color="error" size="x-small">{{ logStore.errorCount }}</v-chip>
          </template>
        </v-list-item>
      </v-list>
    </v-navigation-drawer>

    <!-- Main Content -->
    <v-main class="bg-background">
      <router-view v-slot="{ Component }">
        <transition name="fade" mode="out-in">
          <component :is="Component" />
        </transition>
      </router-view>
    </v-main>

    <!-- Log Viewer Component -->
    <LogViewer />

    <!-- Footer -->
    <v-footer app class="bg-surface-light" height="auto">
      <v-container>
        <v-row align="center" justify="center">
          <v-col cols="12" md="4" class="text-center text-md-left">
            <div class="d-flex align-center justify-center justify-md-start">
              <KidneyGeneticsLogo
                :size="32"
                variant="kidneys"
                :animated="false"
                monochrome
                class="mr-2 opacity-60"
              />
              <span class="text-body-2 text-medium-emphasis">
                © {{ new Date().getFullYear() }} Kidney Genetics Database
              </span>
            </div>
          </v-col>
          <v-col cols="12" md="4" class="text-center">
            <div class="text-caption text-medium-emphasis">
              Advancing nephrology through genomic research
            </div>
          </v-col>
          <v-col cols="12" md="4" class="text-center text-md-right">
            <v-btn
              icon="mdi-github"
              size="small"
              variant="text"
              href="https://github.com"
              target="_blank"
              title="GitHub"
            />
            <v-btn
              icon="mdi-file-document"
              size="small"
              variant="text"
              to="/about"
              title="Documentation"
            />
            <v-btn
              size="small"
              variant="text"
              :title="`Open Log Viewer (Ctrl+Shift+L) - ${logStore.errorCount} errors`"
              @click="logStore.showViewer"
            >
              <v-badge
                :content="logStore.errorCount"
                :model-value="logStore.errorCount > 0"
                color="error"
                dot
              >
                <v-icon>mdi-text-box-search-outline</v-icon>
              </v-badge>
            </v-btn>
          </v-col>
        </v-row>
      </v-container>
    </v-footer>
  </v-app>
</template>

<script setup>
import { ref, computed, onMounted, onUnmounted } from 'vue'
import { useTheme } from 'vuetify'
// import { useRoute } from 'vue-router' // Removed unused import
import KidneyGeneticsLogo from '@/components/KidneyGeneticsLogo.vue'
import UserMenu from '@/components/auth/UserMenu.vue'
import LogViewer from '@/components/admin/LogViewer.vue'
import { useAuthStore } from '@/stores/auth'
import { useLogStore } from '@/stores/logStore'

const theme = useTheme()
// const route = useRoute() // Removed unused variable
const drawer = ref(false)
const authStore = useAuthStore()
const logStore = useLogStore()

const isDark = computed(() => theme.global.current.value.dark)

const toggleTheme = () => {
  theme.global.name.value = isDark.value ? 'light' : 'dark'
}

// Keyboard shortcut for log viewer (Ctrl+Shift+L)
const handleKeyPress = event => {
  if (event.ctrlKey && event.shiftKey && event.key === 'L') {
    event.preventDefault()
    logStore.toggleViewer()
  }
}

// Initialize auth store on app mount
onMounted(() => {
  authStore.initialize()
  // Add keyboard listener for log viewer
  window.addEventListener('keydown', handleKeyPress)
})

onUnmounted(() => {
  // Clean up keyboard listener
  window.removeEventListener('keydown', handleKeyPress)
})
</script>

<style scoped>
.border-b {
  border-bottom: 1px solid rgb(var(--v-theme-surface-variant));
}

.cursor-pointer {
  cursor: pointer;
}

.opacity-60 {
  opacity: 0.6;
}

/* Page transition */
.fade-enter-active,
.fade-leave-active {
  transition: opacity 0.2s ease;
}

.fade-enter-from,
.fade-leave-to {
  opacity: 0;
}
</style>
