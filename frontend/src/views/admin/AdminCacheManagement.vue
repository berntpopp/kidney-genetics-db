<script setup>
/**
 * Cache Management View
 * Monitor and control cache performance
 */

import { ref, h, onMounted, onUnmounted } from 'vue'
import { useVueTable, getCoreRowModel, getSortedRowModel } from '@tanstack/vue-table'
import AdminHeader from '@/components/admin/AdminHeader.vue'
import AdminStatsCard from '@/components/admin/AdminStatsCard.vue'
import * as cacheApi from '@/api/admin/cache'
import { ADMIN_BREADCRUMBS } from '@/utils/adminBreadcrumbs'
import { toast } from 'vue-sonner'
import {
  Check,
  CircleAlert,
  CircleCheck,
  Flame,
  Info,
  Loader2,
  RefreshCw,
  HeartPulse,
  Trash2,
  X
} from 'lucide-vue-next'
import { DataTable } from '@/components/ui/data-table'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { Button } from '@/components/ui/button'
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
const namespaceColumns = [
  {
    accessorKey: 'namespace',
    header: 'Namespace',
    cell: ({ row }) => h('span', { class: 'font-medium' }, row.getValue('namespace'))
  },
  {
    accessorKey: 'entry_count',
    header: 'Entries',
    cell: ({ row }) => {
      const count = row.getValue('entry_count')
      return h('span', null, count != null ? count.toLocaleString() : '0')
    }
  },
  {
    accessorKey: 'size_mb',
    header: 'Size',
    cell: ({ row }) => {
      const size = row.getValue('size_mb')
      return h('span', null, size != null ? `${size.toFixed(2)} MB` : '0 MB')
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
    header: '',
    cell: ({ row }) => {
      const ns = row.original
      return h('div', { class: 'flex items-center gap-1' }, [
        h(Tooltip, null, {
          default: () => [
            h(TooltipTrigger, { asChild: true }, () =>
              h(
                Button,
                {
                  variant: 'ghost',
                  size: 'icon',
                  class: 'h-8 w-8',
                  onClick: () => showNamespaceDetails(ns)
                },
                () => h(Info, { class: 'size-4' })
              )
            ),
            h(TooltipContent, null, () => 'View details')
          ]
        }),
        h(Tooltip, null, {
          default: () => [
            h(TooltipTrigger, { asChild: true }, () =>
              h(
                Button,
                {
                  variant: 'ghost',
                  size: 'icon',
                  class: 'h-8 w-8 text-destructive',
                  onClick: () => confirmClearNamespace(ns)
                },
                () => h(Trash2, { class: 'size-4' })
              )
            ),
            h(TooltipContent, null, () => 'Clear namespace')
          ]
        })
      ])
    },
    enableSorting: false,
    size: 100
  }
]

// TanStack Table
const table = useVueTable({
  get data() {
    return namespaces.value
  },
  columns: namespaceColumns,
  getCoreRowModel: getCoreRowModel(),
  getSortedRowModel: getSortedRowModel()
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

<template>
  <div class="container mx-auto px-4 py-6">
    <AdminHeader
      title="Cache Management"
      subtitle="Monitor and control cache performance"
      icon="mdi-memory"
      icon-color="purple"
      :breadcrumbs="ADMIN_BREADCRUMBS.cache"
    />

    <!-- Cache Stats Overview -->
    <div class="grid grid-cols-1 sm:grid-cols-2 md:grid-cols-4 gap-4 mb-6">
      <AdminStatsCard
        title="Hit Rate"
        :value="Math.round((cacheStats.hit_rate || 0) * 100)"
        format="percent"
        :loading="statsLoading"
        icon="mdi-target"
        color="success"
        :trend="hitRateTrend"
      />
      <AdminStatsCard
        title="Total Entries"
        :value="cacheStats.total_entries || 0"
        :loading="statsLoading"
        icon="mdi-database"
        color="info"
      />
      <AdminStatsCard
        title="Memory Usage"
        :value="cacheStats.total_size_bytes || 0"
        format="bytes"
        :loading="statsLoading"
        icon="mdi-memory"
        color="warning"
      />
      <AdminStatsCard
        title="Namespaces"
        :value="namespaces.length"
        :loading="namespacesLoading"
        icon="mdi-folder-multiple"
        color="purple"
      />
    </div>

    <!-- Actions Bar -->
    <Card class="mb-4">
      <CardContent class="p-4">
        <div class="flex flex-wrap gap-2">
          <Button variant="destructive" size="sm" :disabled="clearing" @click="confirmClearAll">
            <Loader2 v-if="clearing" class="size-4 mr-2 animate-spin" />
            <Trash2 v-else class="size-4 mr-2" />
            Clear All Cache
          </Button>
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
          <Button variant="outline" size="sm" :disabled="checkingHealth" @click="checkHealth">
            <Loader2 v-if="checkingHealth" class="size-4 mr-2 animate-spin" />
            <HeartPulse v-else class="size-4 mr-2" />
            Health Check
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
        <div v-if="namespacesLoading" class="flex items-center justify-center py-12">
          <Loader2 class="size-6 animate-spin text-muted-foreground" />
          <span class="ml-2 text-sm text-muted-foreground">Loading namespaces...</span>
        </div>
        <DataTable v-else :table="table" />
      </CardContent>
    </Card>

    <!-- Health Status Card -->
    <Card v-if="healthStatus" class="mt-4">
      <CardHeader>
        <CardTitle class="flex items-center gap-2">
          <component
            :is="healthStatus.healthy ? CircleCheck : CircleAlert"
            class="size-5"
            :class="
              healthStatus.healthy ? 'text-green-600 dark:text-green-400' : 'text-destructive'
            "
          />
          Cache Health Status
        </CardTitle>
      </CardHeader>
      <CardContent>
        <div class="grid grid-cols-1 md:grid-cols-2 gap-6">
          <div>
            <div class="flex items-center gap-2 mb-2">
              <component
                :is="healthStatus.memory_cache?.available ? Check : X"
                class="size-4"
                :class="
                  healthStatus.memory_cache?.available
                    ? 'text-green-600 dark:text-green-400'
                    : 'text-destructive'
                "
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
                :class="
                  healthStatus.db_cache?.available
                    ? 'text-green-600 dark:text-green-400'
                    : 'text-destructive'
                "
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
            <span v-if="clearingNamespace">
              Are you sure you want to clear the "{{ clearingNamespace.namespace }}" namespace? This
              will remove {{ clearingNamespace.entry_count }} entries.
            </span>
            <span v-else>
              Are you sure you want to clear ALL cache entries? This will remove
              {{ cacheStats.total_entries }} entries across all namespaces.
            </span>
            <br />
            <span class="text-destructive font-medium">This action cannot be undone.</span>
          </AlertDialogDescription>
        </AlertDialogHeader>
        <AlertDialogFooter>
          <AlertDialogCancel @click="showClearDialog = false">Cancel</AlertDialogCancel>
          <AlertDialogAction
            class="bg-destructive text-destructive-foreground hover:bg-destructive/90"
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
