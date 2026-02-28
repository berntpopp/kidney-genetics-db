<script setup lang="ts">
import { ref, computed, onMounted } from 'vue'
import { getAllVersions, getFrontendVersion } from '@/utils/version'
import { useLogStore } from '@/stores/logStore'
import { Button } from '@/components/ui/button'
import { Popover, PopoverContent, PopoverTrigger } from '@/components/ui/popover'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { Badge } from '@/components/ui/badge'
import { Separator } from '@/components/ui/separator'
import { Info, Server, Database, Cloud, RefreshCw, Github, FileSearch } from 'lucide-vue-next'

const logStore = useLogStore()

// Reactive state
const loading = ref(false)
const frontendVersion = ref(getFrontendVersion())
const backendVersion = ref('...')
const databaseVersion = ref('...')
const environment = ref('...')
const timestamp = ref<string | null>(null)

// Computed properties
const formattedTimestamp = computed(() => {
  if (!timestamp.value) return 'N/A'
  const date = new Date(timestamp.value)
  return date.toLocaleTimeString()
})

const environmentColorClass = computed(() => {
  const envMap: Record<string, string> = {
    production: 'text-green-600 dark:text-green-400',
    staging: 'text-yellow-600 dark:text-yellow-400',
    development: 'text-blue-600 dark:text-blue-400'
  }
  return envMap[environment.value?.toLowerCase()] || 'text-muted-foreground'
})

// Methods
async function refreshVersions() {
  loading.value = true
  try {
    const versions = await getAllVersions()
    frontendVersion.value = versions.frontend.version
    backendVersion.value = versions.backend?.version ?? 'unknown'
    databaseVersion.value = versions.database?.version ?? 'unknown'
    environment.value = versions.environment ?? 'unknown'
    timestamp.value = versions.timestamp ?? null
  } catch (error) {
    console.error('Failed to refresh versions:', error)
    backendVersion.value = 'error'
    databaseVersion.value = 'error'
  } finally {
    loading.value = false
  }
}

// Lifecycle
onMounted(() => {
  refreshVersions()
})
</script>

<template>
  <footer class="border-t bg-background py-1">
    <div class="container mx-auto flex items-center justify-between px-4">
      <!-- Left: Version Information -->
      <Popover>
        <PopoverTrigger as-child>
          <Button variant="ghost" size="sm" class="h-7 text-xs text-muted-foreground">
            <Info class="mr-1 size-3" />
            v{{ frontendVersion }}
          </Button>
        </PopoverTrigger>
        <PopoverContent align="start" class="w-80 p-0">
          <Card class="border-0 shadow-none">
            <CardHeader class="pb-2 pt-3 px-4">
              <CardTitle class="text-sm font-semibold">Component Versions</CardTitle>
            </CardHeader>
            <Separator />
            <CardContent class="p-0">
              <div class="divide-y">
                <!-- Frontend -->
                <div class="flex items-center gap-3 px-4 py-2.5">
                  <Info class="size-4 text-green-600 dark:text-green-400 shrink-0" />
                  <div>
                    <div class="text-xs font-medium">Frontend</div>
                    <div class="text-xs text-muted-foreground">
                      v{{ frontendVersion }} &bull; Vue.js
                    </div>
                  </div>
                </div>
                <!-- Backend -->
                <div class="flex items-center gap-3 px-4 py-2.5">
                  <Server
                    class="size-4 shrink-0"
                    :class="
                      backendVersion === 'unknown'
                        ? 'text-destructive'
                        : 'text-blue-600 dark:text-blue-400'
                    "
                  />
                  <div>
                    <div class="text-xs font-medium">Backend</div>
                    <div class="text-xs text-muted-foreground">
                      v{{ backendVersion }} &bull; FastAPI
                    </div>
                  </div>
                </div>
                <!-- Database -->
                <div class="flex items-center gap-3 px-4 py-2.5">
                  <Database
                    class="size-4 shrink-0"
                    :class="
                      databaseVersion === 'unknown'
                        ? 'text-destructive'
                        : 'text-cyan-600 dark:text-cyan-400'
                    "
                  />
                  <div>
                    <div class="text-xs font-medium">Database</div>
                    <div class="text-xs text-muted-foreground">
                      v{{ databaseVersion }} &bull; PostgreSQL
                    </div>
                  </div>
                </div>
                <!-- Environment -->
                <div class="flex items-center gap-3 px-4 py-2.5">
                  <Cloud class="size-4 shrink-0" :class="environmentColorClass" />
                  <div>
                    <div class="text-xs font-medium">Environment</div>
                    <div class="text-xs text-muted-foreground">{{ environment }}</div>
                  </div>
                </div>
              </div>
              <Separator />
              <div class="flex items-center justify-between px-4 py-2">
                <Button
                  variant="ghost"
                  size="sm"
                  class="h-6 text-xs"
                  :disabled="loading"
                  @click="refreshVersions"
                >
                  <RefreshCw class="mr-1 size-3" :class="{ 'animate-spin': loading }" />
                  Refresh
                </Button>
                <span class="text-xs text-muted-foreground">
                  Updated: {{ formattedTimestamp }}
                </span>
              </div>
            </CardContent>
          </Card>
        </PopoverContent>
      </Popover>

      <!-- Right: Quick Links -->
      <div class="flex items-center gap-1">
        <Button variant="ghost" size="icon" class="size-7" as-child>
          <a href="https://github.com" target="_blank" rel="noopener noreferrer" title="GitHub">
            <Github class="size-4" />
          </a>
        </Button>
        <Button
          variant="ghost"
          size="icon"
          class="size-7 relative"
          :title="`Open Log Viewer (Ctrl+Shift+L) - ${logStore.errorCount} errors`"
          @click="logStore.showViewer"
        >
          <FileSearch class="size-4" />
          <Badge
            v-if="logStore.errorCount > 0"
            variant="destructive"
            class="absolute -top-1 -right-1 size-2 p-0 rounded-full"
          />
        </Button>
      </div>
    </div>
  </footer>
</template>
