# Database Backup Management - Frontend UI Plan

**Related**: #23 Automated Database Backup Plan
**Status**: Planning
**Priority**: High (Admin Tool)
**Effort**: 1-2 days

## UI/UX Style Guide Analysis

Based on existing admin views (`AdminDashboard.vue`, `AdminLogViewer.vue`, `AdminAnnotations.vue`):

### Established Patterns

**Layout Structure**:
- `<v-container fluid class="pa-4">` - Outer container with padding
- `AdminHeader` - Title, subtitle, back-route="/admin"
- `AdminStatsCard` - 4 stats cards in `<v-row>` (cols="12" sm="6" md="3")
- Filters section in `<v-card rounded="lg">`
- Data table in `<v-card rounded="lg">`
- Action buttons with icons and loading states

**Component Density**:
- All form controls: `density="compact"`
- All selects/inputs: `variant="outlined"`
- Buttons: `size="small"` with `prepend-icon`

**Color Palette**:
- `primary` (blue) - Main actions
- `success` (green) - Positive actions, completed states
- `info` (cyan) - Informational
- `warning` (orange/yellow) - Caution, pending
- `error` (red) - Errors, failed states
- `purple` - Cache/storage related
- `teal` - Annotations/data

**Icon Library**: Material Design Icons (`mdi-*`)

**Table Patterns**:
- `v-data-table-server` for server-side pagination
- Top pagination controls with items-per-page selector
- Compact row display with hover effects
- Sort indicators in headers

---

## Implementation Plan

### 1. Add Card to AdminDashboard.vue

**Location**: `/frontend/src/views/admin/AdminDashboard.vue`

**Add to `adminSections` array** (line 161):

```javascript
{
  id: 'backups',
  title: 'Database Backups',
  description: 'Create and manage database backups',
  icon: 'mdi-database-export',
  color: 'indigo',
  route: '/admin/backups',
  features: [
    'Create on-demand backups',
    'Schedule automated backups',
    'Restore from backup',
    'Download backup files'
  ]
}
```

**Position**: Insert after `annotations` section (becomes 7th card)

---

### 2. Create AdminBackups.vue View

**Location**: `/frontend/src/views/admin/AdminBackups.vue`

**File Structure** (based on AdminLogViewer.vue pattern):

