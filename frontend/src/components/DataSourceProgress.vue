<template>
  <!-- Provider for the StatusBadge tooltips (also when rendered outside App) -->
  <TooltipProvider>
    <Card>
      <Collapsible v-model:open="expanded">
        <CardHeader class="flex flex-row items-center justify-between p-4">
          <div class="flex items-center gap-2">
            <RefreshCw :size="18" class="text-primary" />
            <CardTitle class="text-base">Data Source Updates</CardTitle>
            <Badge v-if="summary.running > 0" variant="default" class="pulse text-xs">
              <Circle :size="8" class="mr-1" />
              Live
            </Badge>
          </div>
          <div class="flex items-center gap-1">
            <span v-if="lastUpdate" class="mr-2 text-xs text-muted-foreground">
              Updated {{ getRelativeTime(lastUpdate) }}
            </span>
            <TooltipProvider>
              <Tooltip>
                <TooltipTrigger as-child>
                  <Button
                    aria-label="Auto-refresh"
                    :aria-pressed="autoRefresh"
                    variant="ghost"
                    size="icon"
                    class="h-8 w-8"
                    @click="toggleAutoRefresh"
                  >
                    <component
                      :is="autoRefresh ? RefreshCcw : RefreshCw"
                      :size="14"
                      :class="autoRefresh ? 'text-primary' : 'text-muted-foreground'"
                    />
                  </Button>
                </TooltipTrigger>
                <TooltipContent>Auto-refresh</TooltipContent>
              </Tooltip>
            </TooltipProvider>
            <CollapsibleTrigger as-child>
              <Button
                aria-label="Toggle data source details"
                variant="ghost"
                size="icon"
                class="h-8 w-8"
              >
                <ChevronDown
                  :size="14"
                  :class="{ 'rotate-180': expanded }"
                  class="transition-transform"
                />
              </Button>
            </CollapsibleTrigger>
          </div>
        </CardHeader>
        <CollapsibleContent>
          <CardContent class="pt-0">
            <!-- Summary Stats -->
            <div class="mb-4 flex flex-wrap gap-2">
              <StatusBadge status="completed" :label="`${summary.completed} Completed`" />
              <StatusBadge status="running" :label="`${summary.running} Running`" />
              <StatusBadge status="failed" :label="`${summary.failed} Failed`" />
              <StatusBadge status="idle" :label="`${summary.idle} Idle`" />
            </div>

            <!-- Data Sources -->
            <div v-if="dataSources.length > 0" class="mb-4">
              <p class="mb-2 text-sm font-medium text-muted-foreground">Data Sources</p>
              <div class="space-y-3">
                <div
                  v-for="source in dataSources"
                  :key="source.source_name"
                  class="rounded-md border p-3"
                >
                  <div class="mb-2 flex items-center justify-between">
                    <div class="flex items-center gap-2">
                      <span class="text-sm font-medium">{{
                        sourceDisplayName(source.source_name)
                      }}</span>
                      <StatusBadge :status="source.status" />
                      <span v-if="source.current_operation" class="text-xs text-muted-foreground">
                        {{ source.current_operation }}
                      </span>
                    </div>
                    <div class="flex items-center gap-1">
                      <Button
                        v-if="source.status === 'idle' || source.status === 'failed'"
                        :aria-label="`Start ${source.source_name}`"
                        variant="ghost"
                        size="icon"
                        class="h-6 w-6"
                        :disabled="triggering[source.source_name]"
                        @click="triggerUpdate(source.source_name)"
                      >
                        <Play :size="12" />
                      </Button>
                      <Button
                        v-else-if="source.status === 'running'"
                        :aria-label="`Pause ${source.source_name}`"
                        variant="ghost"
                        size="icon"
                        class="h-6 w-6"
                        @click="pauseSource(source.source_name)"
                      >
                        <Pause :size="12" />
                      </Button>
                      <Button
                        v-else-if="source.status === 'paused'"
                        :aria-label="`Resume ${source.source_name}`"
                        variant="ghost"
                        size="icon"
                        class="h-6 w-6"
                        @click="resumeSource(source.source_name)"
                      >
                        <Play :size="12" />
                      </Button>
                    </div>
                  </div>
                  <Progress :model-value="source.progress_percentage || 0" class="h-2" />
                  <div class="mt-2 flex items-center gap-3 text-xs">
                    <span v-if="source.items_added > 0" class="text-success">
                      <Plus :size="10" class="mr-0.5 inline" />{{ source.items_added }}
                    </span>
                    <span v-if="source.items_updated > 0" class="text-muted-foreground">
                      <RefreshCw :size="10" class="mr-0.5 inline" />{{ source.items_updated }}
                    </span>
                    <span v-if="source.items_failed > 0" class="text-danger">
                      <AlertTriangle :size="10" class="mr-0.5 inline" />{{ source.items_failed }}
                    </span>
                  </div>
                  <div v-if="source.last_error" class="mt-1 text-xs text-destructive">
                    Error: {{ source.last_error }}
                  </div>
                </div>
              </div>
            </div>

            <!-- Internal Processes -->
            <div v-if="internalProcesses.length > 0">
              <p class="mb-2 text-sm font-medium text-muted-foreground">Internal Processes</p>
              <div class="space-y-3">
                <div
                  v-for="source in internalProcesses"
                  :key="source.source_name"
                  class="rounded-md border p-3"
                >
                  <div class="mb-2 flex items-center justify-between">
                    <div class="flex items-center gap-2">
                      <span class="text-sm font-medium">{{
                        source.source_name.replace('_', ' ')
                      }}</span>
                      <StatusBadge :status="source.status" />
                      <span v-if="source.current_operation" class="text-xs text-muted-foreground">
                        {{ source.current_operation }}
                      </span>
                    </div>
                    <div class="flex items-center gap-1">
                      <!-- No Start here: pipeline-wide runs go through the confirmed AdminAnnotations form (issue 317) -->
                      <Button
                        v-if="
                          source.source_name === 'annotation_pipeline' &&
                          source.status === 'running'
                        "
                        :aria-label="`Pause ${source.source_name}`"
                        variant="ghost"
                        size="icon"
                        class="h-6 w-6"
                        @click="pauseSource(source.source_name)"
                      >
                        <Pause :size="12" />
                      </Button>
                      <Button
                        v-else-if="
                          source.source_name === 'annotation_pipeline' && source.status === 'paused'
                        "
                        :aria-label="`Resume ${source.source_name}`"
                        variant="ghost"
                        size="icon"
                        class="h-6 w-6"
                        @click="resumeSource(source.source_name)"
                      >
                        <Play :size="12" />
                      </Button>
                      <StatusBadge
                        v-else-if="source.status === 'completed'"
                        status="completed"
                        label="Complete"
                      />
                    </div>
                  </div>
                  <Progress :model-value="source.progress_percentage || 0" class="h-2" />
                  <div class="mt-2 flex items-center gap-3 text-xs">
                    <span v-if="source.items_processed > 0" class="text-muted-foreground">
                      <Cog :size="10" class="mr-0.5 inline" />{{ source.items_processed }}
                      processed
                    </span>
                  </div>
                  <div v-if="source.last_error" class="mt-1 text-xs text-destructive">
                    Error: {{ source.last_error }}
                  </div>
                </div>
              </div>
            </div>
          </CardContent>
        </CollapsibleContent>
      </Collapsible>
    </Card>
  </TooltipProvider>
