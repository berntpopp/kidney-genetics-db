<template>
  <v-container>
    <AdminHeader
      title="Cache Management"
      subtitle="Monitor and control cache performance"
      icon="mdi-memory"
      icon-color="purple"
      :breadcrumbs="ADMIN_BREADCRUMBS.cache"
    />

    <!-- Cache Stats Overview -->
    <v-row class="mb-6">
      <v-col cols="12" sm="6" md="3">
        <AdminStatsCard
          title="Hit Rate"
          :value="Math.round((cacheStats.hit_rate || 0) * 100)"
          format="percent"
          :loading="statsLoading"
          icon="mdi-target"
          color="success"
          :trend="hitRateTrend"
        />
      </v-col>
      <v-col cols="12" sm="6" md="3">
        <AdminStatsCard
          title="Total Entries"
          :value="cacheStats.total_entries || 0"
          :loading="statsLoading"
          icon="mdi-database"
          color="info"
        />
      </v-col>
      <v-col cols="12" sm="6" md="3">
        <AdminStatsCard
          title="Memory Usage"
          :value="cacheStats.total_size_bytes || 0"
          format="bytes"
          :loading="statsLoading"
          icon="mdi-memory"
          color="warning"
        />
      </v-col>
      <v-col cols="12" sm="6" md="3">
        <AdminStatsCard
          title="Namespaces"
          :value="namespaces.length"
          :loading="namespacesLoading"
          icon="mdi-folder-multiple"
          color="purple"
        />
      </v-col>
    </v-row>

    <!-- Actions Bar -->
    <v-card class="mb-4 pa-4">
      <div class="d-flex flex-wrap gap-2">
        <v-btn
          color="error"
          size="small"
          prepend-icon="mdi-delete-sweep"
          :loading="clearing"
          @click="confirmClearAll"
        >
          Clear All Cache
        </v-btn>
        <v-btn
          color="primary"
          size="small"
          prepend-icon="mdi-fire"
          :loading="warming"
          @click="warmCache"
        >
          Warm Cache
        </v-btn>
        <v-btn
          color="info"
          size="small"
          prepend-icon="mdi-refresh"
          :loading="statsLoading || namespacesLoading"
          @click="loadData"
        >
          Refresh Stats
        </v-btn>
        <v-btn
          color="success"
          size="small"
          prepend-icon="mdi-heart-pulse"
          :loading="checkingHealth"
          @click="checkHealth"
        >
          Health Check
        </v-btn>
      </div>
    </v-card>

    <!-- Cache Namespaces -->
    <v-card>
      <v-card-title>Cache Namespaces</v-card-title>
      <v-card-text class="pa-0">
        <v-data-table
          :headers="namespaceHeaders"
          :items="namespaces"
          :loading="namespacesLoading"
          density="compact"
          item-value="namespace"
          hover
        >
          <!-- Size column -->
          <template #item.size_mb="{ item }"> {{ item.size_mb.toFixed(2) }} MB </template>

          <!-- Entry count column -->
          <template #item.entry_count="{ item }">
            {{ item.entry_count.toLocaleString() }}
          </template>

          <!-- Age column -->
          <template #item.oldest_entry="{ item }">
            <span v-if="item.oldest_entry">
              {{ getAge(item.oldest_entry) }}
            </span>
            <span v-else class="text-medium-emphasis">Empty</span>
          </template>

          <!-- Actions column -->
          <template #item.actions="{ item }">
            <v-btn
              icon="mdi-information"
              size="x-small"
              variant="text"
              title="View details"
              @click="showNamespaceDetails(item)"
            />
            <v-btn
              icon="mdi-delete"
              size="x-small"
              variant="text"
              color="error"
              title="Clear namespace"
              @click="confirmClearNamespace(item)"
            />
          </template>
        </v-data-table>
      </v-card-text>
    </v-card>

    <!-- Health Status Card -->
    <v-card v-if="healthStatus" class="mt-4">
      <v-card-title>
        <component
          :is="healthStatus.healthy ? CircleCheck : CircleAlert"
          class="size-5 mr-2"
          :class="healthStatus.healthy ? 'text-green-600 dark:text-green-400' : 'text-destructive'"
        />
        Cache Health Status
      </v-card-title>
      <v-card-text>
        <v-row>
          <v-col cols="12" md="6">
            <div class="d-flex align-center mb-2">
              <component
                :is="healthStatus.memory_cache?.available ? Check : X"
                class="size-4 mr-2"
                :class="
                  healthStatus.memory_cache?.available
                    ? 'text-green-600 dark:text-green-400'
                    : 'text-destructive'
                "
              />
              <span
                >Memory Cache:
                {{ healthStatus.memory_cache?.available ? 'Available' : 'Unavailable' }}</span
              >
            </div>
            <div class="text-caption text-medium-emphasis ml-7">
              Entries: {{ healthStatus.memory_cache?.entry_count || 0 }}
            </div>
          </v-col>
          <v-col cols="12" md="6">
            <div class="d-flex align-center mb-2">
              <component
                :is="healthStatus.db_cache?.available ? Check : X"
                class="size-4 mr-2"
                :class="
                  healthStatus.db_cache?.available
                    ? 'text-green-600 dark:text-green-400'
                    : 'text-destructive'
                "
              />
              <span
                >Database Cache:
                {{ healthStatus.db_cache?.available ? 'Available' : 'Unavailable' }}</span
              >
            </div>
            <div class="text-caption text-medium-emphasis ml-7">
              Entries: {{ healthStatus.db_cache?.entry_count || 0 }}
            </div>
          </v-col>
        </v-row>
        <div class="text-caption text-medium-emphasis mt-2">
          Last checked: {{ formatDate(healthStatus.last_check) }}
        </div>
      </v-card-text>
    </v-card>

    <!-- Clear Confirmation Dialog -->
    <v-dialog v-model="showClearDialog" max-width="400">
      <v-card>
        <v-card-title>Confirm Clear Cache</v-card-title>
        <v-card-text>
          <p v-if="clearingNamespace">
            Are you sure you want to clear the "{{ clearingNamespace.namespace }}" namespace? This
            will remove {{ clearingNamespace.entry_count }} entries.
          </p>
          <p v-else>
            Are you sure you want to clear ALL cache entries? This will remove
            {{ cacheStats.total_entries }} entries across all namespaces.
          </p>
          <p class="text-error mt-2">This action cannot be undone.</p>
        </v-card-text>
        <v-card-actions>
          <v-spacer />
          <v-btn variant="text" @click="showClearDialog = false">Cancel</v-btn>
          <v-btn color="error" variant="flat" :loading="clearing" @click="executeClear">
            Clear Cache
          </v-btn>
        </v-card-actions>
      </v-card>
    </v-dialog>

    <!-- Namespace Details Dialog -->
    <v-dialog v-model="showDetailsDialog" max-width="600">
      <v-card v-if="selectedNamespace">
        <v-card-title> Namespace: {{ selectedNamespace.namespace }} </v-card-title>
        <v-card-text>
          <v-list density="compact">
            <v-list-item>
              <v-list-item-title>Total Entries</v-list-item-title>
              <v-list-item-subtitle>
                {{ selectedNamespace.entry_count.toLocaleString() }}
              </v-list-item-subtitle>
            </v-list-item>
            <v-list-item>
              <v-list-item-title>Size</v-list-item-title>
              <v-list-item-subtitle>
                {{ selectedNamespace.size_mb.toFixed(2) }} MB ({{
                  selectedNamespace.size_bytes.toLocaleString()
                }}
                bytes)
              </v-list-item-subtitle>
            </v-list-item>
            <v-list-item>
              <v-list-item-title>Oldest Entry</v-list-item-title>
              <v-list-item-subtitle>
                {{
                  selectedNamespace.oldest_entry
                    ? formatDate(selectedNamespace.oldest_entry)
                    : 'N/A'
                }}
              </v-list-item-subtitle>
            </v-list-item>
            <v-list-item>
              <v-list-item-title>Newest Entry</v-list-item-title>
              <v-list-item-subtitle>
                {{
                  selectedNamespace.newest_entry
                    ? formatDate(selectedNamespace.newest_entry)
                    : 'N/A'
                }}
              </v-list-item-subtitle>
            </v-list-item>
            <v-list-item v-if="selectedNamespace.ttl_seconds">
              <v-list-item-title>TTL</v-list-item-title>
              <v-list-item-subtitle>
                {{ selectedNamespace.ttl_seconds }} seconds
              </v-list-item-subtitle>
            </v-list-item>
          </v-list>
        </v-card-text>
        <v-card-actions>
          <v-spacer />
          <v-btn variant="text" @click="showDetailsDialog = false">Close</v-btn>
        </v-card-actions>
      </v-card>
    </v-dialog>
  </v-container>