```vue
<template>
  <v-container fluid class="pa-4">
    <!-- Header -->
    <AdminHeader
      title="Database Backups"
      subtitle="Create, manage, and restore database backups"
      back-route="/admin"
    >
      <template #actions>
        <v-btn
          color="primary"
          variant="elevated"
          prepend-icon="mdi-database-plus"
          :loading="creating"
          @click="showCreateDialog = true"
        >
          Create Backup
        </v-btn>
      </template>
    </AdminHeader>

    <!-- Stats Overview (4 cards) -->
    <v-row class="mb-6">
      <v-col cols="12" sm="6" md="3">
        <AdminStatsCard
          title="Total Backups"
          :value="stats.totalBackups"
          :loading="statsLoading"
          icon="mdi-database-outline"
          color="primary"
        />
      </v-col>
      <v-col cols="12" sm="6" md="3">
        <AdminStatsCard
          title="Latest Backup"
          :value="stats.latestBackupAge"
          :loading="statsLoading"
          icon="mdi-clock-outline"
          color="info"
        />
      </v-col>
      <v-col cols="12" sm="6" md="3">
        <AdminStatsCard
          title="Total Size"
          :value="stats.totalSize"
          :loading="statsLoading"
          format="bytes"
          icon="mdi-harddisk"
          color="purple"
        />
      </v-col>
      <v-col cols="12" sm="6" md="3">
        <AdminStatsCard
          title="Retention Days"
          :value="stats.retentionDays"
          :loading="statsLoading"
          icon="mdi-calendar-clock"
          color="warning"
        />
      </v-col>
    </v-row>

    <!-- Filters -->
    <v-card class="mb-3" rounded="lg">
      <v-card-text>
        <v-row>
          <v-col cols="12" md="3">
            <v-select
              v-model="filters.status"
              label="Status"
              :items="statusOptions"
              density="compact"
              variant="outlined"
              clearable
              hide-details
            />
          </v-col>
          <v-col cols="12" md="3">
            <v-select
              v-model="filters.triggerSource"
              label="Trigger Source"
              :items="triggerOptions"
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
          <v-col cols="12" md="3">
            <v-text-field
              v-model="searchQuery"
              label="Search description..."
              prepend-inner-icon="mdi-magnify"
              density="compact"
              variant="outlined"
              clearable
              hide-details
              @keyup.enter="loadBackups"
            />
          </v-col>
        </v-row>
        <v-row class="mt-3">
          <v-col cols="12" class="text-right">
            <v-btn
              color="primary"
              size="small"
              prepend-icon="mdi-filter"
              :loading="loading"
              class="mr-2"
              @click="loadBackups"
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
              color="error"
              size="small"
              prepend-icon="mdi-delete-sweep"
              :loading="cleaning"
              @click="cleanupOldBackups"
            >
              Cleanup Old
            </v-btn>
          </v-col>
        </v-row>
      </v-card-text>
    </v-card>

    <!-- Backups Table -->
    <v-card rounded="lg">
      <!-- Top Pagination -->
      <v-card-text class="pa-2 border-b">
        <div class="d-flex justify-space-between align-center">
          <div class="d-flex align-center ga-4">
            <div class="text-body-2">
              <span class="font-weight-bold">{{ totalBackups }}</span>
              <span class="text-medium-emphasis"> Backups</span>
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
              :items="[10, 25, 50, 100]"
              density="compact"
              variant="outlined"
              hide-details
              style="width: 100px"
              @update:model-value="loadBackups"
            />
            <v-pagination
              v-model="currentPage"
              :length="pageCount"
              :total-visible="5"
              density="compact"
              @update:model-value="loadBackups"
            />
          </div>
        </div>
      </v-card-text>

      <!-- Data Table -->
      <v-data-table
        :headers="headers"
        :items="backups"
        :loading="loading"
        density="compact"
        hover
        :items-per-page="-1"
        hide-default-footer
      >
        <!-- Status Column -->
        <template #item.status="{ item }">
          <v-chip :color="getStatusColor(item.status)" size="small" label>
            <v-icon :icon="getStatusIcon(item.status)" start size="x-small" />
            {{ item.status }}
          </v-chip>
        </template>

        <!-- Trigger Source Column -->
        <template #item.trigger_source="{ item }">
          <v-chip size="x-small" variant="outlined">
            {{ item.trigger_source }}
          </v-chip>
        </template>

        <!-- Size Column -->
        <template #item.file_size_mb="{ item }">
          <span class="text-caption">{{ formatSize(item.file_size_mb) }}</span>
        </template>

        <!-- Duration Column -->
        <template #item.duration_seconds="{ item }">
          <span class="text-caption">{{ formatDuration(item.duration_seconds) }}</span>
        </template>

        <!-- Created At Column -->
        <template #item.created_at="{ item }">
          <span class="text-caption">{{ formatDate(item.created_at) }}</span>
        </template>

        <!-- Actions Column -->
        <template #item.actions="{ item }">
          <div class="d-flex ga-1">
            <v-tooltip text="Download Backup" location="top">
              <template #activator="{ props }">
                <v-btn
                  v-bind="props"
                  icon="mdi-download"
                  size="x-small"
                  variant="text"
                  color="primary"
                  @click="downloadBackup(item)"
                />
              </template>
            </v-tooltip>

            <v-tooltip text="Restore Backup" location="top">
              <template #activator="{ props }">
                <v-btn
                  v-bind="props"
                  icon="mdi-database-import"
                  size="x-small"
                  variant="text"
                  color="success"
                  :disabled="item.status !== 'completed'"
                  @click="showRestoreDialog(item)"
                />
              </template>
            </v-tooltip>

            <v-tooltip text="View Details" location="top">
              <template #activator="{ props }">
                <v-btn
                  v-bind="props"
                  icon="mdi-information"
                  size="x-small"
                  variant="text"
                  color="info"
                  @click="showDetailsDialog(item)"
                />
              </template>
            </v-tooltip>

            <v-tooltip text="Delete Backup" location="top">
              <template #activator="{ props }">
                <v-btn
                  v-bind="props"
                  icon="mdi-delete"
                  size="x-small"
                  variant="text"
                  color="error"
                  @click="showDeleteDialog(item)"
                />
              </template>
            </v-tooltip>
          </div>
        </template>
      </v-data-table>
    </v-card>

    <!-- Create Backup Dialog -->
    <v-dialog v-model="showCreateDialog" max-width="600">
      <v-card>
        <v-card-title class="d-flex align-center">
          <v-icon class="mr-2" color="primary">mdi-database-plus</v-icon>
          Create Database Backup
        </v-card-title>
        <v-card-text>
          <v-alert type="info" variant="tonal" class="mb-4" density="compact">
            This will create a complete backup of the database. The process may take several
            minutes depending on database size.
          </v-alert>

          <v-text-field
            v-model="createForm.description"
            label="Description (optional)"
            density="compact"
            variant="outlined"
            placeholder="e.g., Before major update"
            class="mb-3"
          />

          <v-select
            v-model="createForm.compressionLevel"
            label="Compression Level"
            :items="compressionLevels"
            density="compact"
            variant="outlined"
            hint="Higher = better compression but slower"
            persistent-hint
            class="mb-3"
          />

          <v-select
            v-model="createForm.parallelJobs"
            label="Parallel Jobs"
            :items="parallelJobOptions"
            density="compact"
            variant="outlined"
            hint="More jobs = faster backup on multi-core systems"
            persistent-hint
            class="mb-3"
          />

          <v-switch
            v-model="createForm.includeLogs"
            label="Include system logs"
            density="compact"
            color="warning"
            hide-details
            class="mb-2"
          />

          <v-switch
            v-model="createForm.includeCache"
            label="Include cache tables"
            density="compact"
            color="warning"
            hide-details
          />
        </v-card-text>
        <v-card-actions>
          <v-spacer />
          <v-btn variant="text" @click="showCreateDialog = false">Cancel</v-btn>
          <v-btn
            color="primary"
            variant="elevated"
            :loading="creating"
            @click="createBackup"
          >
            Create Backup
          </v-btn>
        </v-card-actions>
      </v-card>
    </v-dialog>

    <!-- Restore Dialog -->
    <v-dialog v-model="showRestore" max-width="600">
      <v-card>
        <v-card-title class="d-flex align-center">
          <v-icon class="mr-2" color="warning">mdi-alert</v-icon>
          Restore Database Backup
        </v-card-title>
        <v-card-text>
          <v-alert type="warning" variant="tonal" prominent class="mb-4">
            <div class="text-body-2">
              <strong>⚠️ Warning:</strong> This will replace the current database with data from
              the selected backup. This action cannot be undone.
            </div>
          </v-alert>

          <div class="mb-4">
            <div class="text-subtitle-2 mb-2">Selected Backup:</div>
            <v-card variant="outlined" color="info">
              <v-card-text class="pa-3">
                <div class="text-body-2">
                  <strong>Filename:</strong> {{ selectedBackup?.filename }}
                </div>
                <div class="text-body-2">
                  <strong>Created:</strong> {{ formatDate(selectedBackup?.created_at) }}
                </div>
                <div class="text-body-2">
                  <strong>Size:</strong> {{ formatSize(selectedBackup?.file_size_mb) }}
                </div>
              </v-card-text>
            </v-card>
          </div>

          <v-switch
            v-model="restoreForm.createSafetyBackup"
            label="Create safety backup before restore (recommended)"
            density="compact"
            color="success"
            hide-details
            class="mb-2"
          />

          <v-switch
            v-model="restoreForm.runAnalyze"
            label="Run ANALYZE after restore (recommended)"
            density="compact"
            color="success"
            hide-details
          />
        </v-card-text>
        <v-card-actions>
          <v-spacer />
          <v-btn variant="text" @click="showRestore = false">Cancel</v-btn>
          <v-btn color="warning" variant="elevated" :loading="restoring" @click="restoreBackup">
            Restore Database
          </v-btn>
        </v-card-actions>
      </v-card>
    </v-dialog>

    <!-- Details Dialog -->
    <v-dialog v-model="showDetails" max-width="700">
      <v-card>
        <v-card-title class="d-flex align-center">
          <v-icon class="mr-2" color="info">mdi-information</v-icon>
          Backup Details
        </v-card-title>
        <v-card-text>
          <v-list density="compact">
            <v-list-item>
              <v-list-item-title>Filename</v-list-item-title>
              <v-list-item-subtitle>{{ selectedBackup?.filename }}</v-list-item-subtitle>
            </v-list-item>
            <v-list-item>
              <v-list-item-title>Status</v-list-item-title>
              <v-list-item-subtitle>
                <v-chip :color="getStatusColor(selectedBackup?.status)" size="small">
                  {{ selectedBackup?.status }}
                </v-chip>
              </v-list-item-subtitle>
            </v-list-item>
            <v-list-item>
              <v-list-item-title>File Size</v-list-item-title>
              <v-list-item-subtitle>{{ formatSize(selectedBackup?.file_size_mb) }}</v-list-item-subtitle>
            </v-list-item>
            <v-list-item>
              <v-list-item-title>Created</v-list-item-title>
              <v-list-item-subtitle>{{ formatDate(selectedBackup?.created_at) }}</v-list-item-subtitle>
            </v-list-item>
            <v-list-item>
              <v-list-item-title>Duration</v-list-item-title>
              <v-list-item-subtitle>{{ formatDuration(selectedBackup?.duration_seconds) }}</v-list-item-subtitle>
            </v-list-item>
            <v-list-item>
              <v-list-item-title>Trigger Source</v-list-item-title>
              <v-list-item-subtitle>{{ selectedBackup?.trigger_source }}</v-list-item-subtitle>
            </v-list-item>
            <v-list-item v-if="selectedBackup?.description">
              <v-list-item-title>Description</v-list-item-title>
              <v-list-item-subtitle>{{ selectedBackup?.description }}</v-list-item-subtitle>
            </v-list-item>
            <v-list-item>
              <v-list-item-title>SHA256 Checksum</v-list-item-title>
              <v-list-item-subtitle class="text-caption font-mono">
                {{ selectedBackup?.checksum_sha256 }}
              </v-list-item-subtitle>
            </v-list-item>
          </v-list>
        </v-card-text>
        <v-card-actions>
          <v-spacer />
          <v-btn variant="text" @click="showDetails = false">Close</v-btn>
        </v-card-actions>
      </v-card>
    </v-dialog>

    <!-- Delete Dialog -->
    <v-dialog v-model="showDelete" max-width="500">
      <v-card>
        <v-card-title class="d-flex align-center">
          <v-icon class="mr-2" color="error">mdi-delete</v-icon>
          Delete Backup
        </v-card-title>
        <v-card-text>
          <v-alert type="error" variant="tonal" class="mb-4" density="compact">
            This will permanently delete the backup file. This action cannot be undone.
          </v-alert>
          <div class="text-body-2">
            <strong>Filename:</strong> {{ selectedBackup?.filename }}
          </div>
        </v-card-text>
        <v-card-actions>
          <v-spacer />
          <v-btn variant="text" @click="showDelete = false">Cancel</v-btn>
          <v-btn color="error" variant="elevated" :loading="deleting" @click="deleteBackup">
            Delete
          </v-btn>
        </v-card-actions>
      </v-card>
    </v-dialog>
  </v-container>
</template>

<script setup>
/**
 * Admin Backups Management Page
 * Following Material Design 3 principles with compact density
 */

import { ref, computed, onMounted } from 'vue'
import { useAuthStore } from '@/stores/auth'
import AdminHeader from '@/components/admin/AdminHeader.vue'
import AdminStatsCard from '@/components/admin/AdminStatsCard.vue'

const authStore = useAuthStore()

// State
const stats = ref({
  totalBackups: 0,
  latestBackupAge: '—',
  totalSize: 0,
  retentionDays: 7
})

const backups = ref([])
const selectedBackup = ref(null)

const statsLoading = ref(true)
const loading = ref(false)
const creating = ref(false)
const restoring = ref(false)
const deleting = ref(false)
const cleaning = ref(false)

// Dialogs
const showCreateDialog = ref(false)
const showRestore = ref(false)
const showDetails = ref(false)
const showDelete = ref(false)

// Filters
const filters = ref({
  status: null,
  triggerSource: null,
  timeRange: 'all'
})

const searchQuery = ref('')

// Pagination
const currentPage = ref(1)
const itemsPerPage = ref(25)
const totalBackups = ref(0)

// Forms
const createForm = ref({
  description: '',
  includeLogs: false,
  includeCache: false,
  compressionLevel: 6,
  parallelJobs: 2
})

const restoreForm = ref({
  createSafetyBackup: true,
  runAnalyze: true
})

// Options
const statusOptions = [
  { title: 'All Statuses', value: null },
  { title: 'Completed', value: 'completed' },
  { title: 'Running', value: 'running' },
  { title: 'Failed', value: 'failed' },
  { title: 'Pending', value: 'pending' }
]

const triggerOptions = [
  { title: 'All Triggers', value: null },
  { title: 'Manual API', value: 'manual_api' },
  { title: 'Scheduled Cron', value: 'scheduled_cron' },
  { title: 'Pre-Restore Safety', value: 'pre_restore_safety' }
]

const timeRanges = [
  { title: 'All Time', value: 'all' },
  { title: 'Last 24 Hours', value: '24h' },
  { title: 'Last 7 Days', value: '7d' },
  { title: 'Last 30 Days', value: '30d' }
]

const compressionLevels = [
  { title: '0 - No compression (fastest)', value: 0 },
  { title: '1 - Minimal compression', value: 1 },
  { title: '3 - Light compression', value: 3 },
  { title: '6 - Balanced (default)', value: 6 },
  { title: '9 - Maximum compression (slowest)', value: 9 }
]

const parallelJobOptions = [
  { title: '1 - Single thread', value: 1 },
  { title: '2 - Two threads (default)', value: 2 },
  { title: '4 - Four threads', value: 4 },
  { title: '8 - Eight threads', value: 8 }
]

// Table headers
const headers = [
  { title: 'Filename', value: 'filename', sortable: true },
  { title: 'Status', value: 'status', sortable: true },
  { title: 'Trigger', value: 'trigger_source', sortable: false },
  { title: 'Size', value: 'file_size_mb', sortable: true },
  { title: 'Duration', value: 'duration_seconds', sortable: true },
  { title: 'Created', value: 'created_at', sortable: true },
  { title: 'Actions', value: 'actions', sortable: false, align: 'center', width: 160 }
]

// Computed
const pageCount = computed(() => Math.ceil(totalBackups.value / itemsPerPage.value))

const pageRangeText = computed(() => {
  const start = (currentPage.value - 1) * itemsPerPage.value + 1
  const end = Math.min(currentPage.value * itemsPerPage.value, totalBackups.value)
  return `${start}-${end} of ${totalBackups.value}`
})

// Methods
const loadStats = async () => {
  statsLoading.value = true
  try {
    const response = await fetch('/api/admin/backups/stats', {
      headers: {
        Authorization: `Bearer ${authStore.accessToken}`
      }
    })
    if (!response.ok) throw new Error('Failed to load stats')
    const data = await response.json()

    stats.value = {
      totalBackups: data.total_backups || 0,
      latestBackupAge: formatRelativeTime(data.latest_backup_date),
      totalSize: data.total_size_gb * 1024 * 1024 * 1024 || 0,
      retentionDays: data.retention_days || 7
    }
  } catch (error) {
    window.logService.error('Failed to load backup stats:', error)
  } finally {
    statsLoading.value = false
  }
}

const loadBackups = async () => {
  loading.value = true
  try {
    const params = new URLSearchParams({
      limit: itemsPerPage.value,
      offset: (currentPage.value - 1) * itemsPerPage.value
    })

    if (filters.value.status) params.append('status', filters.value.status)
    if (filters.value.triggerSource) params.append('trigger_source', filters.value.triggerSource)
    if (searchQuery.value) params.append('search', searchQuery.value)

    const response = await fetch(`/api/admin/backups?${params}`, {
      headers: {
        Authorization: `Bearer ${authStore.accessToken}`
      }
    })
    if (!response.ok) throw new Error('Failed to load backups')
    const data = await response.json()

    backups.value = data.backups || []
    totalBackups.value = data.total || 0
  } catch (error) {
    window.logService.error('Failed to load backups:', error)
  } finally {
    loading.value = false
  }
}

const createBackup = async () => {
  creating.value = true
  try {
    const response = await fetch('/api/admin/backups/create', {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        Authorization: `Bearer ${authStore.accessToken}`
      },
      body: JSON.stringify({
        description: createForm.value.description,
        include_logs: createForm.value.includeLogs,
        include_cache: createForm.value.includeCache,
        compression_level: createForm.value.compressionLevel,
        parallel_jobs: createForm.value.parallelJobs
      })
    })

    if (!response.ok) throw new Error('Failed to create backup')
    const result = await response.json()

    window.logService.success('Backup created successfully')
    showCreateDialog.value = false
    createForm.value = {
      description: '',
      includeLogs: false,
      includeCache: false,
      compressionLevel: 6,
      parallelJobs: 2
    }

    await loadBackups()
    await loadStats()
  } catch (error) {
    window.logService.error('Failed to create backup:', error)
  } finally {
    creating.value = false
  }
}

const showRestoreDialog = backup => {
  selectedBackup.value = backup
  showRestore.value = true
}

const restoreBackup = async () => {
  restoring.value = true
  try {
    const response = await fetch(`/api/admin/backups/restore/${selectedBackup.value.id}`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        Authorization: `Bearer ${authStore.accessToken}`
      },
      body: JSON.stringify({
        create_safety_backup: restoreForm.value.createSafetyBackup,
        run_analyze: restoreForm.value.runAnalyze
      })
    })

    if (!response.ok) throw new Error('Failed to restore backup')

    window.logService.success('Database restored successfully')
    showRestore.value = false
    await loadBackups()
    await loadStats()
  } catch (error) {
    window.logService.error('Failed to restore backup:', error)
  } finally {
    restoring.value = false
  }
}

const downloadBackup = async backup => {
  try {
    const response = await fetch(`/api/admin/backups/${backup.id}/download`, {
      headers: {
        Authorization: `Bearer ${authStore.accessToken}`
      }
    })

    if (!response.ok) throw new Error('Failed to download backup')

    const blob = await response.blob()
    const url = URL.createObjectURL(blob)
    const a = document.createElement('a')
    a.href = url
    a.download = backup.filename
    a.click()
    URL.revokeObjectURL(url)

    window.logService.success('Backup downloaded successfully')
  } catch (error) {
    window.logService.error('Failed to download backup:', error)
  }
}

const showDetailsDialog = backup => {
  selectedBackup.value = backup
  showDetails.value = true
}

const showDeleteDialog = backup => {
  selectedBackup.value = backup
  showDelete.value = true
}

const deleteBackup = async () => {
  deleting.value = true
  try {
    const response = await fetch(`/api/admin/backups/${selectedBackup.value.id}`, {
      method: 'DELETE',
      headers: {
        Authorization: `Bearer ${authStore.accessToken}`
      }
    })

    if (!response.ok) throw new Error('Failed to delete backup')

    window.logService.success('Backup deleted successfully')
    showDelete.value = false
    await loadBackups()
    await loadStats()
  } catch (error) {
    window.logService.error('Failed to delete backup:', error)
  } finally {
    deleting.value = false
  }
}

const cleanupOldBackups = async () => {
  cleaning.value = true
  try {
    const response = await fetch('/api/admin/backups/cleanup', {
      method: 'POST',
      headers: {
        Authorization: `Bearer ${authStore.accessToken}`
      }
    })

    if (!response.ok) throw new Error('Failed to cleanup old backups')
    const result = await response.json()

    window.logService.success(`Deleted ${result.entries_cleared} old backup(s)`)
    await loadBackups()
    await loadStats()
  } catch (error) {
    window.logService.error('Failed to cleanup old backups:', error)
  } finally {
    cleaning.value = false
  }
}

const clearFilters = () => {
  filters.value = {
    status: null,
    triggerSource: null,
    timeRange: 'all'
  }
  searchQuery.value = ''
  loadBackups()
}

// Helper functions
const getStatusColor = status => {
  const colors = {
    completed: 'success',
    running: 'info',
    failed: 'error',
    pending: 'warning',
    restored: 'purple'
  }
  return colors[status] || 'grey'
}

const getStatusIcon = status => {
  const icons = {
    completed: 'mdi-check-circle',
    running: 'mdi-progress-clock',
    failed: 'mdi-alert-circle',
    pending: 'mdi-clock-outline',
    restored: 'mdi-database-import'
  }
  return icons[status] || 'mdi-help-circle'
}

const formatSize = sizeMb => {
  if (!sizeMb) return '—'
  if (sizeMb >= 1024) return `${(sizeMb / 1024).toFixed(2)} GB`
  return `${sizeMb.toFixed(2)} MB`
}

const formatDuration = seconds => {
  if (!seconds) return '—'
  if (seconds < 60) return `${seconds}s`
  const minutes = Math.floor(seconds / 60)
  const secs = seconds % 60
  return `${minutes}m ${secs}s`
}

const formatDate = date => {
  if (!date) return '—'
  return new Date(date).toLocaleString()
}

const formatRelativeTime = date => {
  if (!date) return '—'
  const now = new Date()
  const then = new Date(date)
  const diffMs = now - then
  const diffHours = Math.floor(diffMs / (1000 * 60 * 60))

  if (diffHours < 1) return 'Just now'
  if (diffHours < 24) return `${diffHours}h ago`
  const diffDays = Math.floor(diffHours / 24)
  if (diffDays < 7) return `${diffDays}d ago`
  const diffWeeks = Math.floor(diffDays / 7)
  return `${diffWeeks}w ago`
}

// Lifecycle
onMounted(() => {
  loadStats()
  loadBackups()
})
</script>

<style scoped>
.font-mono {
  font-family: 'Courier New', monospace;
}

.border-b {
  border-bottom: thin solid rgba(var(--v-border-color), var(--v-border-opacity));
}
</style>
```

