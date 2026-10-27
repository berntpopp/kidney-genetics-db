<script setup>
/**
 * Pipeline Control View
 * Real-time monitoring and control of data pipelines
 */

import { ref, computed, onMounted, onUnmounted } from 'vue'
import { RouterLink } from 'vue-router'
import { useWebSocket } from '@/services/websocket'
import AdminHeader from '@/components/admin/AdminHeader.vue'
import { Chip, DataState, PAGE_CONTAINER, SourceLabel, StatusBadge } from '@/components/shared'
import { sourceDisplayName } from '@/utils/sources'
import AdminStatsCard from '@/components/admin/AdminStatsCard.vue'
import * as pipelineApi from '@/api/admin/pipeline'
import { toast } from 'vue-sonner'
import {
  AlertTriangle,
  CircleAlert,
  CircleCheck,
  CirclePlay,
  Cog,
  Database,
  Info,
  Loader2,
  Pause,
  Play,
  RefreshCw,
  Upload
} from 'lucide-vue-next'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { Button } from '@/components/ui/button'
import { Progress } from '@/components/ui/progress'
import { Alert, AlertDescription } from '@/components/ui/alert'
import {
  AlertDialog,
  AlertDialogAction,
  AlertDialogCancel,
  AlertDialogContent,
  AlertDialogDescription,
  AlertDialogFooter,
  AlertDialogHeader,
  AlertDialogTitle
} from '@/components/ui/alert-dialog'
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle
} from '@/components/ui/dialog'

const { connected: wsConnected, connect, disconnect, subscribe } = useWebSocket()

// State
const sources = ref([])
const loading = ref(false)
const loadError = ref(null)
const triggering = ref({})
const pausing = ref({})
const resuming = ref({})
const triggeringAll = ref(false)
const showRunAllDialog = ref(false)
const showDetailsDialog = ref(false)
const selectedSource = ref(null)

// WebSocket subscriptions
const unsubscribers = []

// Computed — filter by category, sort by source_name for stable tile order
const dataSources = computed(() =>
  sources.value
    .filter(s => s.category === 'data_source')
    .sort((a, b) => a.source_name.localeCompare(b.source_name))
)

const hybridSources = computed(() =>
  sources.value
    .filter(s => s.category === 'hybrid_source')
    .sort((a, b) => a.source_name.localeCompare(b.source_name))
)

const internalProcesses = computed(() =>
  sources.value
    .filter(s => s.category === 'internal_process')
    .sort((a, b) => a.source_name.localeCompare(b.source_name))
)

// Includes internal processes such as the annotation pipeline (#370)
const runningSources = computed(() => sources.value.filter(s => s.status === 'running').length)

const completedSources = computed(
  () => dataSources.value.filter(s => s.status === 'completed').length
)

const failedSources = computed(() => dataSources.value.filter(s => s.status === 'failed').length)

// Methods
const loadSources = async () => {
  loading.value = true
  loadError.value = null
  try {
    const response = await pipelineApi.getAllStatus()
    // API returns { data: [...], meta: {...} } structure
    sources.value = response.data?.data || []
    now.value = Date.now()
  } catch (error) {
    window.logService.error('Failed to load sources:', error)
    loadError.value = error.message || 'Request failed'
  } finally {
    loading.value = false
  }
}

const triggerSource = async sourceName => {
  triggering.value[sourceName] = true
  try {
    await pipelineApi.triggerUpdate(sourceName)
    toast.success(`Started ${sourceDisplayName(sourceName)}`, { duration: 5000 })
  } catch (error) {
    window.logService.error(`Failed to trigger ${sourceName}:`, error)
    toast.error(`Failed to start ${sourceDisplayName(sourceName)}`, { duration: Infinity })
  } finally {
    triggering.value[sourceName] = false
  }
}

