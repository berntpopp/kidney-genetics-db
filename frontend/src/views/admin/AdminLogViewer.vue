<template>
  <v-container fluid class="pa-4">
    <AdminHeader title="System Logs" subtitle="View and analyze system logs" back-route="/admin" />

    <!-- Stats Overview -->
    <v-row class="mb-6">
      <v-col cols="12" sm="6" md="3">
        <AdminStatsCard
          title="Total Logs"
          :value="stats.totalLogs"
          :loading="statsLoading"
          icon="mdi-file-document-multiple"
          color="info"
        />
      </v-col>
      <v-col cols="12" sm="6" md="3">
        <AdminStatsCard
          title="Errors (24h)"
          :value="stats.errorCount"
          :loading="statsLoading"
          icon="mdi-alert-circle"
          color="error"
        />
      </v-col>
      <v-col cols="12" sm="6" md="3">
        <AdminStatsCard
          title="Warnings (24h)"
          :value="stats.warningCount"
          :loading="statsLoading"
          icon="mdi-alert"
          color="warning"
        />
      </v-col>
      <v-col cols="12" sm="6" md="3">
        <AdminStatsCard
          title="Storage Used"
          :value="stats.storageSize"
          :loading="statsLoading"
          icon="mdi-database"
          color="purple"
        />
      </v-col>
    </v-row>

    <!-- Filters -->
    <v-card class="mb-4">
      <v-card-text>
        <v-row>
          <v-col cols="12" md="3">
            <v-select
              v-model="filters.level"
              label="Log Level"
              :items="logLevels"
              density="compact"
              variant="outlined"
              clearable
              hide-details
            />
          </v-col>
          <v-col cols="12" md="3">
            <v-text-field
              v-model="filters.source"
              label="Source Module"
              density="compact"
              variant="outlined"
              clearable
              hide-details
            />
          </v-col>
          <v-col cols="12" md="3">
            <v-text-field
              v-model="filters.requestId"
              label="Request ID"
              density="compact"
              variant="outlined"
              clearable
              hide-details
            />
          </v-col>
          <v-col cols="12" md="3">
            <v-select
              v-model="filters.timeRange"
              label="Time Range"
              :items="timeRanges"
              density="compact"
              variant="outlined"
              hide-details
            />
          </v-col>
        </v-row>
        <v-row class="mt-3">
          <v-col cols="12" md="6">
            <v-text-field
              v-model="searchQuery"
              label="Search logs..."
              prepend-inner-icon="mdi-magnify"
              density="compact"
              variant="outlined"
              clearable
              hide-details
              @keyup.enter="loadLogs"
            />
          </v-col>
          <v-col cols="12" md="6" class="text-right">
            <v-btn
              color="primary"
              size="small"
              prepend-icon="mdi-filter"
              :loading="loading"
              class="mr-2"
              @click="loadLogs"
            >
              Apply Filters
            </v-btn>
            <v-btn
              color="warning"
              size="small"
              prepend-icon="mdi-filter-off"
              variant="outlined"
              class="mr-2"
              @click="clearFilters"
            >
              Clear
            </v-btn>
            <v-btn
              color="success"
              size="small"
              prepend-icon="mdi-download"
              :loading="exporting"
              @click="exportLogs"
            >
              Export
            </v-btn>
          </v-col>
        </v-row>
      </v-card-text>
    </v-card>

    <!-- Logs Table -->
    <v-card>
      <v-data-table
        :headers="headers"
        :items="logs"
        :loading="loading"
        :items-per-page="itemsPerPage"
        :server-items-length="totalLogs"
        density="compact"
        hover
        @update:options="onOptionsUpdate"
      >
        <!-- Timestamp column -->
        <template #item.timestamp="{ item }">
          <span class="text-caption">
            {{ formatTimestamp(item.timestamp) }}
          </span>
        </template>

        <!-- Level column -->
        <template #item.level="{ item }">
          <v-chip :color="getLevelColor(item.level)" size="small" label>
            {{ item.level }}
          </v-chip>
        </template>

        <!-- Source column -->
        <template #item.source="{ item }">
          <code class="text-caption">{{ item.source }}</code>
        </template>

        <!-- Message column -->
        <template #item.message="{ item }">
          <div class="text-truncate" style="max-width: 400px" :title="item.message">
            {{ item.message }}
          </div>
        </template>

        <!-- Actions column -->
        <template #item.actions="{ item }">
          <v-btn
            icon="mdi-eye"
            size="x-small"
            variant="text"
            title="View details"
            @click="showLogDetails(item)"
          />
          <v-btn
            v-if="item.request_id"
            icon="mdi-filter-variant"
            size="x-small"
            variant="text"
            title="Filter by request ID"
            @click="filterByRequestId(item.request_id)"
          />
        </template>
      </v-data-table>
    </v-card>

    <!-- Log Details Dialog -->
    <v-dialog v-model="showDetailsDialog" max-width="800">
      <v-card v-if="selectedLog">
        <v-card-title>
          Log Entry Details
          <v-spacer />
          <v-btn icon="mdi-close" variant="text" @click="showDetailsDialog = false" />
        </v-card-title>

        <v-card-text>
          <v-list density="compact">
            <v-list-item>
              <v-list-item-title>Timestamp</v-list-item-title>
              <v-list-item-subtitle>
                {{ formatTimestamp(selectedLog.timestamp, true) }}
              </v-list-item-subtitle>
            </v-list-item>

            <v-list-item>
              <v-list-item-title>Level</v-list-item-title>
              <v-list-item-subtitle>
                <v-chip :color="getLevelColor(selectedLog.level)" size="small" label>
                  {{ selectedLog.level }}
                </v-chip>
              </v-list-item-subtitle>
            </v-list-item>

            <v-list-item>
              <v-list-item-title>Source</v-list-item-title>
              <v-list-item-subtitle>
                <code>{{ selectedLog.source }}</code>
              </v-list-item-subtitle>
            </v-list-item>

            <v-list-item>
              <v-list-item-title>Message</v-list-item-title>
              <v-list-item-subtitle class="text-wrap">
                {{ selectedLog.message }}
              </v-list-item-subtitle>
            </v-list-item>

            <v-list-item v-if="selectedLog.request_id">
              <v-list-item-title>Request ID</v-list-item-title>
              <v-list-item-subtitle>
                <code>{{ selectedLog.request_id }}</code>
                <v-btn
                  icon="mdi-content-copy"
                  size="x-small"
                  variant="text"
                  @click="copyToClipboard(selectedLog.request_id)"
                />
              </v-list-item-subtitle>
            </v-list-item>

            <v-list-item v-if="selectedLog.user_id">
              <v-list-item-title>User ID</v-list-item-title>
              <v-list-item-subtitle>
                {{ selectedLog.user_id }}
              </v-list-item-subtitle>
            </v-list-item>

            <v-list-item v-if="selectedLog.extra_data">
              <v-list-item-title>Extra Data</v-list-item-title>
              <v-list-item-subtitle>
                <pre class="text-caption">{{
                  JSON.stringify(selectedLog.extra_data, null, 2)
                }}</pre>
              </v-list-item-subtitle>
            </v-list-item>
          </v-list>
        </v-card-text>

        <v-card-actions>
          <v-spacer />
          <v-btn variant="text" @click="showDetailsDialog = false">Close</v-btn>
        </v-card-actions>
      </v-card>
    </v-dialog>

    <!-- Cleanup Dialog -->
    <v-dialog v-model="showCleanupDialog" max-width="400">
      <v-card>
        <v-card-title>Clean Up Old Logs</v-card-title>
        <v-card-text>
          <v-text-field
            v-model.number="cleanupDays"
            label="Delete logs older than (days)"
            type="number"
            min="1"
            max="365"
            density="compact"
            variant="outlined"
          />
          <v-alert type="warning" density="compact" class="mt-2">
            This will permanently delete all logs older than {{ cleanupDays }} days.
          </v-alert>
        </v-card-text>
        <v-card-actions>
          <v-spacer />
          <v-btn variant="text" @click="showCleanupDialog = false">Cancel</v-btn>
          <v-btn color="error" variant="flat" :loading="cleaning" @click="executeCleanup">
            Delete Logs
          </v-btn>
        </v-card-actions>
      </v-card>
    </v-dialog>

    <!-- Actions FAB -->
    <v-btn
      color="warning"
      icon="mdi-broom"
      position="fixed"
      location="bottom right"
      size="large"
      class="mb-4 mr-4"
      elevation="4"
      @click="showCleanupDialog = true"
    />

    <!-- Snackbar -->
    <v-snackbar v-model="snackbar" :color="snackbarColor" :timeout="3000" location="top">
      {{ snackbarText }}
    </v-snackbar>
  </v-container>
