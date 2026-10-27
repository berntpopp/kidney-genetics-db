<template>
  <div :class="PAGE_CONTAINER">
    <!-- Header -->
    <AdminHeader title="Database Backups" subtitle="Create, manage, and restore database backups">
      <template #actions>
        <Button
          variant="outline"
          class="text-danger hover:text-danger"
          :disabled="cleanupLoading || stats.retentionDays == null"
          @click="dialogs.cleanup = true"
        >
          <Trash class="size-4" aria-hidden="true" />
          Cleanup Old
        </Button>
        <Button :disabled="apiLoading" @click="dialogs.create = true">
          <DatabaseBackup class="size-4" aria-hidden="true" />
          Create Backup
        </Button>
      </template>
    </AdminHeader>

    <!-- Stats Overview -->
    <div class="mb-6 grid grid-cols-2 gap-3 md:grid-cols-4">
      <AdminStatsCard
        title="Total Backups"
        :value="stats.totalBackups"
        :loading="statsLoading"
        :icon="Database"
      />
      <AdminStatsCard
        title="Latest Backup"
        :value="stats.latestBackupAge"
        :loading="statsLoading"
        :icon="Clock"
      />
      <AdminStatsCard
        title="Total Size"
        :value="stats.totalSize"
        :loading="statsLoading"
        format="bytes"
        :icon="HardDrive"
      />
      <AdminStatsCard
        title="Retention Days"
        :value="stats.retentionDays"
        :loading="statsLoading"
        :icon="CalendarClock"
      />
    </div>

    <!-- Filters -->
    <BackupFilters
      v-model:filters="filters"
      v-model:search-query="searchQuery"
      :loading="apiLoading"
      @apply="loadBackups"
      @clear="clearFilters"
    />

    <!-- Backups Table -->
    <Card>
      <CardContent v-if="totalBackups > 0" class="p-2 border-b">
        <div class="flex flex-wrap items-center justify-between gap-2">
          <div class="flex items-center gap-4">
            <span class="text-sm">
              <span class="font-semibold tabular-nums">{{ totalBackups.toLocaleString() }}</span>
              <span class="text-muted-foreground"> backups</span>
            </span>
            <span class="text-sm text-muted-foreground tabular-nums">{{ pageRangeText }}</span>
          </div>
          <div class="flex items-center gap-2">
            <span class="mr-2 text-xs text-muted-foreground">Per page:</span>
            <Select v-model="itemsPerPage" @update:model-value="loadBackups">
              <SelectTrigger aria-label="Per page" class="w-[100px]">
                <SelectValue />
              </SelectTrigger>
              <SelectContent>
                <SelectItem v-for="n in [10, 25, 50, 100]" :key="n" :value="n">{{ n }}</SelectItem>
              </SelectContent>
            </Select>
            <div class="flex items-center gap-1">
              <Button
                aria-label="Previous page"
                variant="outline"
                size="icon"
                :disabled="currentPage <= 1"
                @click="
                  () => {
                    currentPage--
                    loadBackups()
                  }
                "
              >
                <ChevronLeft class="size-4" aria-hidden="true" />
              </Button>
              <span class="px-2 text-sm text-muted-foreground tabular-nums"
                >{{ currentPage }} / {{ pageCount || 1 }}</span
              >
              <Button
                aria-label="Next page"
                variant="outline"
                size="icon"
                :disabled="currentPage >= pageCount"
                @click="
                  () => {
                    currentPage++
                    loadBackups()
                  }
                "
              >
                <ChevronRight class="size-4" aria-hidden="true" />
              </Button>
            </div>
          </div>
        </div>
      </CardContent>

      <DataState
        :loading="listLoading && !backups.length"
        :error="listError"
        error-title="Could not load backups"
        :empty="!backups.length"
        :empty-message="
          hasFilters
            ? 'No backups match these filters.'
            : 'No backups yet. Create one before risky operations such as a full pipeline run.'
        "
        class="m-4"
        @retry="loadBackups"
      >
        <template #loading>
          <div class="space-y-3 p-4" aria-hidden="true">
            <div
              v-for="i in 4"
              :key="i"
              class="h-8 rounded-md bg-muted motion-safe:animate-pulse"
            />
          </div>
        </template>
        <Table>
          <TableHeader>
            <TableRow>
              <TableHead>Filename</TableHead>
              <TableHead>Status</TableHead>
              <TableHead>Trigger</TableHead>
              <TableHead class="text-right">Size</TableHead>
              <TableHead class="text-right">Duration</TableHead>
              <TableHead>Created</TableHead>
              <TableHead><span class="sr-only">Actions</span></TableHead>
            </TableRow>
          </TableHeader>
          <TableBody>
            <TableRow v-for="item in backups" :key="item.id">
              <TableCell class="text-sm">{{ item.filename }}</TableCell>
              <TableCell>
                <StatusBadge :status="item.status" />
              </TableCell>
              <TableCell>
                <Chip kind="neutral" :label="item.trigger_source" />
              </TableCell>
              <TableCell class="text-right text-xs tabular-nums">{{
                formatSize(item.file_size_mb)
              }}</TableCell>
              <TableCell class="text-right text-xs tabular-nums">{{
                formatDuration(item.duration_seconds)
              }}</TableCell>
              <TableCell class="text-xs tabular-nums">{{ formatDate(item.created_at) }}</TableCell>
              <TableCell>
                <div class="flex justify-end gap-1">
                  <Tooltip v-for="action in rowActions(item)" :key="action.label">
                    <TooltipTrigger as-child>
                      <Button
                        :aria-label="`${action.label} ${item.filename}`"
                        variant="ghost"
                        size="icon-sm"
                        :class="action.danger && 'text-danger hover:text-danger'"
                        :disabled="action.disabled"
                        @click="action.run(item)"
                      >
                        <component :is="action.icon" class="size-4" aria-hidden="true" />
                      </Button>
                    </TooltipTrigger>
                    <TooltipContent>{{ action.label }}</TooltipContent>
                  </Tooltip>
                </div>
              </TableCell>
            </TableRow>
          </TableBody>
        </Table>
      </DataState>
    </Card>

    <!-- Dialogs -->
    <BackupCreateDialog
      v-model="dialogs.create"
      :loading="apiLoading"
      @create="handleCreateBackup"
    />

    <BackupRestoreDialog
      v-model="dialogs.restore"
      :backup="selectedBackup"
      :loading="apiLoading"
      @restore="handleRestoreBackup"
    />

    <BackupDetailsDialog v-model="dialogs.details" :backup="selectedBackup" />

    <BackupDeleteDialog
      v-model="dialogs.delete"
      :backup="selectedBackup"
      :loading="apiLoading"
      @delete="handleDeleteBackup"
    />

    <AlertDialog v-model:open="dialogs.cleanup">
      <AlertDialogContent>
        <AlertDialogHeader>
          <AlertDialogTitle>Delete expired backups?</AlertDialogTitle>
          <AlertDialogDescription>
            This permanently deletes every completed backup whose expiry date is more than
            {{ stats.retentionDays }} days in the past (the retention period), including its file.
            This action cannot be undone.
          </AlertDialogDescription>
        </AlertDialogHeader>
        <AlertDialogFooter>
          <AlertDialogCancel>Cancel</AlertDialogCancel>
          <AlertDialogAction
            :class="buttonVariants({ variant: 'destructive' })"
            :disabled="cleanupLoading"
            @click="handleCleanupOldBackups"
          >
            Delete Expired Backups
          </AlertDialogAction>
        </AlertDialogFooter>
      </AlertDialogContent>
    </AlertDialog>
  </div>