const pauseSource = async sourceName => {
  pausing.value[sourceName] = true
  try {
    await pipelineApi.pauseSource(sourceName)
    toast.success(`Paused ${sourceDisplayName(sourceName)}`, { duration: 5000 })
  } catch (error) {
    window.logService.error(`Failed to pause ${sourceName}:`, error)
    toast.error(`Failed to pause ${sourceDisplayName(sourceName)}`, { duration: Infinity })
  } finally {
    pausing.value[sourceName] = false
  }
}

const resumeSource = async sourceName => {
  resuming.value[sourceName] = true
  try {
    await pipelineApi.resumeSource(sourceName)
    toast.success(`Resumed ${sourceDisplayName(sourceName)}`, { duration: 5000 })
  } catch (error) {
    window.logService.error(`Failed to resume ${sourceName}:`, error)
    toast.error(`Failed to resume ${sourceDisplayName(sourceName)}`, { duration: Infinity })
  } finally {
    resuming.value[sourceName] = false
  }
}

const triggerableSources = computed(() =>
  dataSources.value.filter(
    s => s.status === 'idle' || s.status === 'failed' || s.status === 'completed'
  )
)

const triggerAll = async () => {
  triggeringAll.value = true
  try {
    await Promise.all(triggerableSources.value.map(source => triggerSource(source.source_name)))

    toast.success('All data sources triggered', { duration: 5000 })
  } catch (error) {
    window.logService.error('Failed to trigger all:', error)
    toast.error('Failed to trigger all data sources', { duration: Infinity })
  } finally {
    triggeringAll.value = false
  }
}

const pauseAll = async () => {
  const runningSrcs = sources.value.filter(s => s.status === 'running')
  await Promise.all(runningSrcs.map(source => pauseSource(source.source_name)))
}

const STALLED_AFTER_MS = 10 * 60 * 1000
// Ticks so relative times and "stalled" stay current without a WebSocket event; while the
// socket is down, the same tick polls so the page never shows a frozen status
const now = ref(Date.now())
const clock = setInterval(() => {
  now.value = Date.now()
  if (!wsConnected.value) loadSources()
}, 30_000)

// A running source whose progress row has not been written for 10 minutes is stalled.
// Without last_update_at (older backend) we cannot tell, so keep the plain status.
const isStalled = source =>
  source.status === 'running' &&
  !!source.last_update_at &&
  now.value - Date.parse(source.last_update_at) > STALLED_AFTER_MS

// A finished run older than this is flagged so admins see the data may be out of date
const STALE_AFTER_DAYS = 30
const isStale = source =>
  source.status !== 'running' &&
  !!source.completed_at &&
  now.value - Date.parse(source.completed_at) > STALE_AFTER_DAYS * 86_400_000

const formatTime = dateString => {
  if (!dateString) return 'N/A'
  const date = new Date(dateString)
  const diff = now.value - date // reactive clock, so "N min ago" keeps counting

  if (diff < 60000) {
    // Less than 1 minute
    return 'Just now'
  } else if (diff < 3600000) {
    // Less than 1 hour
    const minutes = Math.floor(diff / 60000)
    return `${minutes} min ago`
  } else if (diff < 86400000) {
    // Less than 1 day
    const hours = Math.floor(diff / 3600000)
    return `${hours} hours ago`
  } else {
    return date.toLocaleString()
  }
}

// Time left until an estimated completion; rounded up so it never promises too much
const formatRemaining = dateString => {
  const left = Date.parse(dateString) - now.value
  if (Number.isNaN(left)) return ''
  if (left <= 0) return 'Running longer than estimated'
  if (left < 60_000) return 'Under a minute left'
  const minutes = Math.ceil(left / 60_000)
  if (minutes < 60) return `About ${minutes} min left`
  return `About ${Math.floor(minutes / 60)} h ${minutes % 60} min left`
}

const showSourceDetails = source => {
  selectedSource.value = source
  showDetailsDialog.value = true
}

