<template>
  <v-card class="data-source-progress" elevation="1">
    <v-card-title class="d-flex align-center pa-4">
      <RefreshCw class="size-5 mr-2 text-primary" />
      <span class="text-h6">Data Source Updates</span>
      <v-chip v-if="summary.running > 0" size="x-small" color="primary" label class="ml-2 pulse">
        <Circle class="size-3 mr-1" />
        Live
      </v-chip>
      <v-spacer />
      <span v-if="lastUpdate" class="text-caption text-medium-emphasis mr-2">
        Updated {{ getRelativeTime(lastUpdate) }}
      </span>
      <v-tooltip text="Auto-refresh">
        <template #activator="{ props }">
          <v-btn
            icon
            variant="text"
            size="small"
            v-bind="props"
            :color="autoRefresh ? 'primary' : 'grey'"
            @click="toggleAutoRefresh"
          >
            <component :is="autoRefresh ? RefreshCcw : RefreshCw" class="size-5" />
          </v-btn>
        </template>
      </v-tooltip>
      <v-btn icon variant="text" size="small" @click="toggleExpanded">
        <component :is="expanded ? ChevronUp : ChevronDown" class="size-5" />
      </v-btn>
    </v-card-title>

    <v-expand-transition>
      <div v-show="expanded">
        <v-card-text class="pa-4">
          <!-- Summary Stats - Following stat-card pattern -->
          <v-row class="mb-4">
            <v-col cols="6" sm="3">
              <div class="text-center">
                <v-chip color="success" size="x-small" label>
                  {{ summary.completed }} Completed
                </v-chip>
              </div>
            </v-col>
            <v-col cols="6" sm="3">
              <div class="text-center">
                <v-chip color="primary" size="x-small" label>
                  {{ summary.running }} Running
                </v-chip>
              </div>
            </v-col>
            <v-col cols="6" sm="3">
              <div class="text-center">
                <v-chip color="error" size="x-small" label> {{ summary.failed }} Failed </v-chip>
              </div>
            </v-col>
            <v-col cols="6" sm="3">
              <div class="text-center">
                <v-chip color="grey" size="x-small" label> {{ summary.idle }} Idle </v-chip>
              </div>
            </v-col>
          </v-row>

          <!-- Data Sources -->
          <div v-if="dataSources.length > 0" class="mb-4">
            <div class="text-subtitle-2 text-grey-darken-1 mb-2">Data Sources</div>
            <v-list density="compact" class="pa-0">
              <v-list-item
                v-for="source in dataSources"
                :key="source.source_name"
                class="px-0 py-2"
              >
                <v-list-item-title class="d-flex align-center mb-1">
                  <span class="font-weight-medium">{{ source.source_name }}</span>
                  <v-chip :color="getStatusColor(source.status)" size="x-small" label class="ml-2">
                    {{ source.status }}
                  </v-chip>
                  <span v-if="source.current_operation" class="text-caption ml-2 text-grey">
                    {{ source.current_operation }}
                  </span>
                </v-list-item-title>

                <v-progress-linear
                  :model-value="source.progress_percentage"
                  :color="getStatusColor(source.status)"
                  height="18"
                  rounded
                  class="my-2"
                  :indeterminate="source.status === 'running' && source.progress_percentage === 0"
                >
                  <template #default>
                    <span class="text-caption font-weight-medium">
                      {{ Math.ceil(source.progress_percentage) }}%
                    </span>
                  </template>
                </v-progress-linear>

                <div class="d-flex align-center text-caption">
                  <span v-if="source.items_added > 0" class="mr-3">
                    <Plus class="size-3 mr-1 text-green-600 dark:text-green-400" />
                    {{ source.items_added }}
                  </span>
                  <span v-if="source.items_updated > 0" class="mr-3">
                    <RefreshCw class="size-3 mr-1 text-blue-600 dark:text-blue-400" />
                    {{ source.items_updated }}
                  </span>
                  <span v-if="source.items_failed > 0" class="mr-3">
                    <AlertTriangle class="size-3 mr-1 text-destructive" />
                    {{ source.items_failed }}
                  </span>
                  <v-spacer />
                  <!-- Action buttons -->
                  <v-btn
                    v-if="source.status === 'idle' || source.status === 'failed'"
                    icon
                    size="x-small"
                    variant="text"
                    color="primary"
                    :loading="triggering[source.source_name]"
                    @click="triggerUpdate(source.source_name)"
                  >
                    <Play class="size-4" />
                  </v-btn>
                  <v-btn
                    v-else-if="source.status === 'running'"
                    icon
                    size="x-small"
                    variant="text"
                    color="warning"
                    @click="pauseSource(source.source_name)"
                  >
                    <Pause class="size-4" />
                  </v-btn>
                  <v-btn
                    v-else-if="source.status === 'paused'"
                    icon
                    size="x-small"
                    variant="text"
                    color="success"
                    @click="resumeSource(source.source_name)"
                  >
                    <Play class="size-4" />
                  </v-btn>
                </div>

                <!-- Error message if exists -->
                <div v-if="source.last_error" class="text-caption text-error mt-1">
                  Error: {{ source.last_error }}
                </div>
              </v-list-item>
            </v-list>
          </div>

          <!-- Internal Processes -->
          <div v-if="internalProcesses.length > 0">
            <div class="text-subtitle-2 text-grey-darken-1 mb-2">Internal Processes</div>
            <v-list density="compact" class="pa-0">
              <v-list-item
                v-for="source in internalProcesses"
                :key="source.source_name"
                class="px-0 py-2"
              >
                <v-list-item-title class="d-flex align-center mb-1">
                  <span class="font-weight-medium">{{ source.source_name.replace('_', ' ') }}</span>
                  <v-chip :color="getStatusColor(source.status)" size="x-small" label class="ml-2">
                    {{ source.status }}
                  </v-chip>
                  <span v-if="source.current_operation" class="text-caption ml-2 text-grey">
                    {{ source.current_operation }}
                  </span>
                </v-list-item-title>

                <v-progress-linear
                  :model-value="source.progress_percentage"
                  :color="getStatusColor(source.status)"
                  height="18"
                  rounded
                  class="my-2"
                  :indeterminate="source.status === 'running' && source.progress_percentage === 0"
                >
                  <template #default>
                    <span class="text-caption font-weight-medium">
                      {{ Math.ceil(source.progress_percentage) }}%
                    </span>
                  </template>
                </v-progress-linear>

                <div class="d-flex align-center text-caption">
                  <span v-if="source.items_processed > 0" class="mr-3">
                    <Cog class="size-3 mr-1 text-blue-600 dark:text-blue-400" />
                    {{ source.items_processed }} processed
                  </span>
                  <v-spacer />
                  <!-- Show pause/resume for annotation_pipeline like PubTator -->
                  <v-btn
                    v-if="
                      source.source_name === 'annotation_pipeline' &&
                      (source.status === 'idle' || source.status === 'failed')
                    "
                    icon
                    size="x-small"
                    variant="text"
                    color="primary"
                    :loading="triggering[source.source_name]"
                    @click="triggerUpdate(source.source_name)"
                  >
                    <Play class="size-4" />
                  </v-btn>
                  <v-btn
                    v-else-if="
                      source.source_name === 'annotation_pipeline' && source.status === 'running'
                    "
                    icon
                    size="x-small"
                    variant="text"
                    color="warning"
                    @click="pauseSource(source.source_name)"
                  >
                    <Pause class="size-4" />
                  </v-btn>
                  <v-btn
                    v-else-if="
                      source.source_name === 'annotation_pipeline' && source.status === 'paused'
                    "
                    icon
                    size="x-small"
                    variant="text"
                    color="success"
                    @click="resumeSource(source.source_name)"
                  >
                    <Play class="size-4" />
                  </v-btn>
                  <v-chip
                    v-else-if="source.status === 'completed'"
                    size="x-small"
                    color="success"
                    label
                  >
                    <Check class="size-3 mr-1" />
                    Complete
                  </v-chip>
                </div>

                <!-- Error message if exists -->
                <div v-if="source.last_error" class="text-caption text-error mt-1">
                  Error: {{ source.last_error }}
                </div>
              </v-list-item>
            </v-list>
          </div>
        </v-card-text>
      </div>
    </v-expand-transition>
  </v-card>
