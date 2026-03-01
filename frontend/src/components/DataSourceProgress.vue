<template>
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
                <Button variant="ghost" size="icon" class="h-8 w-8" @click="toggleAutoRefresh">
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
            <Button variant="ghost" size="icon" class="h-8 w-8">
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
          <div class="mb-4 grid grid-cols-4 gap-2">
            <div class="text-center">
              <Badge variant="default" class="bg-green-500 text-xs hover:bg-green-500">
                {{ summary.completed }} Completed
              </Badge>
            </div>
            <div class="text-center">
              <Badge variant="default" class="text-xs"> {{ summary.running }} Running </Badge>
            </div>
            <div class="text-center">
              <Badge variant="destructive" class="text-xs"> {{ summary.failed }} Failed </Badge>
            </div>
            <div class="text-center">
              <Badge variant="secondary" class="text-xs"> {{ summary.idle }} Idle </Badge>
            </div>
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
                    <div class="h-2 w-2 rounded-full" :class="getStatusDotClass(source.status)" />
                    <span class="text-sm font-medium">{{ source.source_name }}</span>
                    <Badge variant="outline" class="text-xs">{{ source.status }}</Badge>
                    <span v-if="source.current_operation" class="text-xs text-muted-foreground">
                      {{ source.current_operation }}
                    </span>
                  </div>
                  <div class="flex items-center gap-1">
                    <Button
                      v-if="source.status === 'idle' || source.status === 'failed'"
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
                      variant="ghost"
                      size="icon"
                      class="h-6 w-6"
                      @click="pauseSource(source.source_name)"
                    >
                      <Pause :size="12" />
                    </Button>
                    <Button
                      v-else-if="source.status === 'paused'"
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
                  <span v-if="source.items_added > 0" class="text-green-500">
                    <Plus :size="10" class="mr-0.5 inline" />{{ source.items_added }}
                  </span>
                  <span v-if="source.items_updated > 0" class="text-blue-500">
                    <RefreshCw :size="10" class="mr-0.5 inline" />{{ source.items_updated }}
                  </span>
                  <span v-if="source.items_failed > 0" class="text-red-500">
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
                    <div class="h-2 w-2 rounded-full" :class="getStatusDotClass(source.status)" />
                    <span class="text-sm font-medium">{{
                      source.source_name.replace('_', ' ')
                    }}</span>
                    <Badge variant="outline" class="text-xs">{{ source.status }}</Badge>
                    <span v-if="source.current_operation" class="text-xs text-muted-foreground">
                      {{ source.current_operation }}
                    </span>
                  </div>
                  <div class="flex items-center gap-1">
                    <Button
                      v-if="
                        source.source_name === 'annotation_pipeline' &&
                        (source.status === 'idle' || source.status === 'failed')
                      "
                      variant="ghost"
                      size="icon"
                      class="h-6 w-6"
                      :disabled="triggering[source.source_name]"
                      @click="triggerUpdate(source.source_name)"
                    >
                      <Play :size="12" />
                    </Button>
                    <Button
                      v-else-if="
                        source.source_name === 'annotation_pipeline' && source.status === 'running'
                      "
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
                      variant="ghost"
                      size="icon"
                      class="h-6 w-6"
                      @click="resumeSource(source.source_name)"
                    >
                      <Play :size="12" />
                    </Button>
                    <Badge
                      v-else-if="source.status === 'completed'"
                      variant="default"
                      class="bg-green-500 text-xs hover:bg-green-500"
                    >
                      <Check :size="10" class="mr-1" />
                      Complete
                    </Badge>
                  </div>
                </div>
                <Progress :model-value="source.progress_percentage || 0" class="h-2" />
                <div class="mt-2 flex items-center gap-3 text-xs">
                  <span v-if="source.items_processed > 0" class="text-blue-500">
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
</template>

<script setup>
import { ref, computed, onMounted, onUnmounted } from 'vue'
import apiClient from '@/api/client'
import {
  RefreshCw,
  RefreshCcw,
  ChevronDown,
  Circle,
  Plus,
  AlertTriangle,
  Play,
  Pause,
  Cog,
  Check
} from 'lucide-vue-next'
import { Card, CardHeader, CardTitle, CardContent } from '@/components/ui/card'
import { Collapsible, CollapsibleContent, CollapsibleTrigger } from '@/components/ui/collapsible'
import { Badge } from '@/components/ui/badge'
import { Button } from '@/components/ui/button'
import { Progress } from '@/components/ui/progress'
import { Tooltip, TooltipContent, TooltipProvider, TooltipTrigger } from '@/components/ui/tooltip'

// State
const expanded = ref(false)
const sources = ref([])
const triggering = ref({})
const ws = ref(null)
const reconnectInterval = ref(null)
const pollInterval = ref(null)
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
const getStatusDotClass = status => {
  const classes = {
    running: 'bg-primary',
    completed: 'bg-green-500',
    failed: 'bg-red-500',
    idle: 'bg-muted-foreground',
    paused: 'bg-yellow-500'
  }
  return classes[status] || 'bg-muted-foreground'
}

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
  const wsUrl = 'ws://localhost:8000/api/progress/ws'
  ws.value = new WebSocket(wsUrl)

  ws.value.onopen = () => {
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
  if (ws.value) {
    ws.value.close()
  }
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