</template>

<script setup>
/**
 * Admin Backups Management Page (Refactored)
 *
 * Following Vue 3 best practices:
 * - Component under 300 lines
 * - Separated dialogs into individual components
 * - Extracted composables for API and formatters
 * - Single responsibility principle
 */

import { ref, computed, onMounted } from 'vue'
import {
  CalendarClock,
  ChevronLeft,
  ChevronRight,
  Clock,
  Database,
  DatabaseBackup,
  Download,
  HardDrive,
  Info,
  Trash,
  Trash2
} from 'lucide-vue-next'
import { toast } from 'vue-sonner'
import AdminHeader from '@/components/admin/AdminHeader.vue'
import { Chip, DataState, PAGE_CONTAINER, StatusBadge } from '@/components/shared'
import AdminStatsCard from '@/components/admin/AdminStatsCard.vue'
import BackupCreateDialog from '@/components/admin/backups/BackupCreateDialog.vue'
import BackupRestoreDialog from '@/components/admin/backups/BackupRestoreDialog.vue'
import BackupDetailsDialog from '@/components/admin/backups/BackupDetailsDialog.vue'
import BackupDeleteDialog from '@/components/admin/backups/BackupDeleteDialog.vue'
import BackupFilters from '@/components/admin/backups/BackupFilters.vue'

import { useBackupApi } from '@/composables/useBackupApi'
import { useBackupFormatters } from '@/composables/useBackupFormatters'

import { Card, CardContent } from '@/components/ui/card'
import { Button, buttonVariants } from '@/components/ui/button'
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow
} from '@/components/ui/table'
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue
} from '@/components/ui/select'
import { Tooltip, TooltipContent, TooltipTrigger } from '@/components/ui/tooltip'
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

// Composables
const {
  loading: apiLoading,
  loadStats: apiLoadStats,
  loadBackups: apiLoadBackups,
  createBackup: apiCreateBackup,
  restoreBackup: apiRestoreBackup,
  downloadBackup: apiDownloadBackup,
  deleteBackup: apiDeleteBackup,
  cleanupOldBackups: apiCleanupOldBackups
} = useBackupApi()

const { formatSize, formatDuration, formatDate, formatRelativeTime } = useBackupFormatters()