</template>

<script setup>
/**
 * Cache Management View
 * Monitor and control cache performance
 */

import { ref, onMounted, onUnmounted } from 'vue'
// import { useAuthStore } from '@/stores/auth'
import AdminHeader from '@/components/admin/AdminHeader.vue'
import AdminStatsCard from '@/components/admin/AdminStatsCard.vue'
import * as cacheApi from '@/api/admin/cache'
import { ADMIN_BREADCRUMBS } from '@/utils/adminBreadcrumbs'
import { toast } from 'vue-sonner'
import { Check, CircleAlert, CircleCheck, X } from 'lucide-vue-next'

// const authStore = useAuthStore()

// State
const cacheStats = ref({})
const namespaces = ref([])
const healthStatus = ref(null)
const statsLoading = ref(false)
const namespacesLoading = ref(false)
const clearing = ref(false)
const warming = ref(false)
const checkingHealth = ref(false)
const showClearDialog = ref(false)
const showDetailsDialog = ref(false)
const clearingNamespace = ref(null)
const selectedNamespace = ref(null)
const hitRateTrend = ref(null)
const refreshInterval = ref(null)

// Table configuration
const namespaceHeaders = [
  { title: 'Namespace', key: 'namespace', align: 'start' },
  { title: 'Entries', key: 'entry_count' },
  { title: 'Size', key: 'size_mb' },
  { title: 'Age', key: 'oldest_entry' },
  { title: 'Actions', key: 'actions', sortable: false, align: 'center' }
]

