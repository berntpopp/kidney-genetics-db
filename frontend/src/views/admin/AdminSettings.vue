<template>
  <div :class="PAGE_CONTAINER">
    <!-- Header -->
    <AdminHeader title="System Settings" subtitle="Manage application configuration" />

    <!-- Stats Overview -->
    <div class="mb-6 grid grid-cols-2 gap-3 md:grid-cols-3">
      <AdminStatsCard
        title="Total Settings"
        :value="stats.total"
        :loading="statsLoading"
        :icon="Settings"
      />
      <AdminStatsCard
        title="Requires Restart"
        :value="stats.requires_restart"
        :loading="statsLoading"
        :icon="RotateCw"
      />
      <AdminStatsCard
        title="Recent Changes"
        :value="stats.recent_changes_24h"
        :loading="statsLoading"
        :icon="HistoryIcon"
      />
    </div>

    <!-- Category Filter -->
    <Card class="mb-4">
      <CardContent class="pt-6">
        <div class="max-w-xs space-y-2">
          <Label for="category-filter">Filter by Category</Label>
          <Select v-model="selectedCategory" @update:model-value="loadSettings">
            <SelectTrigger id="category-filter">
              <SelectValue placeholder="All Categories" />
            </SelectTrigger>
            <SelectContent>
              <SelectItem
                v-for="option in categoryOptions"
                :key="option.value ?? 'all'"
                :value="option.value ?? 'all'"
              >
                {{ option.title }}
              </SelectItem>
            </SelectContent>
          </Select>
        </div>
      </CardContent>
    </Card>

    <!-- Settings by Category -->
    <DataState
      :loading="loading && !settings.length"
      :error="loadError"
      error-title="Could not load settings"
      :empty="!settings.length"
      empty-message="No settings in this category."
      @retry="loadSettings"
    >
      <template #loading>
        <div
          class="h-64 rounded-xl border bg-muted/50 motion-safe:animate-pulse"
          aria-hidden="true"
        />
      </template>
      <div v-for="(settingsGroup, category) in groupedSettings" :key="category" class="mb-6">
        <Card>
          <CardHeader>
            <CardTitle class="flex items-center gap-2 text-lg">
              <component
                :is="getCategoryIcon(category)"
                class="size-5 text-muted-foreground"
                aria-hidden="true"
              />
              {{ formatCategoryName(category) }}
            </CardTitle>
          </CardHeader>
          <CardContent class="p-0">
            <!-- Fixed columns so Value and Description line up across every category card -->
            <Table class="min-w-[720px] table-fixed">
              <colgroup>
                <col class="w-[30%]" />
                <col class="w-[22%]" />
                <col />
                <col class="w-[96px]" />
              </colgroup>
              <TableHeader>
                <TableRow>
                  <TableHead>Setting Key</TableHead>
                  <TableHead>Value</TableHead>
                  <TableHead>Description</TableHead>
                  <TableHead><span class="sr-only">Actions</span></TableHead>
                </TableRow>
              </TableHeader>
              <TableBody>
                <TableRow v-for="item in settingsGroup" :key="item.id">
                  <TableCell class="whitespace-normal">
                    <div class="flex flex-wrap items-center gap-2">
                      <span class="font-medium text-sm break-all">{{ item.key }}</span>
                      <StatusBadge
                        v-if="item.requires_restart"
                        status="warning"
                        label="Restart required"
                        tooltip="A change takes effect after the server restarts"
                      />
                    </div>
                  </TableCell>
                  <TableCell class="whitespace-normal">
                    <code v-if="item.is_sensitive" class="rounded bg-muted px-1.5 py-0.5 text-xs"
                      >***MASKED***</code
                    >
                    <code v-else class="rounded bg-muted px-1.5 py-0.5 text-xs break-all">{{
                      formatValue(item.value)
                    }}</code>
                  </TableCell>
                  <TableCell class="text-xs text-muted-foreground whitespace-normal">{{
                    item.description
                  }}</TableCell>
                  <TableCell>
                    <div class="flex justify-end gap-1">
                      <Tooltip>
                        <TooltipTrigger as-child>
                          <Button
                            :aria-label="`Edit ${item.key}`"
                            variant="ghost"
                            size="icon-sm"
                            :disabled="item.is_readonly"
                            @click="showEditDialog(item)"
                          >
                            <Pencil class="size-4" aria-hidden="true" />
                          </Button>
                        </TooltipTrigger>
                        <TooltipContent>{{
                          item.is_readonly ? 'Read-only setting' : 'Edit setting'
                        }}</TooltipContent>
                      </Tooltip>

                      <Tooltip>
                        <TooltipTrigger as-child>
                          <Button
                            :aria-label="`History of ${item.key}`"
                            variant="ghost"
                            size="icon-sm"
                            @click="showHistoryDialog(item)"
                          >
                            <HistoryIcon class="size-4" aria-hidden="true" />
                          </Button>
                        </TooltipTrigger>
                        <TooltipContent>Change history</TooltipContent>
                      </Tooltip>
                    </div>
                  </TableCell>
                </TableRow>
              </TableBody>
            </Table>
          </CardContent>
        </Card>
      </div>
    </DataState>

    <!-- Dialogs -->
    <SettingEditDialog
      v-model="dialogs.edit"
      :setting="selectedSetting"
      :loading="apiLoading"
      @save="handleSaveSetting"
    />

    <SettingHistoryDialog v-model="dialogs.history" :setting="selectedSetting" />
  </div>
