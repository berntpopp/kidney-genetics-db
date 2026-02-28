<template>
  <v-container>
    <AdminHeader
      title="System Logs"
      subtitle="View and analyze system logs"
      :icon="FileText"
      icon-color="orange"
      :breadcrumbs="ADMIN_BREADCRUMBS.logs"
    >
      <template #actions>
        <v-btn
          color="warning"
          variant="elevated"
          prepend-icon="mdi-broom"
          @click="showCleanupDialog = true"
        >
          Clean Up Old Logs
        </v-btn>
      </template>
    </AdminHeader>

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
    <v-card class="mb-3" rounded="lg">
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
          <v-col cols="12" md="3">
            <v-select
              v-model="sortOption"
              :items="sortOptions"
              label="Sort by"
              density="compact"
              variant="outlined"
              hide-details
              @update:model-value="applySorting"
            />
          </v-col>
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
    <v-card rounded="lg">
      <!-- Top Pagination Controls -->
      <v-card-text class="pa-2 border-b">
        <div class="d-flex justify-space-between align-center">
          <div class="d-flex align-center ga-4">
            <div class="text-body-2">
              <span class="font-weight-bold">{{ totalLogs }}</span>
              <span class="text-medium-emphasis"> Log Entries</span>
            </div>
            <v-divider vertical />
            <div class="text-body-2 text-medium-emphasis">
              {{ pageRangeText }}
            </div>
          </div>
          <div class="d-flex align-center ga-2">
            <span class="text-caption text-medium-emphasis mr-2">Per page:</span>
            <v-select
              v-model="itemsPerPage"
              :items="itemsPerPageOptions"
              density="compact"
              variant="outlined"
              hide-details
              style="width: 100px"
              @update:model-value="updateItemsPerPage"
            />
            <v-pagination
              v-model="currentPage"
              :length="pageCount"
              :total-visible="5"
              density="compact"
              @update:model-value="updatePage"
            />
          </div>
        </div>
      </v-card-text>

      <v-data-table-server
        v-model:sort-by="sortBy"
        :headers="headers"
        :items="logs"
        :loading="loading"
        :items-per-page="itemsPerPage"
        :page="currentPage"
        :items-length="totalLogs"
        density="compact"
        hover
        :items-per-page-options="[]"
        must-sort
        @update:options="handleTableUpdate"
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

        <!-- Method column -->
        <template #item.method="{ item }">
          <v-chip v-if="item.method" :color="getMethodColor(item.method)" size="x-small" label>
            {{ item.method }}
          </v-chip>
        </template>

        <!-- Path column -->
        <template #item.path="{ item }">
          <code class="text-caption text-truncate" style="max-width: 200px" :title="item.path">
            {{ item.path || '-' }}
          </code>
        </template>

        <!-- Status column -->
        <template #item.status_code="{ item }">
          <v-chip
            v-if="item.status_code"
            :color="getStatusColor(item.status_code)"
            size="x-small"
            label
          >
            {{ item.status_code }}
          </v-chip>
        </template>

        <!-- Duration column -->
        <template #item.duration_ms="{ item }">
          <span v-if="item.duration_ms" class="text-caption">
            {{ formatDuration(item.duration_ms) }}
          </span>
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
        <!-- Hide bottom pagination slot -->
        <template #bottom />
      </v-data-table-server>
    </v-card>

    <!-- Log Details Dialog - Enhanced -->
    <v-dialog v-model="showDetailsDialog" max-width="1200" scrollable>
      <v-card v-if="selectedLog">
        <v-card-title class="d-flex align-center">
          <Eye class="size-5 mr-2" />
          Request Details
          <v-chip :color="getLevelColor(selectedLog.level)" size="small" label class="ml-2">
            {{ selectedLog.level }}
          </v-chip>
          <v-spacer />
          <v-btn
            icon="mdi-content-copy"
            size="small"
            variant="text"
            title="Copy Request ID"
            @click="copyToClipboard(selectedLog.request_id)"
          />
          <v-btn icon="mdi-close" size="small" variant="text" @click="showDetailsDialog = false" />
        </v-card-title>

        <v-tabs v-model="detailsTab" density="compact">
          <v-tab value="overview">
            <Info class="size-4 mr-2" />
            Overview
          </v-tab>
          <v-tab value="request">
            <SquareArrowRight class="size-4 mr-2" />
            Request
          </v-tab>
          <v-tab value="response">
            <SquareArrowLeft class="size-4 mr-2" />
            Response
          </v-tab>
          <v-tab v-if="selectedLog.error_type" value="error">
            <CircleAlert class="size-4 mr-2" />
            Error
          </v-tab>
          <v-tab value="context">
            <FileJson class="size-4 mr-2" />
            Context
          </v-tab>
        </v-tabs>

        <v-card-text>
          <v-tabs-window v-model="detailsTab">
            <!-- Overview Tab -->
            <v-tabs-window-item value="overview">
              <v-row>
                <v-col cols="12" md="6">
                  <v-list density="compact">
                    <v-list-item>
                      <v-list-item-title class="text-caption text-grey"
                        >Timestamp</v-list-item-title
                      >
                      <v-list-item-subtitle>{{
                        formatTimestamp(selectedLog.timestamp, true)
                      }}</v-list-item-subtitle>
                    </v-list-item>
                    <v-list-item>
                      <v-list-item-title class="text-caption text-grey"
                        >Request ID</v-list-item-title
                      >
                      <v-list-item-subtitle>
                        <code>{{ selectedLog.request_id || 'N/A' }}</code>
                      </v-list-item-subtitle>
                    </v-list-item>
                    <v-list-item>
                      <v-list-item-title class="text-caption text-grey">Duration</v-list-item-title>
                      <v-list-item-subtitle>
                        {{
                          selectedLog.duration_ms ? formatDuration(selectedLog.duration_ms) : 'N/A'
                        }}
                      </v-list-item-subtitle>
                    </v-list-item>
                    <v-list-item>
                      <v-list-item-title class="text-caption text-grey"
                        >Status Code</v-list-item-title
                      >
                      <v-list-item-subtitle>
                        <v-chip
                          v-if="selectedLog.status_code"
                          :color="getStatusColor(selectedLog.status_code)"
                          size="small"
                          label
                        >
                          {{ selectedLog.status_code }}
                        </v-chip>
                        <span v-else>N/A</span>
                      </v-list-item-subtitle>
                    </v-list-item>
                  </v-list>
                </v-col>
                <v-col cols="12" md="6">
                  <v-list density="compact">
                    <v-list-item>
                      <v-list-item-title class="text-caption text-grey"
                        >Source Module</v-list-item-title
                      >
                      <v-list-item-subtitle>
                        <code>{{ selectedLog.source }}</code>
                      </v-list-item-subtitle>
                    </v-list-item>
                    <v-list-item>
                      <v-list-item-title class="text-caption text-grey">User</v-list-item-title>
                      <v-list-item-subtitle>
                        {{ selectedLog.user_id ? `User ID: ${selectedLog.user_id}` : 'Anonymous' }}
                      </v-list-item-subtitle>
                    </v-list-item>
                    <v-list-item>
                      <v-list-item-title class="text-caption text-grey"
                        >IP Address</v-list-item-title
                      >
                      <v-list-item-subtitle>
                        {{ selectedLog.ip_address || selectedLog.client_info?.ip_address || 'N/A' }}
                      </v-list-item-subtitle>
                    </v-list-item>
                    <v-list-item>
                      <v-list-item-title class="text-caption text-grey">Message</v-list-item-title>
                      <v-list-item-subtitle class="text-wrap">
                        {{ selectedLog.message }}
                      </v-list-item-subtitle>
                    </v-list-item>
                  </v-list>
                </v-col>
              </v-row>
            </v-tabs-window-item>

            <!-- Request Tab -->
            <v-tabs-window-item value="request">
              <v-list density="compact">
                <v-list-item>
                  <v-list-item-title class="text-caption text-grey"
                    >Method & Path</v-list-item-title
                  >
                  <v-list-item-subtitle>
                    <v-chip
                      v-if="selectedLog.method"
                      :color="getMethodColor(selectedLog.method)"
                      size="small"
                      label
                      class="mr-2"
                    >
                      {{ selectedLog.method }}
                    </v-chip>
                    <code>{{ selectedLog.path || 'N/A' }}</code>
                  </v-list-item-subtitle>
                </v-list-item>

                <v-list-item v-if="selectedLog.query_params">
                  <v-list-item-title class="text-caption text-grey"
                    >Query Parameters</v-list-item-title
                  >
                  <v-list-item-subtitle>
                    <v-card variant="outlined" class="mt-2">
                      <v-card-text>
                        <pre class="json-display">{{ formatJson(selectedLog.query_params) }}</pre>
                      </v-card-text>
                    </v-card>
                  </v-list-item-subtitle>
                </v-list-item>

                <v-list-item v-if="selectedLog.request_body">
                  <v-list-item-title class="text-caption text-grey">Request Body</v-list-item-title>
                  <v-list-item-subtitle>
                    <v-card variant="outlined" class="mt-2">
                      <v-card-text>
                        <pre class="json-display">{{
                          formatRequestBody(selectedLog.request_body)
                        }}</pre>
                      </v-card-text>
                    </v-card>
                  </v-list-item-subtitle>
                </v-list-item>

                <v-list-item v-if="selectedLog.headers">
                  <v-list-item-title class="text-caption text-grey">Headers</v-list-item-title>
                  <v-list-item-subtitle>
                    <v-card variant="outlined" class="mt-2">
                      <v-card-text>
                        <pre class="json-display">{{ formatJson(selectedLog.headers) }}</pre>
                      </v-card-text>
                    </v-card>
                  </v-list-item-subtitle>
                </v-list-item>

                <v-list-item v-if="selectedLog.user_agent">
                  <v-list-item-title class="text-caption text-grey">User Agent</v-list-item-title>
                  <v-list-item-subtitle class="text-wrap">
                    <code>{{ selectedLog.user_agent }}</code>
                  </v-list-item-subtitle>
                </v-list-item>
              </v-list>
            </v-tabs-window-item>

            <!-- Response Tab -->
            <v-tabs-window-item value="response">
              <v-list density="compact">
                <v-list-item>
                  <v-list-item-title class="text-caption text-grey">Status</v-list-item-title>
                  <v-list-item-subtitle>
                    <v-chip
                      v-if="selectedLog.status_code"
                      :color="getStatusColor(selectedLog.status_code)"
                      size="small"
                      label
                    >
                      {{ selectedLog.status_code }}
                    </v-chip>
                    <span v-else>N/A</span>
                  </v-list-item-subtitle>
                </v-list-item>
                <v-list-item>
                  <v-list-item-title class="text-caption text-grey"
                    >Processing Time</v-list-item-title
                  >
                  <v-list-item-subtitle>
                    {{ selectedLog.duration_ms ? formatDuration(selectedLog.duration_ms) : 'N/A' }}
                  </v-list-item-subtitle>
                </v-list-item>
              </v-list>
            </v-tabs-window-item>

            <!-- Error Tab -->
            <v-tabs-window-item v-if="selectedLog.error_type" value="error">
              <v-list density="compact">
                <v-list-item>
                  <v-list-item-title class="text-caption text-grey">Error Type</v-list-item-title>
                  <v-list-item-subtitle>
                    <v-chip color="error" size="small" label>{{ selectedLog.error_type }}</v-chip>
                  </v-list-item-subtitle>
                </v-list-item>
                <v-list-item v-if="selectedLog.error_message">
                  <v-list-item-title class="text-caption text-grey"
                    >Error Message</v-list-item-title
                  >
                  <v-list-item-subtitle class="text-wrap">
                    {{ selectedLog.error_message }}
                  </v-list-item-subtitle>
                </v-list-item>
                <v-list-item v-if="selectedLog.stack_trace">
                  <v-list-item-title class="text-caption text-grey">Stack Trace</v-list-item-title>
                  <v-list-item-subtitle>
                    <v-card variant="outlined" class="mt-2">
                      <v-card-text>
                        <pre class="stack-trace">{{ selectedLog.stack_trace }}</pre>
                      </v-card-text>
                    </v-card>
                  </v-list-item-subtitle>
                </v-list-item>
              </v-list>
            </v-tabs-window-item>

            <!-- Context Tab -->
            <v-tabs-window-item value="context">
              <v-card variant="outlined">
                <v-card-text>
                  <pre class="json-display">{{ formatJson(selectedLog.context || {}) }}</pre>
                </v-card-text>
              </v-card>
            </v-tabs-window-item>
          </v-tabs-window>
        </v-card-text>

        <v-card-actions>
          <v-btn
            v-if="selectedLog.request_id"
            color="primary"
            variant="text"
            prepend-icon="mdi-filter-variant"
            @click="filterByRequestId(selectedLog.request_id)"
          >
            Filter by Request ID
          </v-btn>
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
  </v-container>
