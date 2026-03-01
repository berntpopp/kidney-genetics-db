<template>
  <div class="container mx-auto px-4 py-6">
    <!-- Header -->
    <AdminHeader
      title="Database Backups"
      subtitle="Create, manage, and restore database backups"
      icon="mdi-database-export"
      icon-color="blue-grey"
      :breadcrumbs="ADMIN_BREADCRUMBS.backups"
    >
      <template #actions>
        <Button :disabled="apiLoading" @click="dialogs.create = true">
          <DatabaseBackup class="mr-2 size-4" />
          Create Backup
        </Button>
      </template>
    </AdminHeader>

    <!-- Stats Overview -->
    <div class="mb-6 grid grid-cols-1 gap-4 sm:grid-cols-2 md:grid-cols-4">
      <AdminStatsCard
        title="Total Backups"
        :value="stats.totalBackups"
        :loading="statsLoading"
        icon="mdi-database-outline"
        color="primary"
      />
      <AdminStatsCard
        title="Latest Backup"
        :value="stats.latestBackupAge"
        :loading="statsLoading"
        icon="mdi-clock-outline"
        color="info"
      />
      <AdminStatsCard
        title="Total Size"
        :value="stats.totalSize"
        :loading="statsLoading"
        format="bytes"
        icon="mdi-harddisk"
        color="purple"
      />
      <AdminStatsCard
        title="Retention Days"
        :value="stats.retentionDays"
        :loading="statsLoading"
        icon="mdi-calendar-clock"
        color="warning"
      />
    </div>

    <!-- Filters -->
    <BackupFilters
      v-model:filters="filters"
      v-model:search-query="searchQuery"
      :loading="apiLoading"
      :cleanup-loading="cleanupLoading"
      @apply="loadBackups"
      @clear="clearFilters"
      @cleanup="handleCleanupOldBackups"
    />

    <!-- Backups Table -->
    <Card>
      <CardContent class="p-2 border-b">
        <div class="flex items-center justify-between">
          <div class="flex items-center gap-4">
            <span class="text-sm">
              <span class="font-bold">{{ totalBackups }}</span>
              <span class="text-muted-foreground"> Backups</span>
            </span>
            <span class="text-sm text-muted-foreground">{{ pageRangeText }}</span>
          </div>
          <div class="flex items-center gap-2">
            <span class="mr-2 text-xs text-muted-foreground">Per page:</span>
            <Select v-model="itemsPerPage" @update:model-value="loadBackups">
              <SelectTrigger class="w-[100px]">
                <SelectValue />
              </SelectTrigger>
              <SelectContent>
                <SelectItem v-for="n in [10, 25, 50, 100]" :key="n" :value="n">{{ n }}</SelectItem>
              </SelectContent>
            </Select>
            <div class="flex items-center gap-1">
              <Button
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
                <ChevronLeft class="size-4" />
              </Button>
              <span class="px-2 text-sm text-muted-foreground"
                >{{ currentPage }} / {{ pageCount || 1 }}</span
              >
              <Button
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
                <ChevronRight class="size-4" />
              </Button>
            </div>
          </div>
        </div>
      </CardContent>

      <!-- Data Table -->
      <Table>
        <TableHeader>
          <TableRow>
            <TableHead>Filename</TableHead>
            <TableHead>Status</TableHead>
            <TableHead>Trigger</TableHead>
            <TableHead>Size</TableHead>
            <TableHead>Duration</TableHead>
            <TableHead>Created</TableHead>
            <TableHead class="text-center">Actions</TableHead>
          </TableRow>
        </TableHeader>
        <TableBody>
          <TableRow v-if="apiLoading">
            <TableCell :colspan="7" class="text-center py-8">
              <div class="flex justify-center">
                <div
                  class="h-6 w-6 animate-spin rounded-full border-2 border-primary border-t-transparent"
                />
              </div>
            </TableCell>
          </TableRow>
          <TableRow v-else-if="backups.length === 0">
            <TableCell :colspan="7" class="text-center py-8 text-muted-foreground">
              No backups found
            </TableCell>
          </TableRow>
          <TableRow v-for="item in backups" :key="item.id" class="hover:bg-muted/50">
            <TableCell class="text-sm">{{ item.filename }}</TableCell>
            <TableCell>
              <Badge :variant="getStatusVariant(item.status)">
                {{ item.status }}
              </Badge>
            </TableCell>
            <TableCell>
              <Badge variant="outline" class="text-xs">{{ item.trigger_source }}</Badge>
            </TableCell>
            <TableCell class="text-xs">{{ formatSize(item.file_size_mb) }}</TableCell>
            <TableCell class="text-xs">{{ formatDuration(item.duration_seconds) }}</TableCell>
            <TableCell class="text-xs">{{ formatDate(item.created_at) }}</TableCell>
            <TableCell>
              <div class="flex justify-center gap-1">
                <Tooltip>
                  <TooltipTrigger as-child>
                    <Button
                      variant="ghost"
                      size="icon"
                      class="h-8 w-8"
                      @click="handleDownloadBackup(item)"
                    >
                      <Download class="size-4 text-primary" />
                    </Button>
                  </TooltipTrigger>
                  <TooltipContent>Download Backup</TooltipContent>
                </Tooltip>

                <Tooltip>
                  <TooltipTrigger as-child>
                    <Button
                      variant="ghost"
                      size="icon"
                      class="h-8 w-8"
                      :disabled="item.status !== 'completed'"
                      @click="showRestoreDialog(item)"
                    >
                      <DatabaseBackup class="size-4 text-green-600" />
                    </Button>
                  </TooltipTrigger>
                  <TooltipContent>Restore Backup</TooltipContent>
                </Tooltip>

                <Tooltip>
                  <TooltipTrigger as-child>
                    <Button
                      variant="ghost"
                      size="icon"
                      class="h-8 w-8"
                      @click="showDetailsDialog(item)"
                    >
                      <Info class="size-4 text-blue-500" />
                    </Button>
                  </TooltipTrigger>
                  <TooltipContent>View Details</TooltipContent>
                </Tooltip>

                <Tooltip>
                  <TooltipTrigger as-child>
                    <Button
                      variant="ghost"
                      size="icon"
                      class="h-8 w-8"
                      @click="showDeleteDialog(item)"
                    >
                      <Trash2 class="size-4 text-destructive" />
                    </Button>
                  </TooltipTrigger>
                  <TooltipContent>Delete Backup</TooltipContent>
                </Tooltip>
              </div>
            </TableCell>
          </TableRow>
        </TableBody>
      </Table>
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
import { Download, Info, Trash2, ChevronLeft, ChevronRight, DatabaseBackup } from 'lucide-vue-next'
import AdminHeader from '@/components/admin/AdminHeader.vue'
import AdminStatsCard from '@/components/admin/AdminStatsCard.vue'
import BackupCreateDialog from '@/components/admin/backups/BackupCreateDialog.vue'
import BackupRestoreDialog from '@/components/admin/backups/BackupRestoreDialog.vue'
import BackupDetailsDialog from '@/components/admin/backups/BackupDetailsDialog.vue'
import BackupDeleteDialog from '@/components/admin/backups/BackupDeleteDialog.vue'
import BackupFilters from '@/components/admin/backups/BackupFilters.vue'

