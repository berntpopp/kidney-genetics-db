<script setup>
/**
 * Pipeline Control View
 * Real-time monitoring and control of data pipelines
 */

import { ref, computed, onMounted, onUnmounted } from 'vue'
import { useWebSocket } from '@/services/websocket'
import AdminHeader from '@/components/admin/AdminHeader.vue'
import AdminStatsCard from '@/components/admin/AdminStatsCard.vue'
import * as pipelineApi from '@/api/admin/pipeline'
import { ADMIN_BREADCRUMBS } from '@/utils/adminBreadcrumbs'
import { toast } from 'vue-sonner'
import {
  AlertTriangle,
  BookOpen,
  BriefcaseMedical,
  Cog,
  Database,
  Dna,
  FileText,
  Hash,
  Hospital,
  Info,
  LayoutList,
  Loader2,
  Pause,
  Play,
  Plus,
  RefreshCw,
  Users,
  Wifi,
  WifiOff
} from 'lucide-vue-next'
import { resolveMdiIcon } from '@/utils/icons'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { Button } from '@/components/ui/button'
import { Badge } from '@/components/ui/badge'
import { Progress } from '@/components/ui/progress'
import { Alert, AlertDescription } from '@/components/ui/alert'
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
const triggering = ref({})
const pausing = ref({})
const resuming = ref({})
const triggeringAll = ref(false)
const showDetailsDialog = ref(false)
const selectedSource = ref(null)

// WebSocket subscriptions
const unsubscribers = []

// Computed
const dataSources = computed(() =>
  sources.value.filter(s => s.category === 'data_source' || s.category === 'hybrid_source')
)

const internalProcesses = computed(() =>
  sources.value.filter(s => s.category === 'internal_process')
)

const runningSources = computed(() => dataSources.value.filter(s => s.status === 'running').length)

const completedSources = computed(
  () => dataSources.value.filter(s => s.status === 'completed').length
)

const failedSources = computed(() => dataSources.value.filter(s => s.status === 'failed').length)

// Methods
const loadSources = async () => {
  loading.value = true
  try {
    const response = await pipelineApi.getAllStatus()
    // API returns { data: [...], meta: {...} } structure
    sources.value = response.data?.data || []
  } catch (error) {
    window.logService.error('Failed to load sources:', error)
    toast.error('Failed to load pipeline status', { duration: Infinity })
  } finally {
    loading.value = false
  }
}

const triggerSource = async sourceName => {
  triggering.value[sourceName] = true
  try {
    await pipelineApi.triggerUpdate(sourceName)
    toast.success(`Started ${sourceName}`, { duration: 5000 })
  } catch (error) {
    window.logService.error(`Failed to trigger ${sourceName}:`, error)
    toast.error(`Failed to start ${sourceName}`, { duration: Infinity })
  } finally {
    triggering.value[sourceName] = false
  }
}

const pauseSource = async sourceName => {
  pausing.value[sourceName] = true
  try {
    await pipelineApi.pauseSource(sourceName)
    toast.success(`Paused ${sourceName}`, { duration: 5000 })
  } catch (error) {
    window.logService.error(`Failed to pause ${sourceName}:`, error)
    toast.error(`Failed to pause ${sourceName}`, { duration: Infinity })
  } finally {
    pausing.value[sourceName] = false
  }
}

const resumeSource = async sourceName => {
  resuming.value[sourceName] = true
  try {
    await pipelineApi.resumeSource(sourceName)
    toast.success(`Resumed ${sourceName}`, { duration: 5000 })
  } catch (error) {
    window.logService.error(`Failed to resume ${sourceName}:`, error)
    toast.error(`Failed to resume ${sourceName}`, { duration: Infinity })
  } finally {
    resuming.value[sourceName] = false
  }
}

