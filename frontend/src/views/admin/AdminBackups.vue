<template>
  <v-container>
    <!-- Header -->
    <AdminHeader
      title="Database Backups"
      subtitle="Create, manage, and restore database backups"
      icon="mdi-database-export"
      icon-color="blue-grey"
      :breadcrumbs="ADMIN_BREADCRUMBS.backups"
    >
      <template #actions>
        <v-btn
          color="primary"
          variant="elevated"
          prepend-icon="mdi-database-plus"
          :loading="apiLoading"
          @click="dialogs.create = true"
        >
          Create Backup
        </v-btn>
      </template>
    </AdminHeader>

    <!-- Stats Overview -->
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
        :loading="apiLoading"
        density="compact"
        hover
        :items-per-page="-1"
        hide-default-footer
      >
        <template #item.status="{ item }">
          <v-chip :color="getStatusColor(item.status)" size="small" label>
            <v-icon :icon="getStatusIcon(item.status)" start size="x-small" />
            {{ item.status }}
          </v-chip>
        </template>

        <template #item.trigger_source="{ item }">
          <v-chip size="x-small" variant="outlined">
            {{ item.trigger_source }}
          </v-chip>
        </template>

        <template #item.file_size_mb="{ item }">
          <span class="text-caption">{{ formatSize(item.file_size_mb) }}</span>
        </template>

        <template #item.duration_seconds="{ item }">
          <span class="text-caption">{{ formatDuration(item.duration_seconds) }}</span>
        </template>

        <template #item.created_at="{ item }">
          <span class="text-caption">{{ formatDate(item.created_at) }}</span>
        </template>

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
                  @click="handleDownloadBackup(item)"
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
  </v-container>
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

const {
  getStatusColor,
  getStatusIcon,
  formatSize,
  formatDuration,
  formatDate,
  formatRelativeTime
} = useBackupFormatters()

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

// Table configuration
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

<style scoped>
.border-b {
  border-bottom: thin solid rgba(var(--v-border-color), var(--v-border-opacity));
}
</style>
