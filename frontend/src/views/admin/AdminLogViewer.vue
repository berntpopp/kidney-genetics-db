<template>
  <div :class="PAGE_CONTAINER">
    <AdminHeader title="System Logs" subtitle="View and analyze system logs">
      <template #actions>
        <Button
          variant="outline"
          class="text-danger hover:text-danger"
          @click="showCleanupDialog = true"
        >
          <Trash2 class="size-4" aria-hidden="true" />
          Clean Up Old Logs
        </Button>
      </template>
    </AdminHeader>

    <!-- Stats Overview -->
    <div class="grid grid-cols-2 md:grid-cols-4 gap-3 mb-6">
      <AdminStatsCard
        title="Total Logs"
        :value="stats.totalLogs"
        :loading="statsLoading"
        :icon="Files"
      />
      <AdminStatsCard
        title="Errors (24h)"
        :value="stats.errorCount"
        :loading="statsLoading"
        :icon="CircleAlert"
      />
      <AdminStatsCard
        title="Warnings (24h)"
        :value="stats.warningCount"
        :loading="statsLoading"
        :icon="AlertTriangle"
      />
      <AdminStatsCard
        title="Storage Used"
        :value="stats.storageSize"
        :loading="statsLoading"
        :icon="Database"
      />
    </div>

    <!-- Filters -->
    <Card class="mb-3">
      <CardContent class="pt-6">
        <div class="grid grid-cols-1 md:grid-cols-4 gap-4">
          <div class="space-y-2">
            <Label>Log Level</Label>
            <Select v-model="filters.level">
              <SelectTrigger aria-label="Log Level">
                <SelectValue placeholder="All levels" />
              </SelectTrigger>
              <SelectContent>
                <SelectItem value="all">All levels</SelectItem>
                <SelectItem v-for="level in logLevels" :key="level" :value="level">
                  {{ level }}
                </SelectItem>
              </SelectContent>
            </Select>
          </div>
          <div class="space-y-2">
            <Label>Source Module</Label>
            <div class="flex items-center gap-2">
              <Input v-model="filters.source" placeholder="Filter by source..." class="flex-1" />
              <button
                type="button"
                :aria-pressed="filters.source === 'frontend'"
                class="inline-flex h-9 items-center gap-1.5 rounded-md border px-3 text-sm whitespace-nowrap focus-visible:ring-2 focus-visible:ring-ring focus-visible:outline-none"
                :class="
                  filters.source === 'frontend'
                    ? 'border-primary bg-primary/10 text-primary'
                    : 'border-border text-muted-foreground hover:bg-muted'
                "
                @click="toggleFrontendFilter"
              >
                <Monitor class="size-4" aria-hidden="true" />
                Frontend Errors
              </button>
            </div>
          </div>
          <div class="space-y-2">
            <Label>Request ID</Label>
            <Input v-model="filters.requestId" placeholder="Filter by request ID..." />
          </div>
          <div class="space-y-2">
            <Label>Time Range</Label>
            <Select v-model="filters.timeRange">
              <SelectTrigger aria-label="Time Range">
                <SelectValue placeholder="Select range" />
              </SelectTrigger>
              <SelectContent>
                <SelectItem v-for="range in timeRanges" :key="range.value" :value="range.value">
                  {{ range.title }}
                </SelectItem>
              </SelectContent>
            </Select>
          </div>
        </div>
        <div class="grid grid-cols-1 md:grid-cols-12 gap-4 mt-4">
          <div class="md:col-span-3 space-y-2">
            <Label>Sort by</Label>
            <Select v-model="sortOption" @update:model-value="applySorting">
              <SelectTrigger aria-label="Sort by">
                <SelectValue />
              </SelectTrigger>
              <SelectContent>
                <SelectItem v-for="opt in sortOptions" :key="opt.value" :value="opt.value">
                  {{ opt.title }}
                </SelectItem>
              </SelectContent>
            </Select>
          </div>
          <div class="md:col-span-5 space-y-2">
            <Label>Search</Label>
            <Input v-model="searchQuery" placeholder="Search logs..." @keyup.enter="loadLogs" />
          </div>
          <div class="md:col-span-4 flex items-end gap-2 justify-end">
            <Button size="sm" :disabled="loading" @click="loadLogs">
              <Filter class="size-4 mr-1" />
              Apply Filters
            </Button>
            <Button variant="outline" size="sm" @click="clearFilters">
              <FilterX class="size-4 mr-1" />
              Clear
            </Button>
            <Button variant="outline" size="sm" :disabled="exporting" @click="exportLogs">
              <Download class="size-4 mr-1" />
              Export
            </Button>
          </div>
        </div>
      </CardContent>
    </Card>

    <!-- Logs Table -->
    <Card>
      <!-- Top Pagination Controls -->
      <div class="p-2 border-b">
        <div class="flex flex-wrap justify-between items-center gap-x-4 gap-y-2">
          <div class="flex items-center gap-4">
            <div class="text-sm">
              <span class="font-semibold tabular-nums">{{ totalLogs.toLocaleString() }}</span>
              <span class="text-muted-foreground"> Log Entries</span>
            </div>
            <Separator orientation="vertical" class="h-4" />
            <div class="text-sm text-muted-foreground">
              {{ pageRangeText }}
            </div>
          </div>
          <div class="flex items-center gap-2">
            <span class="text-xs text-muted-foreground mr-2">Per page:</span>
            <Select v-model="itemsPerPageStr" @update:model-value="updateItemsPerPage">
              <SelectTrigger aria-label="Per page" class="w-[80px] h-8">
                <SelectValue />
              </SelectTrigger>
              <SelectContent>
                <SelectItem
                  v-for="opt in itemsPerPageOptions"
                  :key="opt.value"
                  :value="String(opt.value)"
                >
                  {{ opt.title }}
                </SelectItem>
              </SelectContent>
            </Select>
            <div class="flex items-center gap-1">
              <Button
                aria-label="Previous page"
                variant="outline"
                size="icon"
                class="h-8 w-8"
                :disabled="currentPage <= 1"
                @click="updatePage(currentPage - 1)"
              >
                <ChevronLeft class="size-4" />
              </Button>
              <span class="text-sm px-2 tabular-nums"
                >{{ currentPage }} / {{ pageCount || 1 }}</span
              >
              <Button
                aria-label="Next page"
                variant="outline"
                size="icon"
                class="h-8 w-8"
                :disabled="currentPage >= pageCount"
                @click="updatePage(currentPage + 1)"
              >
                <ChevronRight class="size-4" />
              </Button>
            </div>
          </div>
        </div>
      </div>

      <CardContent class="p-0">
        <DataState
          :loading="loading && !logs.length"
          :error="loadError"
          error-title="Could not load logs"
          :empty="!logs.length"
          empty-message="No log entries match these filters."
          class="m-4"
          @retry="loadLogs"
        >
          <template #loading>
            <div class="space-y-3 p-4" aria-hidden="true">
              <div
                v-for="i in 8"
                :key="i"
                class="h-8 rounded-md bg-muted motion-safe:animate-pulse"
              />
            </div>
          </template>
          <Table>
            <TableHeader>
              <TableRow>
                <TableHead class="w-[170px]">Timestamp</TableHead>
                <TableHead class="w-[100px]">Level</TableHead>
                <TableHead class="hidden w-[80px] xl:table-cell">Method</TableHead>
                <TableHead class="hidden w-[200px] xl:table-cell">Path</TableHead>
                <TableHead class="hidden w-[80px] xl:table-cell">Status</TableHead>
                <TableHead class="hidden w-[90px] text-right xl:table-cell">Duration</TableHead>
                <TableHead>Message</TableHead>
                <TableHead class="w-[88px]"><span class="sr-only">Actions</span></TableHead>
              </TableRow>
            </TableHeader>
            <TableBody>
              <TableRow v-for="item in logs" :key="item.id">
                <TableCell>
                  <span class="text-xs tabular-nums whitespace-nowrap">{{
                    formatTimestamp(item.timestamp)
                  }}</span>
                </TableCell>
                <TableCell>
                  <StatusBadge :status="item.level" />
                </TableCell>
                <TableCell class="hidden xl:table-cell">
                  <Chip v-if="item.method" kind="neutral" :label="item.method" class="font-mono" />
                </TableCell>
                <TableCell class="hidden xl:table-cell">
                  <code
                    v-if="item.path"
                    class="text-xs truncate block max-w-[200px]"
                    :title="item.path"
                  >
                    {{ item.path }}
                  </code>
                </TableCell>
                <TableCell class="hidden xl:table-cell">
                  <StatusBadge v-if="item.status_code" :status="item.status_code" />
                </TableCell>
                <TableCell class="hidden text-right xl:table-cell">
                  <span v-if="item.duration_ms" class="text-xs tabular-nums">
                    {{ formatDuration(item.duration_ms) }}
                  </span>
                </TableCell>
                <TableCell>
                  <div class="truncate max-w-[480px]" :title="item.message">
                    {{ item.message }}
                  </div>
                </TableCell>
                <TableCell>
                  <div class="flex justify-end gap-1">
                    <Tooltip>
                      <TooltipTrigger as-child>
                        <Button
                          variant="ghost"
                          size="icon-sm"
                          aria-label="View log details"
                          @click="showLogDetails(item)"
                        >
                          <Eye class="size-4" aria-hidden="true" />
                        </Button>
                      </TooltipTrigger>
                      <TooltipContent>View log details</TooltipContent>
                    </Tooltip>
                    <Tooltip v-if="item.request_id">
                      <TooltipTrigger as-child>
                        <Button
                          variant="ghost"
                          size="icon-sm"
                          aria-label="Show all logs of this request"
                          @click="filterByRequestId(item.request_id)"
                        >
                          <Filter class="size-4" aria-hidden="true" />
                        </Button>
                      </TooltipTrigger>
                      <TooltipContent>Show all logs of this request</TooltipContent>
                    </Tooltip>
                  </div>
                </TableCell>
              </TableRow>
            </TableBody>
          </Table>
        </DataState>
      </CardContent>
    </Card>

    <!-- Log Details Dialog -->
    <Dialog v-model:open="showDetailsDialog">
      <DialogContent class="max-w-[800px] max-h-[85vh] overflow-y-auto">
        <DialogHeader>
          <DialogTitle class="flex items-center gap-2">
            Log details
            <StatusBadge v-if="selectedLog" :status="selectedLog.level" class="ml-1" />
          </DialogTitle>
        </DialogHeader>

        <div v-if="selectedLog">
          <Tabs v-model="detailsTab" class="w-full">
            <TabsList class="grid w-full grid-cols-5">
              <TabsTrigger value="overview">Overview</TabsTrigger>
              <TabsTrigger value="request">Request</TabsTrigger>
              <TabsTrigger value="response">Response</TabsTrigger>
              <TabsTrigger v-if="selectedLog.error_type" value="error">Error</TabsTrigger>
              <TabsTrigger value="context">Context</TabsTrigger>
            </TabsList>

            <ScrollArea class="max-h-[50vh] mt-4">
              <!-- Overview Tab -->
              <TabsContent value="overview">
                <div class="grid grid-cols-1 md:grid-cols-2 gap-4">
                  <div class="space-y-3">
                    <div class="border-b pb-2">
                      <div
                        class="text-xs text-muted-foreground uppercase tracking-wide font-medium"
                      >
                        Timestamp
                      </div>
                      <div class="text-sm">{{ formatTimestamp(selectedLog.timestamp) }}</div>
                    </div>
                    <div class="border-b pb-2">
                      <div
                        class="text-xs text-muted-foreground uppercase tracking-wide font-medium"
                      >
                        Request ID
                      </div>
                      <div class="text-sm">
                        <code>{{ selectedLog.request_id || 'N/A' }}</code>
                      </div>
                    </div>
                    <div class="border-b pb-2">
                      <div
                        class="text-xs text-muted-foreground uppercase tracking-wide font-medium"
                      >
                        Duration
                      </div>
                      <div class="text-sm">
                        {{
                          selectedLog.duration_ms ? formatDuration(selectedLog.duration_ms) : 'N/A'
                        }}
                      </div>
                    </div>
                    <div class="border-b pb-2">
                      <div
                        class="text-xs text-muted-foreground uppercase tracking-wide font-medium"
                      >
                        Status Code
                      </div>
                      <div class="text-sm">
                        <StatusBadge
                          v-if="selectedLog.status_code"
                          :status="selectedLog.status_code"
                        />
                        <span v-else>N/A</span>
                      </div>
                    </div>
                  </div>
                  <div class="space-y-3">
                    <div class="border-b pb-2">
                      <div
                        class="text-xs text-muted-foreground uppercase tracking-wide font-medium"
                      >
                        Source Module
                      </div>
                      <div class="text-sm">
                        <code>{{ selectedLog.source }}</code>
                      </div>
                    </div>
                    <div class="border-b pb-2">
                      <div
                        class="text-xs text-muted-foreground uppercase tracking-wide font-medium"
                      >
                        User
                      </div>
                      <div class="text-sm">
                        {{ selectedLog.user_id ? `User ID: ${selectedLog.user_id}` : 'Anonymous' }}
                      </div>
                    </div>
                    <div class="border-b pb-2">
                      <div
                        class="text-xs text-muted-foreground uppercase tracking-wide font-medium"
                      >
                        IP Address
                      </div>
                      <div class="text-sm">
                        {{ selectedLog.ip_address || selectedLog.client_info?.ip_address || 'N/A' }}
                      </div>
                    </div>
                    <div class="border-b pb-2">
                      <div
                        class="text-xs text-muted-foreground uppercase tracking-wide font-medium"
                      >
                        Message
                      </div>
                      <div class="text-sm break-words">{{ selectedLog.message }}</div>
                    </div>
                  </div>
                </div>
              </TabsContent>

              <!-- Request Tab -->
              <TabsContent value="request">
                <div class="space-y-4">
                  <div class="border-b pb-2">
                    <div
                      class="text-xs text-muted-foreground uppercase tracking-wide font-medium mb-1"
                    >
                      Method & Path
                    </div>
                    <div class="flex items-center gap-2">
                      <Chip
                        v-if="selectedLog.method"
                        kind="neutral"
                        :label="selectedLog.method"
                        class="font-mono"
                      />
                      <code class="text-sm">{{ selectedLog.path || 'N/A' }}</code>
                    </div>
                  </div>
                  <div v-if="selectedLog.query_params" class="border-b pb-2">
                    <div
                      class="text-xs text-muted-foreground uppercase tracking-wide font-medium mb-1"
                    >
                      Query Parameters
                    </div>
                    <pre class="text-xs bg-muted p-3 rounded overflow-x-auto">{{
                      formatJson(selectedLog.query_params)
                    }}</pre>
                  </div>
                  <div v-if="selectedLog.request_body" class="border-b pb-2">
                    <div
                      class="text-xs text-muted-foreground uppercase tracking-wide font-medium mb-1"
                    >
                      Request Body
                    </div>
                    <pre class="text-xs bg-muted p-3 rounded overflow-x-auto">{{
                      formatRequestBody(selectedLog.request_body)
                    }}</pre>
                  </div>
                  <div v-if="selectedLog.headers" class="border-b pb-2">
                    <div
                      class="text-xs text-muted-foreground uppercase tracking-wide font-medium mb-1"
                    >
                      Headers
                    </div>
                    <pre class="text-xs bg-muted p-3 rounded overflow-x-auto">{{
                      formatJson(selectedLog.headers)
                    }}</pre>
                  </div>
                  <div v-if="selectedLog.user_agent" class="border-b pb-2">
                    <div
                      class="text-xs text-muted-foreground uppercase tracking-wide font-medium mb-1"
                    >
                      User Agent
                    </div>
                    <code class="text-xs break-all">{{ selectedLog.user_agent }}</code>
                  </div>
                </div>
              </TabsContent>

              <!-- Response Tab -->
              <TabsContent value="response">
                <div class="space-y-3">
                  <div class="border-b pb-2">
                    <div class="text-xs text-muted-foreground uppercase tracking-wide font-medium">
                      Status
                    </div>
                    <div class="text-sm">
                      <StatusBadge
                        v-if="selectedLog.status_code"
                        :status="selectedLog.status_code"
                      />
                      <span v-else>N/A</span>
                    </div>
                  </div>
                  <div class="border-b pb-2">
                    <div class="text-xs text-muted-foreground uppercase tracking-wide font-medium">
                      Processing Time
                    </div>
                    <div class="text-sm">
                      {{
                        selectedLog.duration_ms ? formatDuration(selectedLog.duration_ms) : 'N/A'
                      }}
                    </div>
                  </div>
                </div>
              </TabsContent>

              <!-- Error Tab -->
              <TabsContent v-if="selectedLog.error_type" value="error">
                <div class="space-y-3">
                  <div class="border-b pb-2">
                    <div class="text-xs text-muted-foreground uppercase tracking-wide font-medium">
                      Error Type
                    </div>
                    <StatusBadge status="error" :label="selectedLog.error_type" />
                  </div>
                  <div v-if="selectedLog.error_message" class="border-b pb-2">
                    <div class="text-xs text-muted-foreground uppercase tracking-wide font-medium">
                      Error Message
                    </div>
                    <div class="text-sm break-words">{{ selectedLog.error_message }}</div>
                  </div>
                  <div v-if="selectedLog.stack_trace">
                    <div
                      class="text-xs text-muted-foreground uppercase tracking-wide font-medium mb-1"
                    >
                      Stack Trace
                    </div>
                    <pre
                      class="text-xs bg-danger-subtle text-foreground p-3 rounded overflow-x-auto"
                      >{{ selectedLog.stack_trace }}</pre>
                  </div>
                </div>
              </TabsContent>

              <!-- Context Tab -->
              <TabsContent value="context">
                <pre class="text-xs bg-muted p-3 rounded overflow-x-auto">{{
                  formatJson(selectedLog.context || {})
                }}</pre>
              </TabsContent>
            </ScrollArea>
          </Tabs>
        </div>

        <DialogFooter>
          <Button
            v-if="selectedLog?.request_id"
            variant="outline"
            @click="filterByRequestId(selectedLog.request_id)"
          >
            <Filter class="size-4 mr-2" />
            Filter by Request ID
          </Button>
          <Button variant="outline" @click="showDetailsDialog = false">Close</Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>

    <!-- Cleanup confirmation -->
    <ConfirmAction
      v-model:open="showCleanupDialog"
      title="Delete old logs?"
      :confirm-label="cleaning ? 'Deleting…' : 'Delete logs'"
      danger
      :disabled="cleaning || !(cleanupDays >= 1)"
      @confirm="executeCleanup"
    >
      <p>
        Permanently deletes every log entry older than the number of days below. This cannot be
        undone.
      </p>
      <div class="space-y-2 pt-2">
        <Label for="cleanup-days" class="text-foreground">Delete logs older than (days)</Label>
        <Input id="cleanup-days" v-model.number="cleanupDays" type="number" min="1" max="365" />
      </div>
    </ConfirmAction>
  </div>