</template>

<script setup>
import { ref, computed, onMounted, onUnmounted } from 'vue'
import apiClient, { getClientAccessToken } from '@/api/client'
import { config } from '@/config'
import {
  RefreshCw,
  RefreshCcw,
  ChevronDown,
  Circle,
  Plus,
  AlertTriangle,
  Play,
  Pause,
  Cog
} from 'lucide-vue-next'
import { Card, CardHeader, CardTitle, CardContent } from '@/components/ui/card'
import { Collapsible, CollapsibleContent, CollapsibleTrigger } from '@/components/ui/collapsible'
import { Badge } from '@/components/ui/badge'
import { Button } from '@/components/ui/button'
import { Progress } from '@/components/ui/progress'
import { Tooltip, TooltipContent, TooltipProvider, TooltipTrigger } from '@/components/ui/tooltip'
import { StatusBadge } from '@/components/shared'
import { sourceDisplayName } from '@/utils/sources'

// State
const expanded = ref(false)
const sources = ref([])
const triggering = ref({})
const ws = ref(null)
const reconnectInterval = ref(null)
const pollInterval = ref(null)
let unmounted = false
const autoRefresh = ref(true)
const lastUpdate = ref(new Date())

// Computed
const dataSources = computed(() => {
  return sources.value
    .filter(
      s =>
        s.category === 'data_source' ||
        (!s.category &&
          ['PubTator', 'PanelApp', 'HPO', 'ClinGen', 'GenCC', 'OMIM', 'Literature'].includes(
            s.source_name
          ))
    )
    .sort((a, b) => a.source_name.localeCompare(b.source_name))
})

const internalProcesses = computed(() => {
  return sources.value
    .filter(
      s =>
        s.category === 'internal_process' ||
        (!s.category && ['Evidence_Aggregation', 'HGNC_Normalization'].includes(s.source_name))
    )
    .sort((a, b) => a.source_name.localeCompare(b.source_name))
})

const summary = computed(() => {
  return {
    running: sources.value.filter(s => s.status === 'running').length,
    completed: sources.value.filter(s => s.status === 'completed').length,
    failed: sources.value.filter(s => s.status === 'failed').length,
    idle: sources.value.filter(s => s.status === 'idle').length,
    paused: sources.value.filter(s => s.status === 'paused').length
  }
})