// Methods
const loadStats = async () => {
  statsLoading.value = true
  try {
    const response = await cacheApi.getCacheStats()
    const data = response.data || response

    // Calculate trend if we have previous data
    if (cacheStats.value.hit_rate !== undefined) {
      const oldRate = cacheStats.value.hit_rate
      const newRate = data.hit_rate
      hitRateTrend.value = ((newRate - oldRate) / oldRate) * 100
    }

    cacheStats.value = data
  } catch (error) {
    window.logService.error('Failed to load cache stats:', error)
    toast.error('Failed to load cache statistics', { duration: Infinity })
  } finally {
    statsLoading.value = false
  }
}

const loadNamespaces = async () => {
  namespacesLoading.value = true
  try {
    const response = await cacheApi.getCacheNamespaces()
    namespaces.value = response.data || response || []
  } catch (error) {
    window.logService.error('Failed to load namespaces:', error)
    toast.error('Failed to load cache namespaces', { duration: Infinity })
    namespaces.value = [] // Ensure we have an array even on error
  } finally {
    namespacesLoading.value = false
  }
}

const loadData = async () => {
  await Promise.all([loadStats(), loadNamespaces()])
}

const checkHealth = async () => {
  checkingHealth.value = true
  try {
    const response = await cacheApi.getCacheHealth()
    const data = response.data || response

    // Map the API response to our expected format
    healthStatus.value = {
      healthy: data.status === 'healthy',
      memory_cache: {
        available: data.cache_enabled,
        entry_count: data.memory_cache_size || 0
      },
      db_cache: {
        available: data.database_connected,
        entry_count: cacheStats.value.db_entries || 0
      },
      last_check: new Date().toISOString()
    }
    toast.success('Health check completed', { duration: 5000 })
  } catch (error) {
    window.logService.error('Failed to check health:', error)
    toast.error('Failed to check cache health', { duration: Infinity })
  } finally {
    checkingHealth.value = false
  }
}

const warmCache = async () => {
  warming.value = true
  try {
    await cacheApi.warmCache()
    toast.success('Cache warming initiated', { duration: 5000 })
    // Reload stats after warming
    setTimeout(loadData, 2000)
  } catch (error) {
    window.logService.error('Failed to warm cache:', error)
    toast.error('Failed to warm cache', { duration: Infinity })
  } finally {
    warming.value = false
  }
}

const confirmClearAll = () => {
  clearingNamespace.value = null
  showClearDialog.value = true
}

const confirmClearNamespace = namespace => {
  clearingNamespace.value = namespace
  showClearDialog.value = true
}

const executeClear = async () => {
  clearing.value = true
  try {
    if (clearingNamespace.value) {
      await cacheApi.clearNamespace(clearingNamespace.value.namespace)
      toast.success(`Namespace "${clearingNamespace.value.namespace}" cleared`, { duration: 5000 })
    } else {
      await cacheApi.clearAllCache()
      toast.success('All cache cleared successfully', { duration: 5000 })
    }

    showClearDialog.value = false
    clearingNamespace.value = null

    // Reload data
    await loadData()
  } catch (error) {
    window.logService.error('Failed to clear cache:', error)
    toast.error('Failed to clear cache', { duration: Infinity })
  } finally {
    clearing.value = false
  }
}

const showNamespaceDetails = async namespace => {
  try {
    const response = await cacheApi.getNamespaceDetails(namespace.namespace)
    selectedNamespace.value = response.data || response
    showDetailsDialog.value = true
  } catch (error) {
    window.logService.error('Failed to load namespace details:', error)
    toast.error('Failed to load namespace details', { duration: Infinity })
  }
}

const formatDate = dateString => {
  if (!dateString) return 'N/A'
  const date = new Date(dateString)
  return date.toLocaleDateString() + ' ' + date.toLocaleTimeString()
}

const getAge = dateString => {
  if (!dateString) return 'N/A'

  const date = new Date(dateString)
  const now = new Date()
  const diff = now - date

  const hours = Math.floor(diff / (1000 * 60 * 60))
  if (hours < 1) {
    const minutes = Math.floor(diff / (1000 * 60))
    return `${minutes} min ago`
  } else if (hours < 24) {
    return `${hours} hours ago`
  } else {
    const days = Math.floor(hours / 24)
    return `${days} days ago`
  }
}

// Lifecycle
onMounted(() => {
  loadData()
  checkHealth()

  // Auto-refresh every 30 seconds
  refreshInterval.value = setInterval(loadData, 30000)
})

onUnmounted(() => {
  if (refreshInterval.value) {
    clearInterval(refreshInterval.value)
  }
})
</script>

<style scoped>
.gap-2 {
  gap: 0.5rem;
}
</style>