---

### 3. Add Router Route

**Location**: `/frontend/src/router/index.js`

**Add after line 96**:

```javascript
{
  path: '/admin/backups',
  name: 'admin-backups',
  component: () => import('../views/admin/AdminBackups.vue'),
  meta: { requiresAuth: true, requiresAdmin: true }
}
```

---

## Design Consistency Checklist

- [x] Uses `AdminHeader` with title, subtitle, back-route
- [x] 4 `AdminStatsCard` components in responsive grid (cols="12" sm="6" md="3")
- [x] Filters section with `density="compact"` and `variant="outlined"`
- [x] Data table with top pagination controls
- [x] Action buttons with `prepend-icon` and `size="small"`
- [x] Color scheme matches existing palette (primary, success, info, warning, error, purple, indigo)
- [x] Material Design Icons (`mdi-*`)
- [x] Dialogs for destructive actions (restore, delete)
- [x] Loading states on all async operations
- [x] Tooltips for icon-only buttons
- [x] Responsive layout (cols="12" md="6", etc.)
- [x] Consistent spacing (`class="mb-3"`, `class="mb-6"`)
- [x] Alert components for important warnings
- [x] `v-chip` for status indicators

---

## Color Palette Used

| Element | Color | Usage |
|---------|-------|-------|
| Primary Actions | `primary` (blue) | Create, Apply Filters |
| Success States | `success` (green) | Completed, Restore (positive) |
| Info/Metadata | `info` (cyan) | Running status, Details |
| Warnings | `warning` (orange) | Pending, Cleanup, Restore dialog |
| Errors | `error` (red) | Failed status, Delete |
| Storage/Data | `purple` | Total size stat, Restored status |
| Backups Theme | `indigo` | Dashboard card color |