// WebSocket handlers
const handleProgressUpdate = data => {
  // Backend wraps single updates in an array for consistency
  const items = Array.isArray(data) ? data : [data]
  now.value = Date.now() // new data: relative times must not lag the 30 s tick
  for (const item of items) {
    const index = sources.value.findIndex(s => s.source_name === item.source_name)
    if (index > -1) {
      sources.value[index] = { ...sources.value[index], ...item }
    }
  }
}

const handleTaskStarted = data => {
  handleProgressUpdate(data)
  toast.info(`${data.source_name} started`, { duration: 5000 })
}

const handleTaskCompleted = data => {
  handleProgressUpdate(data)
  toast.success(`${data.source_name} completed`, { duration: 5000 })
}

const handleTaskFailed = data => {
  handleProgressUpdate(data)
  toast.error(`${data.source_name} failed`, { duration: Infinity })
}

const handleInitialStatus = data => {
  // Handle both array format and nested API response format
  if (Array.isArray(data)) {
    sources.value = data
  } else if (data?.data && Array.isArray(data.data)) {
    sources.value = data.data
  } else {
    window.logService.warn('Unexpected initial status format:', data)
  }
}

// Lifecycle
onMounted(() => {
  loadSources()

  // Connect to WebSocket for real-time updates
  connect()

  // Subscribe to WebSocket events
  unsubscribers.push(
    subscribe('progress_update', handleProgressUpdate),
    subscribe('task_started', handleTaskStarted),
    subscribe('task_completed', handleTaskCompleted),
    subscribe('task_failed', handleTaskFailed),
    subscribe('initial_status', handleInitialStatus)
  )
})

onUnmounted(() => {
  clearInterval(clock)
  // Unsubscribe from all WebSocket events
  unsubscribers.forEach(unsub => unsub())

  // Disconnect WebSocket
  disconnect(false)
})
</script>