</template>

<script setup>
/**
 * System Log Viewer
 * Complete log management interface with filtering, search, and export
 */

import { ref, computed, onMounted, watch } from 'vue'
import { useAuthStore } from '@/stores/auth'
import AdminHeader from '@/components/admin/AdminHeader.vue'
import AdminStatsCard from '@/components/admin/AdminStatsCard.vue'
import * as logsApi from '@/api/admin/logs'

const authStore = useAuthStore()

// State
const logs = ref([])
const loading = ref(false)
const exporting = ref(false)
const cleaning = ref(false)
const statsLoading = ref(false)
const showDetailsDialog = ref(false)
const showCleanupDialog = ref(false)
const selectedLog = ref(null)
const cleanupDays = ref(30)

// Pagination
const itemsPerPage = ref(25)
const currentPage = ref(1)
const totalLogs = ref(0)

// Filters
const filters = ref({
  level: null,
  source: '',
  requestId: '',
  timeRange: '24h'
})
const searchQuery = ref('')

// Stats
const stats = ref({
  totalLogs: 0,
  errorCount: 0,
  warningCount: 0,
  storageSize: '0 MB'
})

// Snackbar
const snackbar = ref(false)
const snackbarText = ref('')
const snackbarColor = ref('success')

// Table configuration
const headers = [
  { title: 'Timestamp', key: 'timestamp', width: '180px' },
  { title: 'Level', key: 'level', width: '100px' },
  { title: 'Source', key: 'source', width: '200px' },
  { title: 'Message', key: 'message' },
  { title: 'Actions', key: 'actions', sortable: false, width: '100px', align: 'center' }
]

