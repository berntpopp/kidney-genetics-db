<template>
  <v-container>
    <AdminHeader
      title="Data Pipeline Control"
      subtitle="Monitor and control data ingestion pipelines"
      icon="mdi-pipe"
      icon-color="green"
      :breadcrumbs="ADMIN_BREADCRUMBS.pipeline"
    >
      <template #actions>
        <v-chip :color="wsConnected ? 'success' : 'error'" size="small" label>
          <component :is="wsConnected ? Wifi : WifiOff" class="size-3 mr-1" />
          {{ wsConnected ? 'Live' : 'Offline' }}
        </v-chip>
      </template>
    </AdminHeader>

    <!-- Summary Stats -->
    <v-row class="mb-6">
      <v-col cols="12" sm="6" md="3">
        <AdminStatsCard
          title="Data Sources"
          :value="dataSources.length"
          icon="mdi-database"
          color="info"
        />
      </v-col>
      <v-col cols="12" sm="6" md="3">
        <AdminStatsCard
          title="Running"
          :value="runningSources"
          icon="mdi-play-circle"
          color="success"
        />
      </v-col>
      <v-col cols="12" sm="6" md="3">
        <AdminStatsCard
          title="Completed"
          :value="completedSources"
          icon="mdi-check-circle"
          color="primary"
        />
      </v-col>
      <v-col cols="12" sm="6" md="3">
        <AdminStatsCard
          title="Failed"
          :value="failedSources"
          icon="mdi-alert-circle"
          color="error"
        />
      </v-col>
    </v-row>

    <!-- Quick Actions -->
    <v-card class="mb-4 pa-4">
      <div class="d-flex flex-wrap gap-2">
        <v-btn
          color="success"
          size="small"
          prepend-icon="mdi-play"
          :loading="triggeringAll"
          :disabled="runningSources > 0"
          @click="triggerAll"
        >
          Run All Data Sources
        </v-btn>
        <v-btn
          color="warning"
          size="small"
          prepend-icon="mdi-pause"
          :disabled="runningSources === 0"
          @click="pauseAll"
        >
          Pause All
        </v-btn>
        <v-btn
          color="info"
          size="small"
          prepend-icon="mdi-refresh"
          :loading="loading"
          @click="loadSources"
        >
          Refresh Status
        </v-btn>
      </div>
    </v-card>

    <!-- Data Sources Grid -->
    <h3 class="text-h5 mb-4">Data Sources</h3>
    <v-row>
      <v-col v-for="source in dataSources" :key="source.source_name" cols="12" md="6" lg="4">
        <v-card class="h-100">
          <v-card-title class="d-flex align-center">
            <component :is="getSourceIcon(source)" class="size-5 mr-2" />
            {{ source.source_name }}
            <v-spacer />
            <v-chip :color="getStatusColor(source.status)" size="small" label>
              {{ source.status }}
            </v-chip>
          </v-card-title>

          <v-card-text>
            <!-- Progress Bar -->
            <div v-if="source.status === 'running'" class="mb-3">
              <v-progress-linear
                :model-value="source.progress_percentage || 0"
                :color="getStatusColor(source.status)"
                height="20"
                rounded
              >
                <template #default>
                  <strong>{{ Math.round(source.progress_percentage || 0) }}%</strong>
                </template>
              </v-progress-linear>
              <p class="text-caption mt-1">
                {{ source.current_operation || 'Processing...' }}
              </p>
            </div>

            <!-- Statistics -->
            <v-list density="compact" class="pa-0">
              <v-list-item class="px-0">
                <template #prepend>
                  <Hash class="size-4" />
                </template>
                <v-list-item-title>Items Processed</v-list-item-title>
                <template #append>
                  <span class="font-weight-medium">
                    {{ source.items_processed || 0 }}
                  </span>
                </template>
              </v-list-item>

              <v-list-item class="px-0">
                <template #prepend>
                  <Plus class="size-4 text-green-600 dark:text-green-400" />
                </template>
                <v-list-item-title>Added</v-list-item-title>
                <template #append>
                  <span class="font-weight-medium text-success">
                    {{ source.items_added || 0 }}
                  </span>
                </template>
              </v-list-item>

              <v-list-item class="px-0">
                <template #prepend>
                  <RefreshCw class="size-4 text-blue-600 dark:text-blue-400" />
                </template>
                <v-list-item-title>Updated</v-list-item-title>
                <template #append>
                  <span class="font-weight-medium text-info">
                    {{ source.items_updated || 0 }}
                  </span>
                </template>
              </v-list-item>

              <v-list-item v-if="source.items_failed > 0" class="px-0">
                <template #prepend>
                  <AlertTriangle class="size-4 text-destructive" />
                </template>
                <v-list-item-title>Failed</v-list-item-title>
                <template #append>
                  <span class="font-weight-medium text-error">
                    {{ source.items_failed || 0 }}
                  </span>
                </template>
              </v-list-item>
            </v-list>

            <!-- Timing Info -->
            <div v-if="source.started_at" class="mt-3 text-caption">
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
            <v-alert v-if="source.last_error" type="error" density="compact" class="mt-3">
              {{ source.last_error }}
            </v-alert>
          </v-card-text>

          <v-card-actions>
            <v-btn
              v-if="
                source.status === 'idle' ||
                source.status === 'failed' ||
                source.status === 'completed'
              "
              color="primary"
              size="small"
              variant="tonal"
              :loading="triggering[source.source_name]"
              @click="triggerSource(source.source_name)"
            >
              <Play class="size-5 mr-1" />
              Run
            </v-btn>

            <v-btn
              v-else-if="source.status === 'running'"
              color="warning"
              size="small"
              variant="tonal"
              :loading="pausing[source.source_name]"
              @click="pauseSource(source.source_name)"
            >
              <Pause class="size-5 mr-1" />
              Pause
            </v-btn>

            <v-btn
              v-else-if="source.status === 'paused'"
              color="success"
              size="small"
              variant="tonal"
              :loading="resuming[source.source_name]"
              @click="resumeSource(source.source_name)"
            >
              <Play class="size-5 mr-1" />
              Resume
            </v-btn>

            <v-spacer />

            <v-btn
              icon="mdi-information"
              size="small"
              variant="text"
              @click="showSourceDetails(source)"
            />
          </v-card-actions>
        </v-card>
      </v-col>
    </v-row>

    <!-- Internal Processes Section -->
    <div v-if="internalProcesses.length > 0" class="mt-8">
      <h3 class="text-h5 mb-4">Internal Processes</h3>
      <v-row>
        <v-col
          v-for="process in internalProcesses"
          :key="process.source_name"
          cols="12"
          md="6"
          lg="4"
        >
          <v-card class="h-100" variant="outlined">
            <v-card-title class="d-flex align-center">
              <component
                :is="resolveMdiIcon(process.icon || 'mdi-cog') || Cog"
                class="size-5 mr-2"
              />
              {{ process.display_name || process.source_name }}
              <v-spacer />
              <v-chip :color="getStatusColor(process.status)" size="small" label>
                {{ process.status }}
              </v-chip>
            </v-card-title>

            <v-card-text>
              <p class="text-body-2 text-medium-emphasis mb-3">
                {{ process.description }}
              </p>

              <!-- Progress Bar -->
              <div v-if="process.status === 'running'" class="mb-3">
                <v-progress-linear
                  :model-value="process.progress_percentage || 0"
                  :color="getStatusColor(process.status)"
                  height="20"
                  rounded
                >
                  <template #default>
                    <strong>{{ Math.round(process.progress_percentage || 0) }}%</strong>
                  </template>
                </v-progress-linear>
                <p class="text-caption mt-1">
                  {{ process.current_operation || 'Processing...' }}
                </p>
              </div>

              <!-- Timing Info -->
              <div v-if="process.started_at" class="text-caption">
                <div v-if="process.status === 'running'">
                  Started: {{ formatTime(process.started_at) }}
                </div>
                <div v-else-if="process.completed_at">
                  Completed: {{ formatTime(process.completed_at) }}
                </div>
              </div>

              <!-- Error Message -->
              <v-alert v-if="process.last_error" type="error" density="compact" class="mt-3">
                {{ process.last_error }}
              </v-alert>
            </v-card-text>

            <v-card-actions>
              <v-spacer />
              <v-btn
                icon="mdi-information"
                size="small"
                variant="text"
                @click="showSourceDetails(process)"
              />
            </v-card-actions>
          </v-card>
        </v-col>
      </v-row>
    </div>

    <!-- Source Details Dialog -->
    <v-dialog v-model="showDetailsDialog" max-width="800">
      <v-card v-if="selectedSource">
        <v-card-title> {{ selectedSource.source_name }} Details </v-card-title>
        <v-card-text>
          <pre>{{ JSON.stringify(selectedSource, null, 2) }}</pre>
        </v-card-text>
        <v-card-actions>
          <v-spacer />
          <v-btn variant="text" @click="showDetailsDialog = false">Close</v-btn>
        </v-card-actions>
      </v-card>
    </v-dialog>
  </v-container>
</template>

<script setup>
/**
 * Pipeline Control View
 * Real-time monitoring and control of data pipelines
 */

import { ref, computed, onMounted, onUnmounted } from 'vue'
// import { useAuthStore } from '@/stores/auth'
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
  LayoutList,
  Pause,
  Play,
  Plus,
  RefreshCw,
  Users,
  Wifi,
  WifiOff
} from 'lucide-vue-next'
import { resolveMdiIcon } from '@/utils/icons'

// const authStore = useAuthStore()
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

const getStatusColor = status => {
  switch (status) {
    case 'running':
      return 'success'
    case 'completed':
      return 'primary'
    case 'failed':
      return 'error'
    case 'paused':
      return 'warning'
    default:
      return 'grey'
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

<style scoped>
.gap-2 {
  gap: 0.5rem;
}
</style>