<template>
  <div :class="PAGE_CONTAINER">
    <AdminHeader title="Data Pipeline" subtitle="Monitor and control data ingestion pipelines">
      <template #actions>
        <StatusBadge
          :status="wsConnected ? 'ok' : 'warning'"
          :label="wsConnected ? 'Live updates' : 'Polling every 30 s'"
          :tooltip="
            wsConnected
              ? 'Status updates arrive in real time'
              : 'The live connection is down; status refreshes every 30 seconds'
          "
        />
      </template>
    </AdminHeader>

    <!-- Summary Stats -->
    <div class="grid grid-cols-2 md:grid-cols-4 gap-3 mb-6">
      <AdminStatsCard title="Data Sources" :value="dataSources.length" :icon="Database" />
      <AdminStatsCard title="Running" :value="runningSources" :icon="CirclePlay" color="success" />
      <AdminStatsCard title="Completed" :value="completedSources" :icon="CircleCheck" />
      <AdminStatsCard title="Failed" :value="failedSources" :icon="CircleAlert" color="error" />
    </div>

    <!-- Quick Actions -->
    <Card class="mb-4">
      <CardContent class="p-4">
        <div class="flex flex-wrap gap-2">
          <Button
            size="sm"
            :disabled="triggeringAll || runningSources > 0 || triggerableSources.length === 0"
            @click="showRunAllDialog = true"
          >
            <Loader2 v-if="triggeringAll" class="size-4 mr-2 animate-spin" />
            <Play v-else class="size-4 mr-2" />
            Run All Data Sources
          </Button>
          <Button variant="outline" size="sm" :disabled="runningSources === 0" @click="pauseAll">
            <Pause class="size-4 mr-2" />
            Pause All
          </Button>
          <Button variant="outline" size="sm" :disabled="loading" @click="loadSources">
            <Loader2 v-if="loading" class="size-4 mr-2 animate-spin" />
            <RefreshCw v-else class="size-4 mr-2" />
            Refresh Status
          </Button>
        </div>
      </CardContent>
    </Card>

    <!-- Data Sources Grid -->
    <h2 class="text-lg font-semibold mb-4">Data Sources</h2>
    <DataState
      :loading="loading && !sources.length"
      :error="loadError"
      error-title="Could not load pipeline status"
      :empty="!dataSources.length"
      empty-message="No data sources are registered."
      class="mb-4"
      @retry="loadSources"
    >
      <template #loading>
        <div class="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4" aria-hidden="true">
          <div
            v-for="i in 6"
            :key="i"
            class="h-56 rounded-xl border bg-muted/50 motion-safe:animate-pulse"
          />
        </div>
      </template>
      <div class="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
        <Card
          v-for="source in dataSources"
          :key="source.source_name"
          data-testid="source-card"
          class="flex flex-col"
        >
          <CardHeader class="pb-2">
            <div class="flex items-center justify-between">
              <CardTitle class="text-sm">
                <SourceLabel :source="source.source_name" />
              </CardTitle>
              <StatusBadge
                v-if="isStalled(source)"
                status="stale"
                label="Stalled"
                :tooltip="`Stalled: last progress update ${formatTime(source.last_update_at)}`"
              />
              <StatusBadge v-else :status="source.status" />
            </div>
          </CardHeader>

          <CardContent class="flex-1">
            <!-- Progress Bar -->
            <div v-if="source.status === 'running'" class="mb-3">
              <div class="flex items-center justify-between mb-1">
                <span class="text-xs text-muted-foreground">
                  {{ source.current_operation || 'Processing...' }}
                </span>
                <span class="text-xs font-medium tabular-nums">
                  {{ Math.round(source.progress_percentage || 0) }}%
                </span>
              </div>
              <Progress :model-value="source.progress_percentage || 0" class="h-2" />
              <p v-if="isStalled(source)" class="text-xs text-danger mt-1">
                Stalled: last progress update {{ formatTime(source.last_update_at) }}
              </p>
            </div>

            <!-- Statistics -->
            <dl class="space-y-1.5 text-sm">
              <div class="flex items-center justify-between">
                <dt class="text-muted-foreground">Items processed</dt>
                <dd class="font-medium tabular-nums">
                  {{ (source.items_processed || 0).toLocaleString() }}
                </dd>
              </div>
              <div class="flex items-center justify-between">
                <dt class="text-muted-foreground">Added</dt>
                <dd class="font-medium tabular-nums">
                  {{ (source.items_added || 0).toLocaleString() }}
                </dd>
              </div>
              <div class="flex items-center justify-between">
                <dt class="text-muted-foreground">Updated</dt>
                <dd class="font-medium tabular-nums">
                  {{ (source.items_updated || 0).toLocaleString() }}
                </dd>
              </div>
              <div v-if="source.items_failed > 0" class="flex items-center justify-between">
                <dt class="flex items-center gap-1.5 text-danger">
                  <AlertTriangle class="size-4" aria-hidden="true" />
                  Failed
                </dt>
                <dd class="font-medium tabular-nums text-danger">
                  {{ source.items_failed.toLocaleString() }}
                </dd>
              </div>
            </dl>

            <!-- Timing Info -->
            <div v-if="source.started_at" class="mt-3 text-xs text-muted-foreground">
              <div v-if="source.status === 'running'">
                Started: {{ formatTime(source.started_at) }}
              </div>
              <div v-else-if="source.completed_at">
                Completed: {{ formatTime(source.completed_at) }}
                <span v-if="isStale(source)" class="font-medium text-warning">
                  · Stale (over {{ STALE_AFTER_DAYS }} days)
                </span>
              </div>
              <div v-if="source.estimated_completion && source.status === 'running'">
                {{ formatRemaining(source.estimated_completion) }}
              </div>
            </div>

            <!-- Error Message -->
            <Alert v-if="source.last_error" variant="destructive" class="mt-3">
              <AlertTriangle class="size-4" />
              <AlertDescription class="text-xs">{{ source.last_error }}</AlertDescription>
            </Alert>
          </CardContent>

          <!-- Actions -->
          <div class="flex items-center justify-between px-6 pb-4">
            <div>
              <Button
                v-if="
                  source.status === 'idle' ||
                  source.status === 'failed' ||
                  source.status === 'completed'
                "
                size="sm"
                variant="outline"
                :disabled="triggering[source.source_name]"
                @click="triggerSource(source.source_name)"
              >
                <Loader2 v-if="triggering[source.source_name]" class="size-4 mr-1 animate-spin" />
                <Play v-else class="size-4 mr-1" />
                Run
              </Button>

              <Button
                v-else-if="source.status === 'running'"
                size="sm"
                variant="outline"
                :disabled="pausing[source.source_name]"
                @click="pauseSource(source.source_name)"
              >
                <Loader2 v-if="pausing[source.source_name]" class="size-4 mr-1 animate-spin" />
                <Pause v-else class="size-4 mr-1" />
                Pause
              </Button>

              <Button
                v-else-if="source.status === 'paused'"
                size="sm"
                variant="outline"
                :disabled="resuming[source.source_name]"
                @click="resumeSource(source.source_name)"
              >
                <Loader2 v-if="resuming[source.source_name]" class="size-4 mr-1 animate-spin" />
                <Play v-else class="size-4 mr-1" />
                Resume
              </Button>
            </div>

            <Button
              :aria-label="`Details for ${source.source_name}`"
              variant="ghost"
              size="icon"
              class="h-8 w-8"
              @click="showSourceDetails(source)"
            >
              <Info class="size-4" aria-hidden="true" />
            </Button>
          </div>
        </Card>
      </div>
    </DataState>

    <!-- Hybrid Sources Section (manual upload sources like DiagnosticPanels, Literature) -->
    <div v-if="hybridSources.length > 0" class="mt-8">
      <h2 class="text-lg font-semibold mb-4">Upload Sources</h2>
      <div class="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
        <Card
          v-for="source in hybridSources"
          :key="source.source_name"
          class="flex flex-col border-dashed"
        >
          <CardHeader class="pb-2">
            <div class="flex items-center justify-between">
              <CardTitle class="text-sm">
                <SourceLabel :source="source.source_name" />
              </CardTitle>
              <Chip
                kind="neutral"
                label="Manual upload"
                :icon="Upload"
                tooltip="Data arrives by file upload (Hybrid Sources), not from the automated pipeline"
              />
            </div>
          </CardHeader>
          <CardContent class="flex-1 pt-2">
            <p class="text-xs text-muted-foreground">
              Upload files in
              <RouterLink
                to="/admin/hybrid-sources"
                class="text-primary underline-offset-4 hover:underline"
                >Hybrid Sources</RouterLink
              >. Not part of the automated pipeline.
            </p>
          </CardContent>
        </Card>
      </div>
    </div>

    <!-- Internal Processes Section -->
    <div v-if="internalProcesses.length > 0" class="mt-8">
      <h2 class="text-lg font-semibold mb-4">Internal Processes</h2>
      <div class="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
        <Card
          v-for="process in internalProcesses"
          :key="process.source_name"
          class="flex flex-col border-dashed"
        >
          <CardHeader class="pb-2">
            <div class="flex items-center justify-between">
              <CardTitle class="text-sm flex items-center gap-2">
                <Cog class="size-4 text-muted-foreground" aria-hidden="true" />
                {{ process.display_name || process.source_name }}
              </CardTitle>
              <StatusBadge :status="process.status" />
            </div>
          </CardHeader>

          <CardContent class="flex-1">
            <p class="text-sm text-muted-foreground mb-3">
              {{ process.description }}
            </p>

            <!-- Progress Bar -->
            <div v-if="process.status === 'running'" class="mb-3">
              <div class="flex items-center justify-between mb-1">
                <span class="text-xs text-muted-foreground">
                  {{ process.current_operation || 'Processing...' }}
                </span>
                <span class="text-xs font-medium tabular-nums">
                  {{ Math.round(process.progress_percentage || 0) }}%
                </span>
              </div>
              <Progress
                :model-value="process.progress_percentage || 0"
                :aria-label="`${process.display_name || process.source_name} progress`"
                class="h-2"
              />
              <!-- Announced at milestones (a source finished), not on every tick -->
              <span v-if="process.total_items" class="sr-only" role="status">
                {{ process.current_item }} of {{ process.total_items }} sources done
              </span>
              <p v-if="isStalled(process)" class="text-xs text-danger mt-1">
                Stalled: last progress update {{ formatTime(process.last_update_at) }}
              </p>
            </div>

            <!-- Timing Info -->
            <div v-if="process.started_at" class="text-xs text-muted-foreground">
              <div v-if="process.status === 'running'">
                Started: {{ formatTime(process.started_at) }} · last update
                {{ formatTime(process.last_update_at) }}
                <!-- From each source's last successful duration; absent without that history -->
                <div v-if="process.estimated_completion" class="font-medium text-foreground">
                  {{ formatRemaining(process.estimated_completion) }}
                </div>
              </div>
              <div v-else-if="process.completed_at">
                Completed: {{ formatTime(process.completed_at) }}
                <span v-if="isStale(process)" class="font-medium text-warning">
                  · Stale (over {{ STALE_AFTER_DAYS }} days)
                </span>
              </div>
            </div>

            <!-- Error Message -->
            <Alert v-if="process.last_error" variant="destructive" class="mt-3">
              <AlertTriangle class="size-4" />
              <AlertDescription class="text-xs">{{ process.last_error }}</AlertDescription>
            </Alert>
          </CardContent>

          <div class="flex items-center justify-end px-6 pb-4">
            <Button
              :aria-label="`Details for ${process.source_name}`"
              variant="ghost"
              size="icon"
              class="h-8 w-8"
              @click="showSourceDetails(process)"
            >
              <Info class="size-4" aria-hidden="true" />
            </Button>
          </div>
        </Card>
      </div>
    </div>

    <AlertDialog v-model:open="showRunAllDialog">
      <AlertDialogContent>
        <AlertDialogHeader>
          <AlertDialogTitle>
            Run {{ triggerableSources.length }} data source{{
              triggerableSources.length === 1 ? '' : 's'
            }}?
          </AlertDialogTitle>
          <AlertDialogDescription>
            This starts an update run for each of these sources:
            {{ triggerableSources.map(s => sourceDisplayName(s.source_name)).join(', ') }}. Runs
            continue in the background until they finish or are paused.
          </AlertDialogDescription>
        </AlertDialogHeader>
        <AlertDialogFooter>
          <AlertDialogCancel>Cancel</AlertDialogCancel>
          <AlertDialogAction @click="triggerAll">Run All</AlertDialogAction>
        </AlertDialogFooter>
      </AlertDialogContent>
    </AlertDialog>

    <!-- Source Details Dialog -->
    <Dialog v-model:open="showDetailsDialog">
      <DialogContent class="max-w-[700px]">
        <DialogHeader>
          <DialogTitle>{{ sourceDisplayName(selectedSource?.source_name) }} details</DialogTitle>
          <DialogDescription>Raw data for the selected source</DialogDescription>
        </DialogHeader>
        <div v-if="selectedSource" class="max-h-[400px] overflow-auto">
          <pre class="text-xs bg-muted p-4 rounded whitespace-pre-wrap break-words">{{
            JSON.stringify(selectedSource, null, 2)
          }}</pre>
        </div>
        <DialogFooter>
          <Button variant="outline" @click="showDetailsDialog = false">Close</Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  </div>
</template>
