<template>
  <footer class="border-t bg-card py-2">
    <div class="container mx-auto px-4">
      <div class="flex items-center justify-between">
        <!-- Left: Version info dropdown -->
        <DropdownMenu>
          <DropdownMenuTrigger as-child>
            <Button variant="ghost" size="sm" class="text-xs text-muted-foreground">
              <Info :size="14" class="mr-1" />
              v{{ frontendVersion }}
            </Button>
          </DropdownMenuTrigger>
          <DropdownMenuContent align="start" class="w-72">
            <DropdownMenuLabel>Component Versions</DropdownMenuLabel>
            <DropdownMenuSeparator />

            <!-- Frontend Version -->
            <DropdownMenuItem class="gap-3">
              <Code :size="16" class="shrink-0 text-green-600 dark:text-green-400" />
              <div class="flex flex-col">
                <span class="text-xs font-medium">Frontend</span>
                <span class="text-xs text-muted-foreground"
                  >v{{ frontendVersion }} &bull; Vue.js</span
                >
              </div>
            </DropdownMenuItem>

            <DropdownMenuSeparator />

            <!-- Backend Version -->
            <DropdownMenuItem class="gap-3">
              <Server
                :size="16"
                class="shrink-0"
                :class="backendVersion === 'unknown' ? 'text-destructive' : 'text-primary'"
              />
              <div class="flex flex-col">
                <span class="text-xs font-medium">Backend</span>
                <span class="text-xs text-muted-foreground"
                  >v{{ backendVersion }} &bull; FastAPI</span
                >
              </div>
            </DropdownMenuItem>

            <DropdownMenuSeparator />

            <!-- Database Version -->
            <DropdownMenuItem class="gap-3">
              <Database
                :size="16"
                class="shrink-0"
                :class="
                  databaseVersion === 'unknown'
                    ? 'text-destructive'
                    : 'text-blue-600 dark:text-blue-400'
                "
              />
              <div class="flex flex-col">
                <span class="text-xs font-medium">Database</span>
                <span class="text-xs text-muted-foreground"
                  >v{{ databaseVersion }} &bull; PostgreSQL</span
                >
              </div>
            </DropdownMenuItem>

            <DropdownMenuSeparator />

            <!-- Environment -->
            <DropdownMenuItem class="gap-3">
              <Cloud :size="16" class="shrink-0" />
              <div class="flex flex-col">
                <span class="text-xs font-medium">Environment</span>
                <span class="text-xs text-muted-foreground">{{ environment }}</span>
              </div>
            </DropdownMenuItem>

            <DropdownMenuSeparator />

            <!-- Refresh + timestamp -->
            <div class="flex items-center justify-between px-2 py-1.5">
              <Button
                variant="ghost"
                size="sm"
                class="h-6 text-xs"
                :disabled="loading"
                @click="refreshVersions"
              >
                <RefreshCw :size="12" class="mr-1" :class="{ 'animate-spin': loading }" />
                Refresh
              </Button>
              <span class="text-xs text-muted-foreground">
                {{ formattedTimestamp }}
              </span>
            </div>
          </DropdownMenuContent>
        </DropdownMenu>

        <!-- Right: Quick links -->
        <div class="flex items-center gap-1">
          <!-- GitHub link -->
          <Button
            variant="ghost"
            size="icon"
            class="h-8 w-8"
            as="a"
            href="https://github.com"
            target="_blank"
            title="GitHub"
          >
            <Github :size="16" />
          </Button>

          <!-- Log viewer -->
          <Button
            variant="ghost"
            size="icon"
            class="h-8 w-8 relative"
            :title="`Open Log Viewer (Ctrl+Shift+L) - ${logStore.errorCount} errors`"
            @click="logStore.showViewer"
          >
            <FileSearch :size="16" />
            <span
              v-if="logStore.errorCount > 0"
              class="absolute -top-0.5 -right-0.5 h-2 w-2 rounded-full bg-destructive"
            />
          </Button>
        </div>
      </div>
    </div>
  </footer>
</template>

<script setup lang="ts">
import { ref, computed, onMounted } from 'vue'
import { getAllVersions, getFrontendVersion } from '@/utils/version'
import { useLogStore } from '@/stores/logStore'
import { Info, Code, Server, Database, Cloud, FileSearch, RefreshCw, Github } from 'lucide-vue-next'
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuLabel,
  DropdownMenuSeparator,
  DropdownMenuTrigger
} from '@/components/ui/dropdown-menu'
import { Button } from '@/components/ui/button'

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

// Methods
async function refreshVersions() {
  loading.value = true
  try {
    const versions = await getAllVersions()

    frontendVersion.value = versions.frontend.version
    backendVersion.value = versions.backend.version
    databaseVersion.value = versions.database.version
    environment.value = versions.environment
    timestamp.value = versions.timestamp
  } catch (error) {
    window.logService.error('Failed to refresh versions:', error)
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