</template>

<script setup>
/**
 * System Log Viewer
 * Complete log management interface with filtering, search, and export
 */

import { ref, computed, onMounted, watch } from 'vue'
import AdminHeader from '@/components/admin/AdminHeader.vue'
import { Chip, DataState, PAGE_CONTAINER, StatusBadge } from '@/components/shared'
import ConfirmAction from '@/components/admin/ConfirmAction.vue'
import { Tooltip, TooltipContent, TooltipTrigger } from '@/components/ui/tooltip'
import AdminStatsCard from '@/components/admin/AdminStatsCard.vue'
import * as logsApi from '@/api/admin/logs'
import { toast } from 'vue-sonner'
import { Card, CardContent } from '@/components/ui/card'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { Label } from '@/components/ui/label'
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue
} from '@/components/ui/select'
import { Separator } from '@/components/ui/separator'
import {
  Dialog,
  DialogContent,
  DialogFooter,
  DialogHeader,
  DialogTitle
} from '@/components/ui/dialog'
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow
} from '@/components/ui/table'
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs'
import { ScrollArea } from '@/components/ui/scroll-area'
import {
  AlertTriangle,
  ChevronLeft,
  ChevronRight,
  CircleAlert,
  Database,
  Download,
  Eye,
  Files,
  Filter,
  FilterX,
  Monitor,
  Trash2
} from 'lucide-vue-next'

// State
const logs = ref([])
const loading = ref(false)
const loadError = ref(null)
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
const itemsPerPageStr = ref('25')
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

  if (filters.value.level && filters.value.level !== 'all') {
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
  loadError.value = null
  try {
    const response = await logsApi.queryLogs(queryParams.value)
    const data = response.data || response

    logs.value = data.logs || []
    totalLogs.value = data.pagination?.total || 0
  } catch (error) {
    window.logService.error('Failed to load logs:', error)
    loadError.value = error.message || 'Request failed'
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

const toggleFrontendFilter = () => {
  if (filters.value.source === 'frontend') {
    filters.value.source = ''
  } else {
    filters.value.source = 'frontend'
  }
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

// Exact time per row; relative labels collapsed every recent log to "Just now"
const formatTimestamp = timestamp => (timestamp ? new Date(timestamp).toLocaleString() : 'N/A')

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

const updatePage = newPage => {
  currentPage.value = newPage
  loadLogs()
}

const updateItemsPerPage = newValue => {
  itemsPerPage.value = parseInt(newValue)
  itemsPerPageStr.value = newValue
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

// Lifecycle
onMounted(() => {
  loadLogs()
  loadStats()
})
</script>
