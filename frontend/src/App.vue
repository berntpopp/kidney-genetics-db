<script setup lang="ts">
import { computed, defineAsyncComponent, onMounted, onUnmounted, ref, watch } from 'vue'
import { useRoute } from 'vue-router'
import { useHead } from '@unhead/vue'
import AppHeader from '@/layouts/AppHeader.vue'
import AppFooter from '@/layouts/AppFooter.vue'
import { Toaster } from '@/components/ui/sonner'
import { TooltipProvider } from '@/components/ui/tooltip'
import { useLogStore } from '@/stores/logStore'
import { useAppTheme } from '@/composables/useAppTheme'
import { useJsonLd, getOrganizationWebSiteSchema } from '@/composables/useJsonLd'

const route = useRoute()
const logStore = useLogStore()

// Admin log viewer loads on first open only; it then stays mounted to keep its filters
const LogViewer = defineAsyncComponent(() => import('@/components/admin/LogViewer.vue'))
const logViewerUsed = ref(false)
watch(
  () => logStore.isViewerVisible,
  visible => {
    if (visible) logViewerUsed.value = true
  },
  { immediate: true }
)

// Initialize dark mode bidirectional sync
useAppTheme()

// Global JSON-LD: Organization + WebSite schema
useJsonLd(getOrganizationWebSiteSchema())

// Global noindex for admin/auth routes
useHead({
  meta: computed(() =>
    route.meta.noindex ? [{ name: 'robots', content: 'noindex, nofollow' }] : []
  )
})

// Keyboard shortcut for log viewer (Ctrl+Shift+L)
const handleKeyPress = (event: KeyboardEvent) => {
  if (event.ctrlKey && event.shiftKey && event.key === 'L') {
    event.preventDefault()
    logStore.toggleViewer()
  }
}

onMounted(() => {
  window.addEventListener('keydown', handleKeyPress)
})

onUnmounted(() => {
  window.removeEventListener('keydown', handleKeyPress)
})
</script>

<template>
  <TooltipProvider :delay-duration="0">
    <div class="min-h-screen flex flex-col bg-background text-foreground">
      <AppHeader />
      <main class="flex-1 pb-20">
        <router-view v-slot="{ Component }">
          <transition name="fade" mode="out-in">
            <!-- Keyed by path: symbol changes remount gene views; query-only changes do not -->
            <component :is="Component" :key="route.path" />
          </transition>
        </router-view>
      </main>
      <AppFooter />
      <LogViewer v-if="logViewerUsed" />
      <Toaster position="bottom-right" :expand="false" rich-colors />
    </div>
  </TooltipProvider>
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