</template>

<script setup>
/**
 * System Log Viewer
 * Complete log management interface with filtering, search, and export
 */

import { ref, computed, onMounted, watch } from 'vue'
// import { useAuthStore } from '@/stores/auth'
import AdminHeader from '@/components/admin/AdminHeader.vue'
import AdminStatsCard from '@/components/admin/AdminStatsCard.vue'
import * as logsApi from '@/api/admin/logs'
import { ADMIN_BREADCRUMBS } from '@/utils/adminBreadcrumbs'
import { toast } from 'vue-sonner'
import {
  FileText,
  Eye,
  Info,
  SquareArrowRight,
  SquareArrowLeft,
  CircleAlert,
  FileJson
} from 'lucide-vue-next'

// const authStore = useAuthStore()

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
const detailsTab = ref('overview')

// Pagination
const itemsPerPage = ref(25)
const currentPage = ref(1)
const totalLogs = ref(0)
const itemsPerPageOptions = [
  { title: '10', value: 10 },
  { title: '25', value: 25 },
  { title: '50', value: 50 },
  { title: '100', value: 100 }
]

// Sorting
const sortBy = ref([{ key: 'timestamp', order: 'desc' }])
const sortOption = ref('timestamp_desc')
const sortOptions = [
  { title: 'Newest First', value: 'timestamp_desc' },
  { title: 'Oldest First', value: 'timestamp_asc' },
  { title: 'Level (Critical First)', value: 'level_desc' },
  { title: 'Level (Info First)', value: 'level_asc' },
  { title: 'Longest Duration', value: 'duration_desc' },
  { title: 'Shortest Duration', value: 'duration_asc' },
  { title: 'Path (A-Z)', value: 'path_asc' },
  { title: 'Path (Z-A)', value: 'path_desc' },
  { title: 'Source (A-Z)', value: 'source_asc' },
  { title: 'Source (Z-A)', value: 'source_desc' }
]

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

