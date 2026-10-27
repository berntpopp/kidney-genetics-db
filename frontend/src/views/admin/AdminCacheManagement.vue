<script setup>
import { formatDateTime } from '@/utils/formatDate'
/**
 * Cache Management View
 * Monitor and control cache performance
 */

import { ref, h, onMounted, onUnmounted } from 'vue'
import { useTable } from '@tanstack/vue-table'
import AdminHeader from '@/components/admin/AdminHeader.vue'
import { DataState, PAGE_CONTAINER, StatusBadge } from '@/components/shared'
import AdminStatsCard from '@/components/admin/AdminStatsCard.vue'
import * as cacheApi from '@/api/admin/cache'
import { toast } from 'vue-sonner'
import {
  Check,
  Database,
  Flame,
  Folder,
  HeartPulse,
  Info,
  Loader2,
  MemoryStick,
  RefreshCw,
  Target,
  Trash2,
  X
} from 'lucide-vue-next'
import { DataTable, dataTableFeatures } from '@/components/ui/data-table'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { Button, buttonVariants } from '@/components/ui/button'
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle
} from '@/components/ui/dialog'
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
import { Tooltip, TooltipContent, TooltipTrigger } from '@/components/ui/tooltip'

// State
const cacheStats = ref({})
const namespaces = ref([])
const healthStatus = ref(null)
const statsLoading = ref(false)
const namespacesLoading = ref(false)
const namespacesError = ref(null)
const clearing = ref(false)
const warming = ref(false)
const checkingHealth = ref(false)
const showClearDialog = ref(false)
const showDetailsDialog = ref(false)
const clearingNamespace = ref(null)
const selectedNamespace = ref(null)
const hitRateTrend = ref(null)
const refreshInterval = ref(null)

// Column definitions for TanStack Table
const NUM = 'text-right tabular-nums'
const iconButton = (label, icon, onClick, danger = false) =>
  h(Tooltip, null, {
    default: () => [
      h(TooltipTrigger, { asChild: true }, () =>
        h(
          Button,
          {
            variant: 'ghost',
            size: 'icon-sm',
            'aria-label': label,
            class: danger ? 'text-danger hover:text-danger' : '',
            onClick
          },
          () => h(icon, { class: 'size-4', 'aria-hidden': 'true' })
        )
      ),
      h(TooltipContent, null, () => label)
    ]
  })
const namespaceColumns = [
  {
    accessorKey: 'namespace',
    header: 'Namespace',
    cell: ({ row }) => h('span', { class: 'font-medium' }, row.getValue('namespace'))
  },
  {
    accessorKey: 'entry_count',
    header: () => h('div', { class: 'text-right' }, 'Entries'),
    cell: ({ row }) => {
      const count = row.getValue('entry_count')
      return h('div', { class: NUM }, count != null ? count.toLocaleString() : '0')
    }
  },
  {
    accessorKey: 'size_mb',
    header: () => h('div', { class: 'text-right' }, 'Size'),
    cell: ({ row }) => {
      const size = row.getValue('size_mb')
      return h('div', { class: NUM }, size != null ? `${size.toFixed(2)} MB` : '0 MB')
    }
  },
  {
    accessorKey: 'oldest_entry',
    header: 'Age',
    cell: ({ row }) => {
      const val = row.getValue('oldest_entry')
      return h('span', { class: val ? '' : 'text-muted-foreground' }, val ? getAge(val) : 'Empty')
    }
  },
  {
    id: 'actions',
    header: () => h('span', { class: 'sr-only' }, 'Actions'),
    cell: ({ row }) => {
      const ns = row.original
      return h('div', { class: 'flex items-center justify-end gap-1' }, [
        iconButton(`Details for ${ns.namespace}`, Info, () => showNamespaceDetails(ns)),
        iconButton(`Clear ${ns.namespace}`, Trash2, () => confirmClearNamespace(ns), true)
      ])
    },
    enableSorting: false,
    size: 100
  }
]

// TanStack Table
const table = useTable({
  features: dataTableFeatures,
  manualPagination: true, // unpaged: render every row
  get data() {
    return namespaces.value
  },
  columns: namespaceColumns
})

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
  namespacesError.value = null
  try {
    const response = await cacheApi.getCacheNamespaces()
    namespaces.value = response.data || response || []
  } catch (error) {
    window.logService.error('Failed to load namespaces:', error)
    namespacesError.value = error.message || 'Request failed'
  } finally {
    namespacesLoading.value = false
  }
}

const loadData = async () => {
  await Promise.all([loadStats(), loadNamespaces()])
}