</template>

<script setup>
import { ref, computed, onMounted } from 'vue'
import { History as HistoryIcon, Pencil, RotateCw } from 'lucide-vue-next'
import AdminHeader from '@/components/admin/AdminHeader.vue'
import { DataState, PAGE_CONTAINER, StatusBadge } from '@/components/shared'
import AdminStatsCard from '@/components/admin/AdminStatsCard.vue'
import SettingEditDialog from '@/components/admin/settings/SettingEditDialog.vue'
import SettingHistoryDialog from '@/components/admin/settings/SettingHistoryDialog.vue'
import { useSettingsApi } from '@/composables/useSettingsApi'
import {
  Cog,
  DatabaseBackup,
  FileText,
  RefreshCw,
  ScanSearch,
  Settings,
  ShieldAlert,
  Workflow
} from 'lucide-vue-next'

import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { Button } from '@/components/ui/button'
import { Label } from '@/components/ui/label'
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
  loadSettings: apiLoadSettings,
  loadStats: apiLoadStats,
  updateSetting: apiUpdateSetting
} = useSettingsApi()

// State
const stats = ref({
  total: 0,
  requires_restart: 0,
  recent_changes_24h: 0
})

const settings = ref([])
const selectedSetting = ref(null)
const selectedCategory = ref(null)
const statsLoading = ref(true)
const loading = ref(true)
const loadError = ref(null)

// Dialogs
const dialogs = ref({
  edit: false,
  history: false
})

// Category options
const categoryOptions = [
  { title: 'All Categories', value: null },
  { title: 'Cache', value: 'cache' },
  { title: 'Security', value: 'security' },
  { title: 'Pipeline', value: 'pipeline' },
  { title: 'Backup', value: 'backup' },
  { title: 'Features', value: 'features' },
  { title: 'Logging', value: 'logging' }
]

// Computed
const groupedSettings = computed(() => {
  if (!settings.value.length) return {}

  const grouped = {}
  for (const setting of settings.value) {
    if (!grouped[setting.category]) {
      grouped[setting.category] = []
    }
    grouped[setting.category].push(setting)
  }
  return grouped
})

// Methods
const loadStats = async () => {
  statsLoading.value = true
  try {
    const data = await apiLoadStats()
    stats.value = {
      total: data.total || 0,
      requires_restart: data.requires_restart || 0,
      recent_changes_24h: data.recent_changes_24h || 0
    }
  } catch (error) {
    window.logService.error('Failed to load settings stats:', error)
  } finally {
    statsLoading.value = false
  }
}

const loadSettings = async () => {
  loading.value = true
  loadError.value = null
  try {
    const category = selectedCategory.value === 'all' ? null : selectedCategory.value
    const data = await apiLoadSettings({
      category,
      limit: 500,
      offset: 0
    })

    settings.value = data.settings || []
  } catch (error) {
    window.logService.error('Failed to load settings:', error)
    loadError.value = error.message || 'Request failed'
  } finally {
    loading.value = false
  }
}

const showEditDialog = setting => {
  selectedSetting.value = setting
  dialogs.value.edit = true
}

const showHistoryDialog = setting => {
  selectedSetting.value = setting
  dialogs.value.history = true
}

const handleSaveSetting = async ({ value, reason }) => {
  try {
    const result = await apiUpdateSetting(selectedSetting.value.id, value, reason)

    window.logService.info('Setting updated successfully', result)

    if (result.setting.requires_restart) {
      window.logService.warn('Server restart required for this change to take effect')
    }

    dialogs.value.edit = false
    await Promise.all([loadSettings(), loadStats()])
  } catch (error) {
    window.logService.error('Failed to update setting:', error)
  }
}

const getCategoryIcon = category => {
  const icons = {
    cache: RefreshCw,
    security: ShieldAlert,
    pipeline: Workflow,
    backup: DatabaseBackup,
    features: ScanSearch,
    logging: FileText
  }
  return icons[category] || Cog
}

const formatCategoryName = category => {
  return category.charAt(0).toUpperCase() + category.slice(1)
}

const formatValue = value => {
  if (typeof value === 'object') {
    return JSON.stringify(value)
  }
  return String(value)
}

// Lifecycle
onMounted(() => {
  loadStats()
  loadSettings()
})
</script>
