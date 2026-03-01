<template>
  <div class="container mx-auto px-4 py-6">
    <AdminHeader
      title="System Logs"
      subtitle="View and analyze system logs"
      :icon="FileText"
      icon-color="orange"
      :breadcrumbs="ADMIN_BREADCRUMBS.logs"
    >
      <template #actions>
        <Button
          variant="outline"
          class="border-yellow-500 text-yellow-600"
          @click="showCleanupDialog = true"
        >
          <Trash2 class="size-4 mr-2" />
          Clean Up Old Logs
        </Button>
      </template>
    </AdminHeader>

    <!-- Stats Overview -->
    <div class="grid grid-cols-1 sm:grid-cols-2 md:grid-cols-4 gap-4 mb-6">
      <AdminStatsCard
        title="Total Logs"
        :value="stats.totalLogs"
        :loading="statsLoading"
        icon="mdi-file-document-multiple"
        color="info"
      />
      <AdminStatsCard
        title="Errors (24h)"
        :value="stats.errorCount"
        :loading="statsLoading"
        icon="mdi-alert-circle"
        color="error"
      />
      <AdminStatsCard
        title="Warnings (24h)"
        :value="stats.warningCount"
        :loading="statsLoading"
        icon="mdi-alert"
        color="warning"
      />
      <AdminStatsCard
        title="Storage Used"
        :value="stats.storageSize"
        :loading="statsLoading"
        icon="mdi-database"
        color="purple"
      />
    </div>

    <!-- Filters -->
    <Card class="mb-3">
      <CardContent class="pt-6">
        <div class="grid grid-cols-1 md:grid-cols-4 gap-4">
          <div class="space-y-2">
            <Label>Log Level</Label>
            <Select v-model="filters.level">
              <SelectTrigger>
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
            <Input v-model="filters.source" placeholder="Filter by source..." />
          </div>
          <div class="space-y-2">
            <Label>Request ID</Label>
            <Input v-model="filters.requestId" placeholder="Filter by request ID..." />
          </div>
          <div class="space-y-2">
            <Label>Time Range</Label>
            <Select v-model="filters.timeRange">
              <SelectTrigger>
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
              <SelectTrigger>
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
            <Button variant="secondary" size="sm" :disabled="exporting" @click="exportLogs">
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
        <div class="flex justify-between items-center">
          <div class="flex items-center gap-4">
            <div class="text-sm">
              <span class="font-bold">{{ totalLogs }}</span>
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
              <SelectTrigger class="w-[80px] h-8">
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
                variant="outline"
                size="icon"
                class="h-8 w-8"
                :disabled="currentPage <= 1"
                @click="updatePage(currentPage - 1)"
              >
                <ChevronLeft class="size-4" />
              </Button>
              <span class="text-sm px-2">{{ currentPage }} / {{ pageCount || 1 }}</span>
              <Button
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
        <Table>
          <TableHeader>
            <TableRow>
              <TableHead class="w-[150px]">Timestamp</TableHead>
              <TableHead class="w-[80px]">Level</TableHead>
              <TableHead class="w-[80px]">Method</TableHead>
              <TableHead class="w-[200px]">Path</TableHead>
              <TableHead class="w-[80px]">Status</TableHead>
              <TableHead class="w-[100px]">Duration</TableHead>
              <TableHead>Message</TableHead>
              <TableHead class="w-[100px] text-center">Actions</TableHead>
            </TableRow>
          </TableHeader>
          <TableBody>
            <TableRow v-if="loading">
              <TableCell colspan="8" class="text-center py-8 text-muted-foreground">
                Loading...
              </TableCell>
            </TableRow>
            <TableRow v-else-if="logs.length === 0">
              <TableCell colspan="8" class="text-center py-8 text-muted-foreground">
                No logs found
              </TableCell>
            </TableRow>
            <TableRow v-for="item in logs" :key="item.id" class="hover:bg-muted/50">
              <TableCell>
                <span class="text-xs">{{ formatTimestamp(item.timestamp) }}</span>
              </TableCell>
              <TableCell>
                <Badge :variant="getLevelVariant(item.level)" class="text-xs">
                  {{ item.level }}
                </Badge>
              </TableCell>
              <TableCell>
                <Badge v-if="item.method" variant="outline" class="text-xs">
                  {{ item.method }}
                </Badge>
              </TableCell>
              <TableCell>
                <code class="text-xs truncate block max-w-[200px]" :title="item.path">
                  {{ item.path || '-' }}
                </code>
              </TableCell>
              <TableCell>
                <Badge
                  v-if="item.status_code"
                  :variant="getStatusVariant(item.status_code)"
                  class="text-xs"
                >
                  {{ item.status_code }}
                </Badge>
              </TableCell>
              <TableCell>
                <span v-if="item.duration_ms" class="text-xs">
                  {{ formatDuration(item.duration_ms) }}
                </span>
              </TableCell>
              <TableCell>
                <div class="truncate max-w-[400px]" :title="item.message">
                  {{ item.message }}
                </div>
              </TableCell>
              <TableCell class="text-center">
                <Button
                  variant="ghost"
                  size="icon"
                  class="h-7 w-7"
                  title="View details"
                  @click="showLogDetails(item)"
                >
                  <Eye class="size-4" />
                </Button>
                <Button
                  v-if="item.request_id"
                  variant="ghost"
                  size="icon"
                  class="h-7 w-7"
                  title="Filter by request ID"
                  @click="filterByRequestId(item.request_id)"
                >
                  <Filter class="size-4" />
                </Button>
              </TableCell>
            </TableRow>
          </TableBody>
        </Table>
      </CardContent>
    </Card>

    <!-- Log Details Dialog -->
    <Dialog v-model:open="showDetailsDialog">
      <DialogContent class="max-w-[800px] max-h-[85vh] overflow-y-auto">
        <DialogHeader>
          <DialogTitle class="flex items-center gap-2">
            <Eye class="size-5" />
            Request Details
            <Badge v-if="selectedLog" :variant="getLevelVariant(selectedLog.level)" class="ml-1">
              {{ selectedLog.level }}
            </Badge>
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
                      <div class="text-sm">{{ formatTimestamp(selectedLog.timestamp, true) }}</div>
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
                        <Badge
                          v-if="selectedLog.status_code"
                          :variant="getStatusVariant(selectedLog.status_code)"
                        >
                          {{ selectedLog.status_code }}
                        </Badge>
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
                      <Badge v-if="selectedLog.method" variant="outline">{{
                        selectedLog.method
                      }}</Badge>
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
                      <Badge
                        v-if="selectedLog.status_code"
                        :variant="getStatusVariant(selectedLog.status_code)"
                      >
                        {{ selectedLog.status_code }}
                      </Badge>
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
                    <Badge variant="destructive">{{ selectedLog.error_type }}</Badge>
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
                      class="text-xs bg-red-50 dark:bg-red-950 text-red-700 dark:text-red-300 p-3 rounded overflow-x-auto"
                      >{{ selectedLog.stack_trace }}</pre
                    >
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

    <!-- Cleanup Dialog -->
    <Dialog v-model:open="showCleanupDialog">
      <DialogContent class="max-w-[400px]">
        <DialogHeader>
          <DialogTitle>Clean Up Old Logs</DialogTitle>
        </DialogHeader>
        <div class="space-y-4">
          <div class="space-y-2">
            <Label>Delete logs older than (days)</Label>
            <Input v-model.number="cleanupDays" type="number" min="1" max="365" />
          </div>
          <Alert variant="destructive">
            <AlertDescription>
              This will permanently delete all logs older than {{ cleanupDays }} days.
            </AlertDescription>
          </Alert>
        </div>
        <DialogFooter>
          <Button variant="outline" @click="showCleanupDialog = false">Cancel</Button>
          <Button variant="destructive" :disabled="cleaning" @click="executeCleanup">
            {{ cleaning ? 'Deleting...' : 'Delete Logs' }}
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  </div>
</template>