// State
const stats = ref({
  totalBackups: 0,
  latestBackupAge: '—',
  totalSize: 0,
  retentionDays: null // unknown until the stats load; cleanup stays disabled
})

const backups = ref([])
const selectedBackup = ref(null)
const statsLoading = ref(true)
const cleanupLoading = ref(false)

// Dialogs
const dialogs = ref({
  create: false,
  restore: false,
  details: false,
  delete: false,
  cleanup: false
})

// Filters & Pagination
const filters = ref({
  status: null,
  triggerSource: null,
  timeRange: 'all'
})

const searchQuery = ref('')
const currentPage = ref(1)
const itemsPerPage = ref(25)
const totalBackups = ref(0)

// Computed
const pageCount = computed(() => Math.ceil(totalBackups.value / itemsPerPage.value))

const pageRangeText = computed(() => {
  const start = (currentPage.value - 1) * itemsPerPage.value + 1
  const end = Math.min(currentPage.value * itemsPerPage.value, totalBackups.value)
  return `${start}-${end} of ${totalBackups.value}`
})

const listLoading = ref(false)
const listError = ref(null)
const hasFilters = computed(
  () => !!(searchQuery.value || filters.value.status || filters.value.triggerSource)
)

const rowActions = item => [
  { label: 'Download backup', icon: Download, run: handleDownloadBackup },
  {
    label: 'Restore backup',
    icon: DatabaseBackup,
    run: showRestoreDialog,
    disabled: item.status !== 'completed'
  },
  { label: 'Backup details', icon: Info, run: showDetailsDialog },
  { label: 'Delete backup', icon: Trash2, run: showDeleteDialog, danger: true }
]

// Methods
const loadStats = async () => {
  statsLoading.value = true
  try {
    const data = await apiLoadStats()
    stats.value = {
      totalBackups: data.total_backups || 0,
      latestBackupAge: formatRelativeTime(data.latest_backup_date),
      totalSize: (data.total_size_gb || 0) * 1024 * 1024 * 1024,
      retentionDays: data.retention_days ?? null
    }
  } catch (error) {
    window.logService.error('Failed to load backup stats:', error)
  } finally {
    statsLoading.value = false
  }
}

const loadBackups = async () => {
  listLoading.value = true
  listError.value = null
  try {
    const data = await apiLoadBackups({
      limit: itemsPerPage.value,
      offset: (currentPage.value - 1) * itemsPerPage.value,
      status: filters.value.status,
      triggerSource: filters.value.triggerSource,
      search: searchQuery.value
    })

    backups.value = data.backups || []
    totalBackups.value = data.total || 0
  } catch (error) {
    window.logService.error('Failed to load backups:', error)
    listError.value = error.message || 'Request failed'
  } finally {
    listLoading.value = false
  }
}

const handleCreateBackup = async formData => {
  try {
    await apiCreateBackup(formData)
    window.logService.info('Backup created successfully')
    dialogs.value.create = false
    await Promise.all([loadBackups(), loadStats()])
  } catch (error) {
    window.logService.error('Failed to create backup:', error)
  }
}

const showRestoreDialog = backup => {
  selectedBackup.value = backup
  dialogs.value.restore = true
}

const handleRestoreBackup = async options => {
  try {
    await apiRestoreBackup(selectedBackup.value.id, options)
    window.logService.info('Database restored successfully')
    dialogs.value.restore = false
    await Promise.all([loadBackups(), loadStats()])
  } catch (error) {
    window.logService.error('Failed to restore backup:', error)
  }
}

const handleDownloadBackup = async backup => {
  try {
    await apiDownloadBackup(backup)
    window.logService.info('Backup downloaded successfully')
  } catch (error) {
    window.logService.error('Failed to download backup:', error)
  }
}

const showDetailsDialog = backup => {
  selectedBackup.value = backup
  dialogs.value.details = true
}

const showDeleteDialog = backup => {
  selectedBackup.value = backup
  dialogs.value.delete = true
}

const handleDeleteBackup = async () => {
  try {
    await apiDeleteBackup(selectedBackup.value.id)
    window.logService.info('Backup deleted successfully')
    dialogs.value.delete = false
    await Promise.all([loadBackups(), loadStats()])
  } catch (error) {
    window.logService.error('Failed to delete backup:', error)
  }
}

const handleCleanupOldBackups = async () => {
  cleanupLoading.value = true
  try {
    const result = await apiCleanupOldBackups()
    toast.success(`Deleted ${result.deleted_count || 0} expired backup(s)`, { duration: 5000 })
    await Promise.all([loadBackups(), loadStats()])
  } catch (error) {
    window.logService.error('Failed to cleanup old backups:', error)
    toast.error('Failed to delete expired backups', { duration: Infinity })
  } finally {
    cleanupLoading.value = false
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

// Lifecycle
onMounted(() => {
  loadStats()
  loadBackups()
})
</script>