const triggerAll = async () => {
  triggeringAll.value = true
  try {
    const triggerable = dataSources.value.filter(
      s => s.status === 'idle' || s.status === 'failed' || s.status === 'completed'
    )

    await Promise.all(triggerable.map(source => triggerSource(source.source_name)))

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

const getSourceIcon = source => {
  switch (source.source_name) {
    case 'PanelApp':
      return LayoutList
    case 'HPO':
      return Dna
    case 'ClinGen':
      return Hospital
    case 'GenCC':
      return Users
    case 'PubTator':
      return FileText
    case 'DiagnosticPanels':
      return BriefcaseMedical
    case 'Literature':
      return BookOpen
    default:
      return Database
  }
}

const getStatusVariant = status => {
  switch (status) {
    case 'running':
      return 'default'
    case 'completed':
      return 'secondary'
    case 'failed':
      return 'destructive'
    case 'paused':
      return 'outline'
    default:
      return 'secondary'
  }
}

const formatTime = dateString => {
  if (!dateString) return 'N/A'
  const date = new Date(dateString)
  const now = new Date()
  const diff = now - date

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

const showSourceDetails = source => {
  selectedSource.value = source
  showDetailsDialog.value = true
}

// WebSocket handlers
const handleProgressUpdate = data => {
  const index = sources.value.findIndex(s => s.source_name === data.source_name)
  if (index > -1) {
    sources.value[index] = { ...sources.value[index], ...data }
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
  // Unsubscribe from all WebSocket events
  unsubscribers.forEach(unsub => unsub())

  // Disconnect WebSocket
  disconnect(false)
})
</script>

<template>
  <div class="container mx-auto px-4 py-6">
    <AdminHeader
      title="Data Pipeline Control"
      subtitle="Monitor and control data ingestion pipelines"
      icon="mdi-pipe"
      icon-color="green"
      :breadcrumbs="ADMIN_BREADCRUMBS.pipeline"
    >
      <template #actions>
        <Badge :variant="wsConnected ? 'default' : 'destructive'" class="flex items-center gap-1">
          <component :is="wsConnected ? Wifi : WifiOff" class="size-3" />
          {{ wsConnected ? 'Live' : 'Offline' }}
        </Badge>
      </template>
    </AdminHeader>

    <!-- Summary Stats -->
    <div class="grid grid-cols-1 sm:grid-cols-2 md:grid-cols-4 gap-4 mb-6">
      <AdminStatsCard
        title="Data Sources"
        :value="dataSources.length"
        icon="mdi-database"
        color="info"
      />
      <AdminStatsCard
        title="Running"
        :value="runningSources"
        icon="mdi-play-circle"
        color="success"
      />
      <AdminStatsCard
        title="Completed"
        :value="completedSources"
        icon="mdi-check-circle"
        color="primary"
      />
      <AdminStatsCard title="Failed" :value="failedSources" icon="mdi-alert-circle" color="error" />
    </div>

    <!-- Quick Actions -->
    <Card class="mb-4">
      <CardContent class="p-4">
        <div class="flex flex-wrap gap-2">
          <Button size="sm" :disabled="triggeringAll || runningSources > 0" @click="triggerAll">
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
    <h3 class="text-lg font-semibold mb-4">Data Sources</h3>
    <div class="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
      <Card v-for="source in dataSources" :key="source.source_name" class="flex flex-col">
        <CardHeader class="pb-2">
          <div class="flex items-center justify-between">
            <CardTitle class="text-sm flex items-center gap-2">
              <component :is="getSourceIcon(source)" class="size-5" />
              {{ source.source_name }}
            </CardTitle>
            <Badge :variant="getStatusVariant(source.status)">
              {{ source.status }}
            </Badge>
          </div>
        </CardHeader>

        <CardContent class="flex-1">
          <!-- Progress Bar -->
          <div v-if="source.status === 'running'" class="mb-3">
            <div class="flex items-center justify-between mb-1">
              <span class="text-xs text-muted-foreground">
                {{ source.current_operation || 'Processing...' }}
              </span>
              <span class="text-xs font-medium">
                {{ Math.round(source.progress_percentage || 0) }}%
              </span>
            </div>
            <Progress :model-value="source.progress_percentage || 0" class="h-2" />
          </div>

          <!-- Statistics -->
          <div class="space-y-2 text-sm">
            <div class="flex items-center justify-between">
              <div class="flex items-center gap-2 text-muted-foreground">
                <Hash class="size-4" />
                <span>Items Processed</span>
              </div>
              <span class="font-medium">{{ source.items_processed || 0 }}</span>
            </div>
            <div class="flex items-center justify-between">
              <div class="flex items-center gap-2 text-green-600 dark:text-green-400">
                <Plus class="size-4" />
                <span>Added</span>
              </div>
              <span class="font-medium text-green-600 dark:text-green-400">
                {{ source.items_added || 0 }}
              </span>
            </div>
            <div class="flex items-center justify-between">
              <div class="flex items-center gap-2 text-blue-600 dark:text-blue-400">
                <RefreshCw class="size-4" />
                <span>Updated</span>
              </div>
              <span class="font-medium text-blue-600 dark:text-blue-400">
                {{ source.items_updated || 0 }}
              </span>
            </div>
            <div v-if="source.items_failed > 0" class="flex items-center justify-between">
              <div class="flex items-center gap-2 text-destructive">
                <AlertTriangle class="size-4" />
                <span>Failed</span>
              </div>
              <span class="font-medium text-destructive">
                {{ source.items_failed || 0 }}
              </span>
            </div>
          </div>

          <!-- Timing Info -->
          <div v-if="source.started_at" class="mt-3 text-xs text-muted-foreground">
            <div v-if="source.status === 'running'">
              Started: {{ formatTime(source.started_at) }}
            </div>
            <div v-else-if="source.completed_at">
              Completed: {{ formatTime(source.completed_at) }}
            </div>
            <div v-if="source.estimated_completion && source.status === 'running'">
              ETA: {{ formatTime(source.estimated_completion) }}
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

          <Button variant="ghost" size="icon" class="h-8 w-8" @click="showSourceDetails(source)">
            <Info class="size-4" />
          </Button>
        </div>
      </Card>
    </div>

    <!-- Internal Processes Section -->
    <div v-if="internalProcesses.length > 0" class="mt-8">
      <h3 class="text-lg font-semibold mb-4">Internal Processes</h3>
      <div class="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
        <Card
          v-for="process in internalProcesses"
          :key="process.source_name"
          class="flex flex-col border-dashed"
        >
          <CardHeader class="pb-2">
            <div class="flex items-center justify-between">
              <CardTitle class="text-sm flex items-center gap-2">
                <component :is="resolveMdiIcon(process.icon || 'mdi-cog') || Cog" class="size-5" />
                {{ process.display_name || process.source_name }}
              </CardTitle>
              <Badge :variant="getStatusVariant(process.status)">
                {{ process.status }}
              </Badge>
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
                <span class="text-xs font-medium">
                  {{ Math.round(process.progress_percentage || 0) }}%
                </span>
              </div>
              <Progress :model-value="process.progress_percentage || 0" class="h-2" />
            </div>

            <!-- Timing Info -->
            <div v-if="process.started_at" class="text-xs text-muted-foreground">
              <div v-if="process.status === 'running'">
                Started: {{ formatTime(process.started_at) }}
              </div>
              <div v-else-if="process.completed_at">
                Completed: {{ formatTime(process.completed_at) }}
              </div>
            </div>

            <!-- Error Message -->
            <Alert v-if="process.last_error" variant="destructive" class="mt-3">
              <AlertTriangle class="size-4" />
              <AlertDescription class="text-xs">{{ process.last_error }}</AlertDescription>
            </Alert>
          </CardContent>

          <div class="flex items-center justify-end px-6 pb-4">
            <Button variant="ghost" size="icon" class="h-8 w-8" @click="showSourceDetails(process)">
              <Info class="size-4" />
            </Button>
          </div>
        </Card>
      </div>
    </div>

    <!-- Source Details Dialog -->
    <Dialog v-model:open="showDetailsDialog">
      <DialogContent class="max-w-[700px]">
        <DialogHeader>
          <DialogTitle>{{ selectedSource?.source_name }} Details</DialogTitle>
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
