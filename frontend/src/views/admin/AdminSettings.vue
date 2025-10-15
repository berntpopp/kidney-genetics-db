<template>
  <v-container>
    <!-- Header -->
    <AdminHeader
      title="System Settings"
      subtitle="Manage application configuration"
      icon="mdi-cog"
      icon-color="deep-purple"
      :breadcrumbs="ADMIN_BREADCRUMBS.settings"
    />

    <!-- Stats Overview -->
    <v-row class="mb-6">
      <v-col cols="12" sm="6" md="4">
        <AdminStatsCard
          title="Total Settings"
          :value="stats.total"
          :loading="statsLoading"
          icon="mdi-cog-outline"
          color="primary"
        />
      </v-col>
      <v-col cols="12" sm="6" md="4">
        <AdminStatsCard
          title="Requires Restart"
          :value="stats.requires_restart"
          :loading="statsLoading"
          icon="mdi-restart-alert"
          color="warning"
        />
      </v-col>
      <v-col cols="12" sm="6" md="4">
        <AdminStatsCard
          title="Recent Changes"
          :value="stats.recent_changes_24h"
          :loading="statsLoading"
          icon="mdi-history"
          color="info"
        />
      </v-col>
    </v-row>

    <!-- Category Filter -->
    <v-card rounded="lg" class="mb-4">
      <v-card-text>
        <v-row align="center">
          <v-col cols="12" md="4">
            <v-select
              v-model="selectedCategory"
              :items="categoryOptions"
              label="Filter by Category"
              clearable
              variant="outlined"
              density="compact"
              @update:model-value="loadSettings"
            />
          </v-col>
        </v-row>
      </v-card-text>
    </v-card>

    <!-- Settings by Category -->
    <div v-for="(settingsGroup, category) in groupedSettings" :key="category" class="mb-6">
      <v-card rounded="lg">
        <v-card-title class="text-h6 bg-surface-variant">
          <v-icon :icon="getCategoryIcon(category)" start />
          {{ formatCategoryName(category) }}
        </v-card-title>

        <v-data-table
          :headers="headers"
          :items="settingsGroup"
          :loading="loading"
          density="compact"
          hover
          items-per-page="-1"
          hide-default-footer
        >
          <template #item.key="{ item }">
            <span class="font-weight-medium">{{ item.key }}</span>
          </template>

          <template #item.value="{ item }">
            <code v-if="item.is_sensitive" class="text-caption">***MASKED***</code>
            <code v-else class="text-caption">{{ formatValue(item.value) }}</code>
          </template>

          <template #item.requires_restart="{ item }">
            <v-chip v-if="item.requires_restart" size="x-small" color="warning" variant="outlined">
              Restart Required
            </v-chip>
            <span v-else class="text-caption text-medium-emphasis">—</span>
          </template>

          <template #item.actions="{ item }">
            <div class="d-flex ga-1">
              <v-tooltip text="Edit Setting" location="top">
                <template #activator="{ props }">
                  <v-btn
                    v-bind="props"
                    icon="mdi-pencil"
                    size="x-small"
                    variant="text"
                    color="primary"
                    :disabled="item.is_readonly"
                    @click="showEditDialog(item)"
                  />
                </template>
              </v-tooltip>

              <v-tooltip text="View History" location="top">
                <template #activator="{ props }">
                  <v-btn
                    v-bind="props"
                    icon="mdi-history"
                    size="x-small"
                    variant="text"
                    color="info"
                    @click="showHistoryDialog(item)"
                  />
                </template>
              </v-tooltip>
            </div>
          </template>
        </v-data-table>
      </v-card>
    </div>

    <!-- Empty State -->
    <v-card v-if="!loading && Object.keys(groupedSettings).length === 0" rounded="lg">
      <v-card-text class="text-center py-8">
        <v-icon icon="mdi-cog-outline" size="64" color="grey-lighten-1" />
        <div class="text-h6 mt-4">No Settings Found</div>
        <div class="text-body-2 text-medium-emphasis">
          Select a different category or clear filters
        </div>
      </v-card-text>
    </v-card>

    <!-- Dialogs -->
    <SettingEditDialog
      v-model="dialogs.edit"
      :setting="selectedSetting"
      :loading="apiLoading"
      @save="handleSaveSetting"
    />

    <SettingHistoryDialog v-model="dialogs.history" :setting="selectedSetting" />
  </v-container>
</template>

<script setup>
import { ref, computed, onMounted } from 'vue'
import AdminHeader from '@/components/admin/AdminHeader.vue'
import AdminStatsCard from '@/components/admin/AdminStatsCard.vue'
import SettingEditDialog from '@/components/admin/settings/SettingEditDialog.vue'
import SettingHistoryDialog from '@/components/admin/settings/SettingHistoryDialog.vue'
import { useSettingsApi } from '@/composables/useSettingsApi'
import { ADMIN_BREADCRUMBS } from '@/utils/adminBreadcrumbs'

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

// Table headers
const headers = [
  { title: 'Setting Key', value: 'key', sortable: false },
  { title: 'Value', value: 'value', sortable: false },
  { title: 'Description', value: 'description', sortable: false },
  { title: 'Status', value: 'requires_restart', sortable: false, align: 'center' },
  { title: 'Actions', value: 'actions', sortable: false, align: 'center', width: 100 }
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
    const data = await apiLoadSettings({
      category: selectedCategory.value,
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
      window.logService.warn('⚠️ Server restart required for this change to take effect')
    }

    dialogs.value.edit = false
    await Promise.all([loadSettings(), loadStats()])
  } catch (error) {
    window.logService.error('Failed to update setting:', error)
  }
}

const getCategoryIcon = category => {
  const icons = {
    cache: 'mdi-database-refresh',
    security: 'mdi-shield-lock',
    pipeline: 'mdi-pipe',
    backup: 'mdi-database-export',
    features: 'mdi-feature-search'
  }
  return icons[category] || 'mdi-cog'
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

<style scoped>
code {
  background-color: rgba(var(--v-theme-on-surface), 0.05);
  padding: 2px 6px;
  border-radius: 4px;
}
</style>