---

## Icon Mapping

| Element | Icon | Purpose |
|---------|------|---------|
| Dashboard Card | `mdi-database-export` | Backups section |
| Create Backup | `mdi-database-plus` | Add new backup |
| Download | `mdi-download` | Download backup file |
| Restore | `mdi-database-import` | Restore from backup |
| Details | `mdi-information` | View backup details |
| Delete | `mdi-delete` | Remove backup |
| Cleanup | `mdi-delete-sweep` | Bulk cleanup |
| Status - Completed | `mdi-check-circle` | Success indicator |
| Status - Running | `mdi-progress-clock` | In progress |
| Status - Failed | `mdi-alert-circle` | Error indicator |
| Status - Pending | `mdi-clock-outline` | Queued |

---

## Implementation Checklist

### Phase 1: Dashboard Integration (30 min)
- [ ] Add `backups` section to `adminSections` array in `AdminDashboard.vue`
- [ ] Test card navigation to `/admin/backups`
- [ ] Verify card styling matches other sections

### Phase 2: View Creation (3-4 hours)
- [ ] Create `frontend/src/views/admin/AdminBackups.vue`
- [ ] Add router route in `index.js`
- [ ] Implement stats cards with API integration
- [ ] Implement filters section
- [ ] Implement data table with pagination
- [ ] Implement create backup dialog
- [ ] Implement restore dialog
- [ ] Implement details dialog
- [ ] Implement delete dialog

### Phase 3: API Integration (2-3 hours)
- [ ] Connect to `/api/admin/backups/stats` endpoint
- [ ] Connect to `/api/admin/backups` list endpoint
- [ ] Connect to `/api/admin/backups/create` endpoint
- [ ] Connect to `/api/admin/backups/restore/:id` endpoint
- [ ] Connect to `/api/admin/backups/:id/download` endpoint
- [ ] Connect to `/api/admin/backups/:id` delete endpoint
- [ ] Connect to `/api/admin/backups/cleanup` endpoint
- [ ] Add error handling and loading states

### Phase 4: Polish & Testing (1 hour)
- [ ] Test all dialogs and confirmations
- [ ] Test pagination and filtering
- [ ] Test responsive layout on mobile
- [ ] Verify color consistency
- [ ] Verify icon consistency
- [ ] Test with real backend API (once implemented)

---

## Total Effort: 1-2 Days

- **Phase 1**: 30 minutes
- **Phase 2**: 3-4 hours
- **Phase 3**: 2-3 hours
- **Phase 4**: 1 hour

**Total**: 6.5-8.5 hours (1-2 days with testing)