</template>

<script setup>
import { ref, computed, onMounted, onUnmounted } from 'vue'
import apiClient from '@/api/client'
import { RefreshCw, RefreshCcw, ChevronUp, ChevronDown, Circle, Plus, AlertTriangle, Play, Pause, Cog, Check } from 'lucide-vue-next'

// Browser globals are already defined in eslint config

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
    .sort((a, b) => a.source_name.localeCompare(b.source_name)) // Stable alphabetical sort
})

const internalProcesses = computed(() => {
  return sources.value
    .filter(
      s =>
        s.category === 'internal_process' ||
        (!s.category && ['Evidence_Aggregation', 'HGNC_Normalization'].includes(s.source_name))
    )
    .sort((a, b) => a.source_name.localeCompare(b.source_name)) // Stable alphabetical sort
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
const getStatusColor = status => {
  // Following style guide color system
  const colors = {
    running: 'primary', // #0EA5E9
    completed: 'success', // #10B981
    failed: 'error', // #EF4444
    idle: 'grey',
    paused: 'warning' // #F59E0B
  }
  return colors[status] || 'grey'
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

const toggleExpanded = () => {
  expanded.value = !expanded.value
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

    // Auto-expand if sources are running
    if (summary.value.running > 0 && !expanded.value) {
      expanded.value = true
    }
  } catch (error) {
    window.logService.error('Failed to fetch status:', error)
  }
}

const startPolling = () => {
  stopPolling() // Clear any existing interval

  // Start polling every 3 seconds when any source is running
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
      // Update sources with new progress data
      message.data.forEach(update => {
        const index = sources.value.findIndex(s => s.source_name === update.source_name)
        if (index >= 0) {
          sources.value[index] = update
        }
      })
    } else if (message.type === 'status_change') {
      // Update single source status
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
    // Try to reconnect after 5 seconds
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

  // Start auto-refresh by default
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
/* Following style guide spacing system (4px grid) */
.data-source-progress {
  margin-bottom: 16px; /* mb-4 equivalent */
}

/* Professional typography */
.text-caption {
  font-weight: 500;
  text-transform: uppercase;
  letter-spacing: 0.05em;
}

/* Ensure progress bar text is visible */
.v-progress-linear {
  font-variant-numeric: tabular-nums;
}

/* Pulsing animation for live indicator */
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

/* Smooth transitions for progress bars */
.v-progress-linear {
  transition: all 0.3s cubic-bezier(0.4, 0, 0.2, 1);
}

/* Hover effect for expandable card */
.data-source-progress:hover {
  box-shadow:
    0 4px 6px -1px rgba(0, 0, 0, 0.1),
    0 2px 4px -1px rgba(0, 0, 0, 0.06);
}

/* Respect motion preferences */
@media (prefers-reduced-motion: reduce) {
  .pulse {
    animation: none;
  }

  .v-progress-linear {
    transition-duration: 0.01ms !important;
  }
}
</style>