const logLevels = ['INFO', 'WARNING', 'ERROR', 'DEBUG']

const timeRanges = [
  { title: 'Last Hour', value: '1h' },
  { title: 'Last 24 Hours', value: '24h' },
  { title: 'Last 7 Days', value: '7d' },
  { title: 'Last 30 Days', value: '30d' },
  { title: 'All Time', value: 'all' }
]

// Computed
const queryParams = computed(() => {
  const params = {
    limit: itemsPerPage.value,
    offset: (currentPage.value - 1) * itemsPerPage.value
  }

  if (filters.value.level) {
    params.level = filters.value.level
  }

  if (filters.value.source) {
    params.source = filters.value.source
  }

  if (filters.value.requestId) {
    params.request_id = filters.value.requestId
  }

  // Calculate time range
  if (filters.value.timeRange && filters.value.timeRange !== 'all') {
    const now = new Date()
    const start = new Date()

    switch (filters.value.timeRange) {
      case '1h':
        start.setHours(now.getHours() - 1)
        break
      case '24h':
        start.setDate(now.getDate() - 1)
        break
      case '7d':
        start.setDate(now.getDate() - 7)
        break
      case '30d':
        start.setDate(now.getDate() - 30)
        break
    }

    params.start_time = start.toISOString()
    params.end_time = now.toISOString()
  }

  return params
})

// Methods
const loadLogs = async () => {
  loading.value = true
  try {
    const response = await logsApi.queryLogs(queryParams.value)
    const data = response.data || response

    logs.value = data.logs || []
    totalLogs.value = data.pagination?.total || 0
  } catch (error) {
    console.error('Failed to load logs:', error)
    showSnackbar('Failed to load logs', 'error')
  } finally {
    loading.value = false
  }
}