// Methods
const getRelativeTime = date => {
  const seconds = Math.floor((new Date() - date) / 1000)

  if (seconds < 5) return 'just now'
  if (seconds < 60) return `${seconds}s ago`

  const minutes = Math.floor(seconds / 60)
  if (minutes < 60) return `${minutes}m ago`

  const hours = Math.floor(minutes / 60)
  if (hours < 24) return `${hours}h ago`

  const days = Math.floor(hours / 24)
  return `${days}d ago`
}

const toggleAutoRefresh = () => {
  autoRefresh.value = !autoRefresh.value
  if (autoRefresh.value) {
    startPolling()
  } else {
    stopPolling()
  }
}

const fetchStatus = async () => {
  try {
    const response = await apiClient.get('/api/progress/status')
    sources.value = response.data.data
    lastUpdate.value = new Date()

    if (summary.value.running > 0 && !expanded.value) {
      expanded.value = true
    }
  } catch (error) {
    window.logService.error('Failed to fetch status:', error)
  }
}

const startPolling = () => {
  stopPolling()

  pollInterval.value = setInterval(() => {
    if (summary.value.running > 0 || autoRefresh.value) {
      fetchStatus()
    }
  }, 3000)
}

const stopPolling = () => {
  if (pollInterval.value) {
    clearInterval(pollInterval.value)
    pollInterval.value = null
  }
}

const connectWebSocket = () => {
  // One socket at a time: a slow handshake must not spawn a second one that unmount would miss
  if (unmounted || (ws.value && ws.value.readyState <= WebSocket.OPEN)) return
  // Same host and path as the REST API base (empty base = same origin), http(s) -> ws(s)
  const url = new URL(
    `${config.apiBaseUrl.replace(/\/$/, '')}/api/progress/ws`,
    window.location.href
  )
  url.protocol = url.protocol === 'https:' ? 'wss:' : 'ws:'
  ws.value = new WebSocket(url.href)

  ws.value.onopen = () => {
    if (unmounted) return
    // Authenticate in the first message: a token in the URL would land in request logs
    ws.value.send(JSON.stringify({ type: 'auth', token: getClientAccessToken() }))
    window.logService.info('WebSocket connected for progress updates')
    if (reconnectInterval.value) {
      clearInterval(reconnectInterval.value)
      reconnectInterval.value = null
    }
  }

  ws.value.onmessage = event => {
    const message = JSON.parse(event.data)

    if (message.type === 'initial_status') {
      sources.value = message.data
    } else if (message.type === 'progress_update') {
      message.data.forEach(update => {
        const index = sources.value.findIndex(s => s.source_name === update.source_name)
        if (index >= 0) {
          sources.value[index] = update
        }
      })
    } else if (message.type === 'status_change') {
      const index = sources.value.findIndex(s => s.source_name === message.source)
      if (index >= 0) {
        sources.value[index] = message.data
      }
    }
  }

  ws.value.onerror = error => {
    window.logService.error('WebSocket error:', error)
  }

  ws.value.onclose = () => {
    if (unmounted) return
    window.logService.info('WebSocket disconnected')
    if (!reconnectInterval.value) {
      reconnectInterval.value = setInterval(() => {
        window.logService.info('Attempting to reconnect WebSocket...')
        connectWebSocket()
      }, 5000)
    }
  }
}

const triggerUpdate = async sourceName => {
  triggering.value[sourceName] = true
  try {
    await apiClient.post(`/api/progress/trigger/${sourceName}`)
  } catch (error) {
    window.logService.error(`Failed to trigger ${sourceName}:`, error)
  } finally {
    triggering.value[sourceName] = false
  }
}

const pauseSource = async sourceName => {
  try {
    await apiClient.post(`/api/progress/pause/${sourceName}`)
  } catch (error) {
    window.logService.error(`Failed to pause ${sourceName}:`, error)
  }
}

const resumeSource = async sourceName => {
  try {
    await apiClient.post(`/api/progress/resume/${sourceName}`)
  } catch (error) {
    window.logService.error(`Failed to resume ${sourceName}:`, error)
  }
}

// Lifecycle
onMounted(() => {
  fetchStatus()
  connectWebSocket()

  if (autoRefresh.value) {
    startPolling()
  }
})

onUnmounted(() => {
  unmounted = true // close() fires onclose asynchronously, which would re-arm reconnects
  ws.value?.close()
  if (reconnectInterval.value) {
    clearInterval(reconnectInterval.value)
  }
  if (pollInterval.value) {
    clearInterval(pollInterval.value)
  }
})
</script>

<style scoped>
.pulse {
  animation: pulse 2s cubic-bezier(0.4, 0, 0.6, 1) infinite;
}

@keyframes pulse {
  0%,
  100% {
    opacity: 1;
  }
  50% {
    opacity: 0.5;
  }
}

@media (prefers-reduced-motion: reduce) {
  .pulse {
    animation: none;
  }
}
</style>
