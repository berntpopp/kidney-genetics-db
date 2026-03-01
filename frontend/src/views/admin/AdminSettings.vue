<template>
  <div class="container mx-auto px-4 py-6">
    <!-- Header -->
    <AdminHeader
      title="System Settings"
      subtitle="Manage application configuration"
      icon="mdi-cog"
      icon-color="deep-purple"
      :breadcrumbs="ADMIN_BREADCRUMBS.settings"
    />

    <!-- Stats Overview -->
    <div class="mb-6 grid grid-cols-1 gap-4 sm:grid-cols-2 md:grid-cols-3">
      <AdminStatsCard
        title="Total Settings"
        :value="stats.total"
        :loading="statsLoading"
        icon="mdi-cog-outline"
        color="primary"
      />
      <AdminStatsCard
        title="Requires Restart"
        :value="stats.requires_restart"
        :loading="statsLoading"
        icon="mdi-restart-alert"
        color="warning"
      />
      <AdminStatsCard
        title="Recent Changes"
        :value="stats.recent_changes_24h"
        :loading="statsLoading"
        icon="mdi-history"
        color="info"
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
    <div v-for="(settingsGroup, category) in groupedSettings" :key="category" class="mb-6">
      <Card>
        <CardHeader>
          <CardTitle class="flex items-center gap-2 text-lg">
            <component :is="getCategoryIcon(category)" class="size-5" />
            {{ formatCategoryName(category) }}
          </CardTitle>
        </CardHeader>
        <CardContent class="p-0">
          <Table>
            <TableHeader>
              <TableRow>
                <TableHead>Setting Key</TableHead>
                <TableHead>Value</TableHead>
                <TableHead>Description</TableHead>
                <TableHead class="text-center">Status</TableHead>
                <TableHead class="text-center w-[100px]">Actions</TableHead>
              </TableRow>
            </TableHeader>
            <TableBody>
              <TableRow v-for="item in settingsGroup" :key="item.id" class="hover:bg-muted/50">
                <TableCell class="font-medium text-sm">{{ item.key }}</TableCell>
                <TableCell>
                  <code v-if="item.is_sensitive" class="rounded bg-muted px-1.5 py-0.5 text-xs"
                    >***MASKED***</code
                  >
                  <code v-else class="rounded bg-muted px-1.5 py-0.5 text-xs">{{
                    formatValue(item.value)
                  }}</code>
                </TableCell>
                <TableCell class="text-xs text-muted-foreground">{{ item.description }}</TableCell>
                <TableCell class="text-center">
                  <Badge
                    v-if="item.requires_restart"
                    variant="outline"
                    class="text-yellow-600 border-yellow-600"
                  >
                    Restart Required
                  </Badge>
                  <span v-else class="text-xs text-muted-foreground">--</span>
                </TableCell>
                <TableCell>
                  <div class="flex justify-center gap-1">
                    <Tooltip>
                      <TooltipTrigger as-child>
                        <Button
                          variant="ghost"
                          size="icon"
                          class="h-8 w-8"
                          :disabled="item.is_readonly"
                          @click="showEditDialog(item)"
                        >
                          <Pencil class="size-4 text-primary" />
                        </Button>
                      </TooltipTrigger>
                      <TooltipContent>Edit Setting</TooltipContent>
                    </Tooltip>

                    <Tooltip>
                      <TooltipTrigger as-child>
                        <Button
                          variant="ghost"
                          size="icon"
                          class="h-8 w-8"
                          @click="showHistoryDialog(item)"
                        >
                          <HistoryIcon class="size-4 text-blue-500" />
                        </Button>
                      </TooltipTrigger>
                      <TooltipContent>View History</TooltipContent>
                    </Tooltip>
                  </div>
                </TableCell>
              </TableRow>
            </TableBody>
          </Table>
        </CardContent>
      </Card>
    </div>

    <!-- Empty State -->
    <Card v-if="!loading && Object.keys(groupedSettings).length === 0">
      <CardContent class="py-8 text-center">
        <Settings class="mx-auto size-16 text-muted-foreground" />
        <div class="mt-4 text-lg font-semibold">No Settings Found</div>
        <div class="text-sm text-muted-foreground">
          Select a different category or clear filters
        </div>
      </CardContent>
    </Card>

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
import { Pencil, History as HistoryIcon } from 'lucide-vue-next'
import AdminHeader from '@/components/admin/AdminHeader.vue'
import AdminStatsCard from '@/components/admin/AdminStatsCard.vue'
import SettingEditDialog from '@/components/admin/settings/SettingEditDialog.vue'
import SettingHistoryDialog from '@/components/admin/settings/SettingHistoryDialog.vue'
import { useSettingsApi } from '@/composables/useSettingsApi'
import { ADMIN_BREADCRUMBS } from '@/utils/adminBreadcrumbs'
import {
  Cog,
  DatabaseBackup,
  RefreshCw,
  ScanSearch,
  Settings,
  ShieldAlert,
  Workflow
} from 'lucide-vue-next'

import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { Button } from '@/components/ui/button'
import { Badge } from '@/components/ui/badge'
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
  { title: 'Features', value: 'features' }
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
    features: ScanSearch
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