import { useBackupApi } from '@/composables/useBackupApi'
import { useBackupFormatters } from '@/composables/useBackupFormatters'
import { ADMIN_BREADCRUMBS } from '@/utils/adminBreadcrumbs'

import { Card, CardContent } from '@/components/ui/card'
import { Button } from '@/components/ui/button'
import { Badge } from '@/components/ui/badge'
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
  retentionDays: 7
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
  delete: false
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

const getStatusVariant = status => {
  const variants = {
    completed: 'default',
    running: 'secondary',
    failed: 'destructive',
    pending: 'outline'
  }
  return variants[status] || 'secondary'
}

// Methods
const loadStats = async () => {
  statsLoading.value = true
  try {
    const data = await apiLoadStats()
    stats.value = {
      totalBackups: data.total_backups || 0,
      latestBackupAge: formatRelativeTime(data.latest_backup_date),
      totalSize: (data.total_size_gb || 0) * 1024 * 1024 * 1024,
      retentionDays: data.retention_days || 7
    }
  } catch (error) {
    window.logService.error('Failed to load backup stats:', error)
  } finally {
    statsLoading.value = false
  }
}

const loadBackups = async () => {
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
    window.logService.info(`Deleted ${result.deleted_count || 0} old backup(s)`)
    await Promise.all([loadBackups(), loadStats()])
  } catch (error) {
    window.logService.error('Failed to cleanup old backups:', error)
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