const loadStats = async () => {
  statsLoading.value = true
  try {
    const response = await logsApi.getLogStatistics(24)
    const data = response.data || response

    stats.value = {
      totalLogs: data.storage?.total_rows || 0,
      errorCount: data.level_distribution?.find(l => l.level === 'ERROR')?.count || 0,
      warningCount: data.level_distribution?.find(l => l.level === 'WARNING')?.count || 0,
      storageSize: data.storage?.table_size || '0 MB'
    }
  } catch (error) {
    console.error('Failed to load log statistics:', error)
  } finally {
    statsLoading.value = false
  }
}

const clearFilters = () => {
  filters.value = {
    level: null,
    source: '',
    requestId: '',
    timeRange: '24h'
  }
  searchQuery.value = ''
  currentPage.value = 1
  loadLogs()
}

const filterByRequestId = requestId => {
  filters.value.requestId = requestId
  currentPage.value = 1
  loadLogs()
}

const showLogDetails = log => {
  selectedLog.value = log
  showDetailsDialog.value = true
}

const exportLogs = async () => {
  exporting.value = true
  try {
    const data = await logsApi.exportLogs(queryParams.value)

    // Create and download JSON file
    const blob = new Blob([JSON.stringify(data, null, 2)], {
      type: 'application/json'
    })
    const url = URL.createObjectURL(blob)
    const a = document.createElement('a')
    a.href = url
    a.download = `logs-${new Date().toISOString().split('T')[0]}.json`
    a.click()
    URL.revokeObjectURL(url)

    showSnackbar('Logs exported successfully', 'success')
  } catch (error) {
    console.error('Failed to export logs:', error)
    showSnackbar('Failed to export logs', 'error')
  } finally {
    exporting.value = false
  }
}

const executeCleanup = async () => {
  cleaning.value = true
  try {
    const response = await logsApi.cleanupLogs(cleanupDays.value)
    const data = response.data || response

    showSnackbar(`Deleted ${data.logs_deleted || 0} log entries`, 'success')
    showCleanupDialog.value = false

    // Reload logs and stats
    await Promise.all([loadLogs(), loadStats()])
  } catch (error) {
    console.error('Failed to cleanup logs:', error)
    showSnackbar('Failed to cleanup logs', 'error')
  } finally {
    cleaning.value = false
  }
}

const formatTimestamp = (timestamp, full = false) => {
  if (!timestamp) return 'N/A'

  const date = new Date(timestamp)

  if (full) {
    return date.toLocaleString()
  }

  // Show relative time for recent logs
  const now = new Date()
  const diff = now - date

  if (diff < 60000) {
    // Less than 1 minute
    return 'Just now'
  } else if (diff < 3600000) {
    // Less than 1 hour
    const minutes = Math.floor(diff / 60000)
    return `${minutes}m ago`
  } else if (diff < 86400000) {
    // Less than 1 day
    return date.toLocaleTimeString()
  } else {
    return (
      date.toLocaleDateString() +
      ' ' +
      date.toLocaleTimeString([], {
        hour: '2-digit',
        minute: '2-digit'
      })
    )
  }
}

const getLevelColor = level => {
  switch (level) {
    case 'ERROR':
      return 'error'
    case 'WARNING':
      return 'warning'
    case 'INFO':
      return 'info'
    case 'DEBUG':
      return 'grey'
    default:
      return 'grey'
  }
}

const copyToClipboard = async text => {
  try {
    await navigator.clipboard.writeText(text)
    showSnackbar('Copied to clipboard', 'success')
  } catch (error) {
    console.error('Failed to copy:', error)
    showSnackbar('Failed to copy', 'error')
  }
}

const onOptionsUpdate = options => {
  currentPage.value = options.page
  itemsPerPage.value = options.itemsPerPage
  loadLogs()
}

const showSnackbar = (text, color = 'success') => {
  snackbarText.value = text
  snackbarColor.value = color
  snackbar.value = true
}

// Watch filters
watch(
  () => filters.value.timeRange,
  () => {
    currentPage.value = 1
    loadLogs()
  }
)

// Lifecycle
onMounted(() => {
  loadLogs()
  loadStats()
})
</script>

<style scoped>
pre {
  white-space: pre-wrap;
  word-wrap: break-word;
  max-width: 100%;
}

code {
  background-color: rgba(0, 0, 0, 0.05);
  padding: 2px 4px;
  border-radius: 3px;
}
</style>