<script setup>
/**
 * System Log Viewer
 * Complete log management interface with filtering, search, and export
 */

import { ref, computed, onMounted, watch } from 'vue'
import AdminHeader from '@/components/admin/AdminHeader.vue'
import AdminStatsCard from '@/components/admin/AdminStatsCard.vue'
import * as logsApi from '@/api/admin/logs'
import { ADMIN_BREADCRUMBS } from '@/utils/adminBreadcrumbs'
import { toast } from 'vue-sonner'
import { Card, CardContent } from '@/components/ui/card'
import { Button } from '@/components/ui/button'
import { Badge } from '@/components/ui/badge'
import { Input } from '@/components/ui/input'
import { Label } from '@/components/ui/label'
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue
} from '@/components/ui/select'
import { Alert, AlertDescription } from '@/components/ui/alert'
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
  ChevronLeft,
  ChevronRight,
  Download,
  Eye,
  FileText,
  Filter,
  FilterX,
  Trash2
} from 'lucide-vue-next'

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

// Level/status variant helpers
const getLevelVariant = level => {
  switch (level) {
    case 'ERROR':
    case 'CRITICAL':
      return 'destructive'
    case 'WARNING':
      return 'outline'
    case 'INFO':
      return 'default'
    case 'DEBUG':
      return 'secondary'
    default:
      return 'outline'
  }
}

const getStatusVariant = status => {
  if (status >= 200 && status < 300) return 'default'
  if (status >= 300 && status < 400) return 'secondary'
  if (status >= 400 && status < 500) return 'outline'
  if (status >= 500) return 'destructive'
  return 'outline'
}

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