// Table configuration
const headers = [
  { title: 'Timestamp', key: 'timestamp', width: '150px', sortable: true },
  { title: 'Level', key: 'level', width: '80px', sortable: true },
  { title: 'Method', key: 'method', width: '80px', sortable: true },
  { title: 'Path', key: 'path', width: '200px', sortable: true },
  { title: 'Status', key: 'status_code', width: '80px', sortable: true },
  { title: 'Duration', key: 'duration_ms', width: '100px', sortable: true },
  { title: 'Message', key: 'message', sortable: true },
  { title: 'Actions', key: 'actions', sortable: false, width: '120px', align: 'center' }
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
const pageCount = computed(() => Math.ceil(totalLogs.value / itemsPerPage.value))

const pageRangeText = computed(() => {
  if (totalLogs.value === 0) return 'No logs found'
  const start = (currentPage.value - 1) * itemsPerPage.value + 1
  const end = Math.min(currentPage.value * itemsPerPage.value, totalLogs.value)
  return `Showing ${start}-${end} of ${totalLogs.value}`
})

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

  if (searchQuery.value) {
    params.search = searchQuery.value
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

  // Add sorting parameters
  if (sortBy.value.length > 0) {
    // Map frontend keys to backend field names
    const fieldMap = {
      timestamp: 'timestamp',
      level: 'level',
      method: 'method',
      path: 'path',
      status_code: 'status_code',
      duration_ms: 'duration_ms',
      message: 'message',
      source: 'logger' // Backend uses 'logger' field for source
    }
    params.sort_by = fieldMap[sortBy.value[0].key] || sortBy.value[0].key
    params.sort_order = sortBy.value[0].order
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
    window.logService.error('Failed to load logs:', error)
    toast.error('Failed to load logs', { duration: Infinity })
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
    window.logService.error('Failed to load log statistics:', error)
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
  sortBy.value = [{ key: 'timestamp', order: 'desc' }]
  sortOption.value = 'timestamp_desc'
  loadLogs()
}

const applySorting = () => {
  const [field, order] = sortOption.value.split('_')
  const fieldMap = {
    timestamp: 'timestamp',
    level: 'level',
    duration: 'duration_ms',
    path: 'path',
    source: 'source'
  }
  sortBy.value = [{ key: fieldMap[field] || field, order }]
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

    toast.success('Logs exported successfully', { duration: 5000 })
  } catch (error) {
    window.logService.error('Failed to export logs:', error)
    toast.error('Failed to export logs', { duration: Infinity })
  } finally {
    exporting.value = false
  }
}

const executeCleanup = async () => {
  cleaning.value = true
  try {
    const response = await logsApi.cleanupLogs(cleanupDays.value)
    const data = response.data || response

    toast.success(`Deleted ${data.logs_deleted || 0} log entries`, { duration: 5000 })
    showCleanupDialog.value = false

    // Reload logs and stats
    await Promise.all([loadLogs(), loadStats()])
  } catch (error) {
    window.logService.error('Failed to cleanup logs:', error)
    toast.error('Failed to cleanup logs', { duration: Infinity })
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

const getMethodColor = method => {
  switch (method) {
    case 'GET':
      return 'success'
    case 'POST':
      return 'primary'
    case 'PUT':
      return 'warning'
    case 'PATCH':
      return 'orange'
    case 'DELETE':
      return 'error'
    default:
      return 'grey'
  }
}

const getStatusColor = status => {
  if (status >= 200 && status < 300) return 'success'
  if (status >= 300 && status < 400) return 'info'
  if (status >= 400 && status < 500) return 'warning'
  if (status >= 500) return 'error'
  return 'grey'
}

const formatDuration = ms => {
  if (ms < 1000) return `${ms}ms`
  if (ms < 60000) return `${(ms / 1000).toFixed(1)}s`
  return `${(ms / 60000).toFixed(1)}m`
}

const formatJson = obj => {
  if (!obj) return 'N/A'
  if (typeof obj === 'string') {
    try {
      obj = JSON.parse(obj)
    } catch {
      return obj
    }
  }
  return JSON.stringify(obj, null, 2)
}

const formatRequestBody = body => {
  if (!body) return 'No request body'
  if (typeof body === 'string') {
    // Try to parse as JSON for better formatting
    try {
      const parsed = JSON.parse(body)
      return JSON.stringify(parsed, null, 2)
    } catch {
      // Not JSON, return as is
      return body
    }
  }
  return JSON.stringify(body, null, 2)
}

const copyToClipboard = async text => {
  try {
    await navigator.clipboard.writeText(text)
    toast.success('Copied to clipboard', { duration: 5000 })
  } catch (error) {
    window.logService.error('Failed to copy:', error)
    toast.error('Failed to copy', { duration: Infinity })
  }
}

const handleTableUpdate = () => {
  // The v-data-table-server will update sortBy automatically via v-model
  // Our watcher will handle the actual loading
}

const updatePage = newPage => {
  currentPage.value = newPage
  loadLogs()
}

const updateItemsPerPage = newValue => {
  itemsPerPage.value = newValue
  currentPage.value = 1 // Reset to first page when changing items per page
  loadLogs()
}

// Watch filters
watch(
  () => filters.value.timeRange,
  () => {
    currentPage.value = 1
    loadLogs()
  }
)

// Watch for sorting changes from table headers
watch(
  sortBy,
  newSortBy => {
    if (newSortBy.length > 0) {
      const key = newSortBy[0].key
      const order = newSortBy[0].order
      const reverseFieldMap = {
        timestamp: 'timestamp',
        level: 'level',
        duration_ms: 'duration',
        path: 'path',
        method: 'method',
        status_code: 'status',
        message: 'message',
        logger: 'source'
      }
      const field = reverseFieldMap[key] || key
      sortOption.value = `${field}_${order}`
      loadLogs()
    }
  },
  { deep: true }
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
  font-family: 'Roboto Mono', monospace;
  font-size: 12px;
}

.json-display {
  background-color: #f5f5f5;
  border-radius: 4px;
  padding: 12px;
  font-family: 'Roboto Mono', monospace;
  font-size: 12px;
  line-height: 1.6;
  overflow-x: auto;
}

.v-theme--dark .json-display {
  background-color: #1e1e1e;
}

.stack-trace {
  background-color: #fee;
  border-radius: 4px;
  padding: 12px;
  font-family: 'Roboto Mono', monospace;
  font-size: 11px;
  line-height: 1.5;
  overflow-x: auto;
  color: #d00;
}

.v-theme--dark .stack-trace {
  background-color: #3e1e1e;
  color: #ff6b6b;
}

.text-caption.text-grey {
  text-transform: uppercase;
  letter-spacing: 0.05em;
  font-weight: 500;
}

.v-list-item {
  border-bottom: thin solid rgba(0, 0, 0, 0.05);
}

.v-list-item:last-child {
  border-bottom: none;
}

.v-theme--dark .v-list-item {
  border-bottom-color: rgba(255, 255, 255, 0.05);
}
</style>
