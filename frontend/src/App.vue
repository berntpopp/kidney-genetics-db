<script setup lang="ts">
import { onMounted, onUnmounted } from 'vue'
import AppHeader from '@/layouts/AppHeader.vue'
import AppFooter from '@/layouts/AppFooter.vue'
import LogViewer from '@/components/admin/LogViewer.vue'
import { Toaster } from '@/components/ui/sonner'
import { useAuthStore } from '@/stores/auth'
import { useLogStore } from '@/stores/logStore'
import { useAppTheme } from '@/composables/useAppTheme'

const authStore = useAuthStore()
const logStore = useLogStore()

// Initialize dark mode bidirectional sync
useAppTheme()

// Keyboard shortcut for log viewer (Ctrl+Shift+L)
const handleKeyPress = (event: KeyboardEvent) => {
  if (event.ctrlKey && event.shiftKey && event.key === 'L') {
    event.preventDefault()
    logStore.toggleViewer()
  }
}

onMounted(() => {
  authStore.initialize()
  window.addEventListener('keydown', handleKeyPress)
})

onUnmounted(() => {
  window.removeEventListener('keydown', handleKeyPress)
})
</script>

<template>
  <div class="min-h-screen flex flex-col bg-background text-foreground">
    <AppHeader />
    <main class="flex-1">
      <router-view v-slot="{ Component }">
        <transition name="fade" mode="out-in">
          <component :is="Component" />
        </transition>
      </router-view>
    </main>
    <AppFooter />
    <LogViewer />
    <Toaster position="bottom-right" :expand="false" rich-colors />
  </div>
</template>

<style scoped>
.fade-enter-active,
.fade-leave-active {
  transition: opacity 0.2s ease;
}
.fade-enter-from,
.fade-leave-to {
  opacity: 0;
}
</style>
