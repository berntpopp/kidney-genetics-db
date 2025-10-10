<template>
  <v-app>
    <!-- Navigation Bar -->
    <v-app-bar
      app
      elevation="0"
      class="border-b"
      :class="{ 'bg-surface': !isDark, 'bg-surface-bright': isDark }"
    >
      <v-container class="py-0">
        <v-row align="center" justify="space-between" class="py-0 ma-0">
          <v-col cols="auto" class="d-flex align-center py-0">
            <!-- Brand Logo (consistent everywhere) -->
            <KGDBLogo
              :size="40"
              variant="with-text"
              text-layout="horizontal"
              :animated="false"
              :interactive="true"
              @click="$router.push('/')"
            />
          </v-col>

          <v-spacer class="d-none d-md-flex" />

          <!-- Navigation Links -->
          <v-col cols="auto" class="d-none d-md-flex align-center ga-1 py-0">
            <v-btn
              :to="'/genes'"
              variant="text"
              :color="$route.path.startsWith('/genes') ? 'primary' : ''"
              class="text-none"
              size="default"
            >
              <v-icon icon="mdi-dna" size="small" class="mr-1" />
              Gene Browser
            </v-btn>
            <v-btn
              :to="'/dashboard'"
              variant="text"
              :color="$route.path === '/dashboard' ? 'primary' : ''"
              class="text-none"
              size="default"
            >
              <v-icon icon="mdi-view-dashboard" size="small" class="mr-1" />
              Data Overview
            </v-btn>
            <v-btn
              :to="'/network-analysis'"
              variant="text"
              :color="$route.path === '/network-analysis' ? 'primary' : ''"
              class="text-none"
              size="default"
            >
              <v-icon icon="mdi-chart-scatter-plot" size="small" class="mr-1" />
              Network Analysis
            </v-btn>
            <v-btn
              :to="'/data-sources'"
              variant="text"
              :color="$route.path === '/data-sources' ? 'primary' : ''"
              class="text-none"
              size="default"
            >
              <v-icon icon="mdi-database-sync" size="small" class="mr-1" />
              Data Sources
            </v-btn>
            <v-btn
              :to="'/about'"
              variant="text"
              :color="$route.path === '/about' ? 'primary' : ''"
              class="text-none"
              size="default"
            >
              <v-icon icon="mdi-information" size="small" class="mr-1" />
              About
            </v-btn>
          </v-col>

          <!-- Desktop Auth Controls -->
          <v-col cols="auto" class="d-none d-md-flex align-center ga-2 py-0">
            <!-- User Menu for authenticated users -->
            <UserMenu v-if="authStore.isAuthenticated" />

            <!-- Login button for unauthenticated users -->
            <v-btn v-else :to="'/login'" color="primary" size="default" variant="tonal">
              <v-icon start>mdi-login</v-icon>
              Login
            </v-btn>

            <!-- Theme Toggle -->
            <v-btn
              icon
              size="default"
              :title="isDark ? 'Switch to light mode' : 'Switch to dark mode'"
              @click="toggleTheme"
            >
              <v-icon :icon="isDark ? 'mdi-weather-sunny' : 'mdi-weather-night'" />
            </v-btn>
          </v-col>

          <!-- Mobile Menu Button -->
          <v-col cols="auto" class="d-md-none py-0">
            <v-app-bar-nav-icon @click="drawer = !drawer" />
          </v-col>
        </v-row>
      </v-container>
    </v-app-bar>

    <!-- Mobile Navigation Drawer -->
    <v-navigation-drawer v-model="drawer" temporary location="right">
      <!-- User Section for authenticated users -->
      <template v-if="authStore.isAuthenticated">
        <v-list density="comfortable">
          <v-list-item>
            <template #prepend>
              <v-avatar color="primary" size="40">
                <v-icon>mdi-account</v-icon>
              </v-avatar>
            </template>
            <v-list-item-title class="font-weight-medium">
              {{ authStore.user?.username }}
            </v-list-item-title>
            <v-list-item-subtitle>
              {{ authStore.user?.email }}
            </v-list-item-subtitle>
          </v-list-item>
        </v-list>
        <v-divider />
        <v-list density="comfortable" nav>
          <v-list-item prepend-icon="mdi-account-circle" title="My Profile" :to="'/profile'" />
          <v-list-item
            v-if="authStore.isAdmin"
            prepend-icon="mdi-shield-crown"
            title="Admin Panel"
            :to="'/admin'"
          />
          <v-list-item prepend-icon="mdi-logout" title="Logout" @click="handleLogout" />
        </v-list>
        <v-divider />
      </template>

      <!-- Login prompt for unauthenticated users -->
      <template v-else>
        <v-list density="comfortable">
          <v-list-item prepend-icon="mdi-login" title="Login" :to="'/login'" />
        </v-list>
        <v-divider />
      </template>

      <!-- Navigation Links -->
      <v-list density="comfortable" nav>
        <v-list-item
          prepend-icon="mdi-dna"
          title="Gene Browser"
          :to="'/genes'"
          :active="$route.path.startsWith('/genes')"
        />
        <v-list-item
          prepend-icon="mdi-view-dashboard"
          title="Data Overview"
          :to="'/dashboard'"
          :active="$route.path === '/dashboard'"
        />
        <v-list-item
          prepend-icon="mdi-chart-scatter-plot"
          title="Network Analysis"
          :to="'/network-analysis'"
          :active="$route.path === '/network-analysis'"
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
      </v-list>

      <!-- Theme Toggle at Bottom -->
      <template #append>
        <v-list density="comfortable">
          <v-list-item
            :prepend-icon="isDark ? 'mdi-weather-sunny' : 'mdi-weather-night'"
            :title="isDark ? 'Light Mode' : 'Dark Mode'"
            @click="toggleTheme"
          />
        </v-list>
      </template>
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

    <!-- Footer with Version Information -->
    <AppFooter />
  </v-app>
</template>

<script setup>
import { ref, computed, onMounted, onUnmounted } from 'vue'
import { useTheme } from 'vuetify'
// import { useRoute } from 'vue-router' // Removed unused import
import { KGDBLogo } from '@/components/branding'
import UserMenu from '@/components/auth/UserMenu.vue'
import LogViewer from '@/components/admin/LogViewer.vue'
import AppFooter from '@/components/AppFooter.vue'
import { useAuthStore } from '@/stores/auth'
import { useLogStore } from '@/stores/logStore'

const theme = useTheme()
// const route = useRoute() // Removed unused variable
const drawer = ref(false)
const authStore = useAuthStore()
const logStore = useLogStore()

const handleLogout = async () => {
  drawer.value = false
  await authStore.logout()
}

const isDark = computed(() => theme.global.current.value.dark)

const toggleTheme = () => {
  theme.change(isDark.value ? 'light' : 'dark')
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