const checkHealth = async (notify = false) => {
  checkingHealth.value = true
  try {
    const response = await cacheApi.getCacheHealth()
    const data = response.data || response

    // Map the API response to our expected format
    healthStatus.value = {
      healthy: data.status === 'healthy',
      status: data.status,
      issues: data.issues || [],
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
    if (notify) toast.success('Health check completed', { duration: 5000 })
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

const formatDate = dateString => formatDateTime(dateString) || 'N/A'

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

<template>
  <div :class="PAGE_CONTAINER">
    <AdminHeader title="Cache Management" subtitle="Monitor and control cache performance" />

    <!-- Cache Stats Overview -->
    <div class="grid grid-cols-1 sm:grid-cols-2 md:grid-cols-4 gap-4 mb-6">
      <AdminStatsCard
        title="Hit Rate"
        :value="Math.round((cacheStats.hit_rate || 0) * 100)"
        format="percent"
        :loading="statsLoading"
        :icon="Target"
        :trend="hitRateTrend"
      />
      <AdminStatsCard
        title="Total Entries"
        :value="cacheStats.total_entries || 0"
        :loading="statsLoading"
        :icon="Database"
      />
      <AdminStatsCard
        v-if="statsLoading || cacheStats.total_size_bytes > 0"
        title="Memory Usage"
        :value="cacheStats.total_size_bytes || 0"
        format="bytes"
        :loading="statsLoading"
        :icon="MemoryStick"
      />
      <AdminStatsCard
        title="Namespaces"
        :value="namespaces.length"
        :loading="namespacesLoading"
        :icon="Folder"
      />
    </div>

    <!-- Actions Bar -->
    <Card class="mb-4">
      <CardContent class="p-4">
        <div class="flex flex-wrap gap-2">
          <Button size="sm" :disabled="warming" @click="warmCache">
            <Loader2 v-if="warming" class="size-4 mr-2 animate-spin" />
            <Flame v-else class="size-4 mr-2" />
            Warm Cache
          </Button>
          <Button
            variant="outline"
            size="sm"
            :disabled="statsLoading || namespacesLoading"
            @click="loadData"
          >
            <Loader2 v-if="statsLoading || namespacesLoading" class="size-4 mr-2 animate-spin" />
            <RefreshCw v-else class="size-4 mr-2" />
            Refresh Stats
          </Button>
          <Button variant="outline" size="sm" :disabled="checkingHealth" @click="checkHealth(true)">
            <Loader2 v-if="checkingHealth" class="size-4 mr-2 animate-spin" />
            <HeartPulse v-else class="size-4 mr-2" />
            Health Check
          </Button>
          <Button
            variant="outline"
            size="sm"
            class="text-danger hover:text-danger sm:ml-auto"
            :disabled="clearing"
            @click="confirmClearAll"
          >
            <Loader2 v-if="clearing" class="size-4 mr-2 animate-spin" />
            <Trash2 v-else class="size-4 mr-2" />
            Clear All Cache
          </Button>
        </div>
      </CardContent>
    </Card>

    <!-- Cache Namespaces -->
    <Card>
      <CardHeader>
        <CardTitle>Cache Namespaces</CardTitle>
      </CardHeader>
      <CardContent class="p-0">
        <DataState
          :loading="namespacesLoading && !namespaces.length"
          :error="namespacesError"
          error-title="Could not load cache namespaces"
          :empty="!namespaces.length"
          empty-message="The cache is empty."
          class="m-4"
          @retry="loadNamespaces"
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
          <DataTable :table="table" />
        </DataState>
      </CardContent>
    </Card>

    <!-- Health Status Card -->
    <Card v-if="healthStatus" class="mt-4">
      <CardHeader>
        <CardTitle class="flex items-center gap-2">
          Cache Health Status
          <StatusBadge :status="healthStatus.status" />
        </CardTitle>
      </CardHeader>
      <CardContent>
        <ul
          v-if="healthStatus.issues.length"
          class="mb-4 list-disc space-y-1 pl-5 text-sm text-foreground marker:text-warning"
          data-testid="health-issues"
        >
          <li v-for="issue in healthStatus.issues" :key="issue">{{ issue }}</li>
        </ul>
        <div class="grid grid-cols-1 md:grid-cols-2 gap-6">
          <div>
            <div class="flex items-center gap-2 mb-2">
              <component
                :is="healthStatus.memory_cache?.available ? Check : X"
                class="size-4"
                aria-hidden="true"
                :class="healthStatus.memory_cache?.available ? 'text-success' : 'text-danger'"
              />
              <span>
                Memory Cache:
                {{ healthStatus.memory_cache?.available ? 'Available' : 'Unavailable' }}
              </span>
            </div>
            <p class="text-sm text-muted-foreground ml-6">
              Entries: {{ healthStatus.memory_cache?.entry_count || 0 }}
            </p>
          </div>
          <div>
            <div class="flex items-center gap-2 mb-2">
              <component
                :is="healthStatus.db_cache?.available ? Check : X"
                class="size-4"
                aria-hidden="true"
                :class="healthStatus.db_cache?.available ? 'text-success' : 'text-danger'"
              />
              <span>
                Database Cache:
                {{ healthStatus.db_cache?.available ? 'Available' : 'Unavailable' }}
              </span>
            </div>
            <p class="text-sm text-muted-foreground ml-6">
              Entries: {{ healthStatus.db_cache?.entry_count || 0 }}
            </p>
          </div>
        </div>
        <p class="text-sm text-muted-foreground mt-4">
          Last checked: {{ formatDate(healthStatus.last_check) }}
        </p>
      </CardContent>
    </Card>

    <!-- Clear Confirmation Dialog -->
    <AlertDialog v-model:open="showClearDialog">
      <AlertDialogContent>
        <AlertDialogHeader>
          <AlertDialogTitle>Confirm Clear Cache</AlertDialogTitle>
          <AlertDialogDescription>
            <span v-if="clearingNamespace" class="block">
              Are you sure you want to clear the "{{ clearingNamespace.namespace }}" namespace? This
              will remove {{ clearingNamespace.entry_count }} entries.
            </span>
            <span v-else class="block">
              Are you sure you want to clear ALL cache entries? This will remove
              {{ cacheStats.total_entries }} entries across all namespaces.
            </span>
            <span class="mt-2 block font-medium text-foreground"
              >This action cannot be undone.</span
            >
          </AlertDialogDescription>
        </AlertDialogHeader>
        <AlertDialogFooter>
          <AlertDialogCancel @click="showClearDialog = false">Cancel</AlertDialogCancel>
          <AlertDialogAction
            :class="buttonVariants({ variant: 'destructive' })"
            :disabled="clearing"
            @click="executeClear"
          >
            <Loader2 v-if="clearing" class="size-4 mr-2 animate-spin" />
            Clear Cache
          </AlertDialogAction>
        </AlertDialogFooter>
      </AlertDialogContent>
    </AlertDialog>

    <!-- Namespace Details Dialog -->
    <Dialog v-model:open="showDetailsDialog">
      <DialogContent class="max-w-[500px]">
        <DialogHeader>
          <DialogTitle>Namespace: {{ selectedNamespace?.namespace }}</DialogTitle>
          <DialogDescription>Cache namespace details and statistics</DialogDescription>
        </DialogHeader>
        <div v-if="selectedNamespace" class="space-y-3">
          <div class="flex justify-between py-2 border-b">
            <span class="text-sm text-muted-foreground">Total Entries</span>
            <span class="text-sm font-medium">
              {{ selectedNamespace.entry_count.toLocaleString() }}
            </span>
          </div>
          <div class="flex justify-between py-2 border-b">
            <span class="text-sm text-muted-foreground">Size</span>
            <span class="text-sm font-medium">
              {{ selectedNamespace.size_mb.toFixed(2) }} MB ({{
                selectedNamespace.size_bytes.toLocaleString()
              }}
              bytes)
            </span>
          </div>
          <div class="flex justify-between py-2 border-b">
            <span class="text-sm text-muted-foreground">Oldest Entry</span>
            <span class="text-sm font-medium">
              {{
                selectedNamespace.oldest_entry ? formatDate(selectedNamespace.oldest_entry) : 'N/A'
              }}
            </span>
          </div>
          <div class="flex justify-between py-2 border-b">
            <span class="text-sm text-muted-foreground">Newest Entry</span>
            <span class="text-sm font-medium">
              {{
                selectedNamespace.newest_entry ? formatDate(selectedNamespace.newest_entry) : 'N/A'
              }}
            </span>
          </div>
          <div v-if="selectedNamespace.ttl_seconds" class="flex justify-between py-2 border-b">
            <span class="text-sm text-muted-foreground">TTL</span>
            <span class="text-sm font-medium"> {{ selectedNamespace.ttl_seconds }} seconds </span>
          </div>
        </div>
        <DialogFooter>
          <Button variant="outline" @click="showDetailsDialog = false">Close</Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  </div>
</template>
