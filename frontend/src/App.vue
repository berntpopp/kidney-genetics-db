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

// Route meta title as the fallback document title (views with useSeoMeta override it);
// global noindex for admin/auth routes
useHead({
  title: computed(() => (route.meta.title ? `${route.meta.title} | KGDB` : undefined)),
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
      <a
        href="#main-content"
        class="sr-only focus:not-sr-only focus:fixed focus:top-2 focus:left-2 focus:z-[60] focus:rounded-md focus:bg-background focus:px-4 focus:py-2 focus:text-sm focus:font-medium focus:shadow-md focus:ring-2 focus:ring-ring"
      >
        Skip to main content
      </a>
      <AppHeader />
      <main id="main-content" tabindex="-1" class="flex-1 focus:outline-none">
        <!-- No route transition: an out-in fade emptied <main> and shifted the page on every navigation -->
        <router-view v-slot="{ Component }">
          <!-- Keyed by path: symbol changes remount gene views; query-only changes do not -->
          <component :is="Component" :key="route.path" />
        </router-view>
      </main>
      <AppFooter />
      <LogViewer v-if="logViewerUsed" />
      <Toaster position="bottom-right" :expand="false" rich-colors />
    </div>
  </TooltipProvider>
</template>
