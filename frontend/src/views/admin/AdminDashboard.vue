<template>
  <v-container fluid class="pa-4">
    <!-- Admin Header -->
    <AdminHeader title="Admin Dashboard" subtitle="System administration and management" />

    <!-- Stats Overview -->
    <v-row class="mb-6">
      <v-col cols="12" sm="6" md="3">
        <AdminStatsCard
          title="Active Users"
          :value="stats.activeUsers"
          :loading="statsLoading"
          icon="mdi-account-check"
          color="success"
        />
      </v-col>
      <v-col cols="12" sm="6" md="3">
        <AdminStatsCard
          title="Cache Hit Rate"
          :value="stats.cacheHitRate"
          :loading="statsLoading"
          format="percent"
          icon="mdi-speedometer"
          color="info"
        />
      </v-col>
      <v-col cols="12" sm="6" md="3">
        <AdminStatsCard
          title="Pipeline Jobs"
          :value="stats.pipelineJobs"
          :loading="statsLoading"
          icon="mdi-pipe"
          color="warning"
        />
      </v-col>
      <v-col cols="12" sm="6" md="3">
        <AdminStatsCard
          title="Pending Staging"
          :value="stats.pendingStaging"
          :loading="statsLoading"
          icon="mdi-clock-alert"
          color="error"
        />
      </v-col>
      <v-col cols="12" sm="6" md="3">
        <AdminStatsCard
          title="Data Releases"
          :value="stats.totalReleases"
          :loading="statsLoading"
          icon="mdi-package-variant"
          color="indigo"
        />
      </v-col>
    </v-row>

    <!-- Admin Function Cards -->
    <v-row>
      <v-col v-for="section in adminSections" :key="section.id" cols="12" lg="4" md="6">
        <v-card hover class="pa-4 h-100 d-flex flex-column" @click="navigateTo(section.route)">
          <div class="d-flex align-center mb-3">
            <v-icon :icon="section.icon" size="x-large" :color="section.color" />
            <div class="ml-4 flex-grow-1">
              <h3 class="text-h6 font-weight-medium">{{ section.title }}</h3>
              <p class="text-caption text-medium-emphasis mt-1">
                {{ section.description }}
              </p>
            </div>
          </div>

          <v-divider class="my-3" />

          <div class="text-body-2 flex-grow-1">
            <div
              v-for="feature in section.features"
              :key="feature"
              class="d-flex align-center mb-2"
            >
              <v-icon icon="mdi-check-circle" size="small" color="success" class="mr-2" />
              <span>{{ feature }}</span>
            </div>
          </div>

          <v-btn :color="section.color" variant="tonal" size="small" class="mt-3" block>
            Manage
            <v-icon icon="mdi-arrow-right" end />
          </v-btn>
        </v-card>
      </v-col>
    </v-row>

    <!-- Quick Actions -->
    <v-row class="mt-6">
      <v-col cols="12">
        <v-card class="pa-4">
          <h3 class="text-h6 mb-3">Quick Actions</h3>
          <div class="d-flex flex-wrap gap-2">
            <v-btn
              color="primary"
              size="small"
              prepend-icon="mdi-database-refresh"
              :loading="refreshingCache"
              @click="refreshCache"
            >
              Refresh Cache
            </v-btn>
            <v-btn
              color="success"
              size="small"
              prepend-icon="mdi-play"
              :loading="runningPipeline"
              @click="runPipeline"
            >
              Run All Pipelines
            </v-btn>
            <v-btn
              color="warning"
              size="small"
              prepend-icon="mdi-broom"
              :loading="cleaningLogs"
              @click="cleanupLogs"
            >
              Cleanup Old Logs
            </v-btn>
            <v-btn
              color="info"
              size="small"
              prepend-icon="mdi-chart-line"
              :loading="exportingStats"
              @click="exportStats"
            >
              Export Statistics
            </v-btn>
          </div>
        </v-card>
      </v-col>
    </v-row>
  </v-container>
</template>

<script setup>
/**
 * Admin Dashboard - Central hub for all admin functions
 * Following Material Design 3 principles with compact density
 */

import { ref, onMounted } from 'vue'
import { useRouter } from 'vue-router'
import { useAuthStore } from '@/stores/auth'
import AdminHeader from '@/components/admin/AdminHeader.vue'
import AdminStatsCard from '@/components/admin/AdminStatsCard.vue'

const router = useRouter()
const authStore = useAuthStore()

// State
const stats = ref({
  activeUsers: 0,
  cacheHitRate: 0,
  pipelineJobs: 0,
  pendingStaging: 0,
  totalReleases: 0
})

const statsLoading = ref(true)
const refreshingCache = ref(false)
const runningPipeline = ref(false)
const cleaningLogs = ref(false)
const exportingStats = ref(false)

// Admin sections configuration
const adminSections = [
  {
    id: 'users',
    title: 'User Management',
    description: 'Manage user accounts and permissions',
    icon: 'mdi-account-group',
    color: 'primary',
    route: '/admin/users',
    features: [
      'Create and manage users',
      'Assign roles and permissions',
      'View user activity',
      'Bulk operations'
    ]
  },
  {
    id: 'cache',
    title: 'Cache Management',
    description: 'Monitor and control cache performance',
    icon: 'mdi-memory',
    color: 'purple',
    route: '/admin/cache',
    features: [
      'View cache statistics',
      'Clear cache namespaces',
      'Monitor hit rates',
      'Warm cache preemptively'
    ]
  },
  {
    id: 'logs',
    title: 'System Logs',
    description: 'View and analyze system logs',
    icon: 'mdi-file-document-outline',
    color: 'orange',
    route: '/admin/logs',
    features: ['Filter by severity', 'Search log entries', 'Export log data', 'View error trends']
  },
  {
    id: 'pipeline',
    title: 'Data Pipeline',
    description: 'Control data ingestion pipelines',
    icon: 'mdi-pipe',
    color: 'green',
    route: '/admin/pipeline',
    features: [
      'Monitor pipeline status',
      'Trigger manual updates',
      'View progress in real-time',
      'Schedule automated runs'
    ]
  },
  {
    id: 'staging',
    title: 'Gene Staging',
    description: 'Review gene normalization attempts',
    icon: 'mdi-dna',
    color: 'red',
    route: '/admin/staging',
    features: [
      'Review pending genes',
      'Approve normalizations',
      'View statistics',
      'Bulk operations'
    ]
  },
  {
    id: 'annotations',
    title: 'Annotations',
    description: 'Manage gene annotation sources',
    icon: 'mdi-tag-multiple',
    color: 'teal',
    route: '/admin/annotations',
    features: ['Configure sources', 'Update annotations', 'View statistics', 'Schedule updates']
  },
  {
    id: 'releases',
    title: 'Data Releases',
    description: 'Create and manage CalVer data releases',
    icon: 'mdi-package-variant',
    color: 'indigo',
    route: '/admin/releases',
    features: [
      'Create versioned releases',
      'Publish snapshots',
      'Download exports',
      'Track release history'
    ]
  },
  {
    id: 'backups',
    title: 'Database Backups',
    description: 'Create and manage database backups',
    icon: 'mdi-database-export',
    color: 'blue-grey',
    route: '/admin/backups',
    features: [
      'Create on-demand backups',
      'Restore from backup',
      'Download backup files',
      'Automatic retention policy'
    ]
  },
  {
    id: 'settings',
    title: 'System Settings',
    description: 'Manage application configuration',
    icon: 'mdi-cog',
    color: 'deep-purple',
    route: '/admin/settings',
    features: [
      'Configure cache settings',
      'Manage security options',
      'Update pipeline parameters',
      'View change history'
    ]
  },
  {
    id: 'hybrid-sources',
    title: 'Hybrid Sources',
    description: 'Upload DiagnosticPanels and Literature data',
    icon: 'mdi-database-import',
    color: 'cyan',
    route: '/admin/hybrid-sources',
    features: [
      'Upload diagnostic panel files',
      'Upload literature evidence',
      'View upload statistics',
      'Manage provider data'
    ]
  }
]

// Methods
const navigateTo = route => {
  router.push(route)
}

const loadStats = async () => {
  statsLoading.value = true
  try {
    // Load statistics from various endpoints
    const [users, cache, pipeline, staging, releases] = await Promise.all([
      fetchUserStats(),
      fetchCacheStats(),
      fetchPipelineStats(),
      fetchStagingStats(),
      fetchReleasesStats()
    ])

    stats.value = {
      activeUsers: users?.activeCount || 0,
      cacheHitRate: Math.round((cache?.hit_rate || 0) * 100),
      pipelineJobs: pipeline?.running || 0,
      pendingStaging: staging?.total_pending || 0,
      totalReleases: releases?.total || 0
    }
  } catch (error) {
    window.logService.error('Failed to load dashboard stats:', error)
  } finally {
    statsLoading.value = false
  }
}

const fetchUserStats = async () => {
  try {
    const users = await authStore.getAllUsers()
    return {
      total: users.length,
      activeCount: users.filter(u => u.is_active).length
    }
  } catch (error) {
    window.logService.error('Failed to fetch user stats:', error)
    return null
  }
}

const fetchCacheStats = async () => {
  try {
    const response = await fetch('/api/admin/cache/stats', {
      headers: {
        Authorization: `Bearer ${authStore.accessToken}`
      }
    })
    if (!response.ok) throw new Error('Failed to fetch cache stats')
    const data = await response.json()
    return data.data || data
  } catch (error) {
    window.logService.error('Failed to fetch cache stats:', error)
    return null
  }
}

const fetchPipelineStats = async () => {
  try {
    const response = await fetch('/api/progress/dashboard', {
      headers: {
        Authorization: `Bearer ${authStore.accessToken}`
      }
    })
    if (!response.ok) throw new Error('Failed to fetch pipeline stats')
    const data = await response.json()
    return data.data?.summary || null
  } catch (error) {
    window.logService.error('Failed to fetch pipeline stats:', error)
    return null
  }
}

const fetchStagingStats = async () => {
  try {
    const response = await fetch('/api/staging/staging/stats', {
      headers: {
        Authorization: `Bearer ${authStore.accessToken}`
      }
    })
    if (!response.ok) throw new Error('Failed to fetch staging stats')
    const data = await response.json()
    return data.data || data
  } catch (error) {
    window.logService.error('Failed to fetch staging stats:', error)
    return null
  }
}

const fetchReleasesStats = async () => {
  try {
    const response = await fetch('/api/releases/', {
      headers: {
        Authorization: `Bearer ${authStore.accessToken}`
      }
    })
    if (!response.ok) throw new Error('Failed to fetch releases stats')
    const data = await response.json()
    return {
      total: data.meta?.total || 0,
      published: data.data?.filter(r => r.status === 'published').length || 0
    }
  } catch (error) {
    window.logService.error('Failed to fetch releases stats:', error)
    return null
  }
}

const refreshCache = async () => {
  refreshingCache.value = true
  try {
    const response = await fetch('/api/admin/cache', {
      method: 'DELETE',
      headers: {
        Authorization: `Bearer ${authStore.accessToken}`
      }
    })
    if (!response.ok) throw new Error('Failed to clear cache')
    // Show success message
    window.logService.info('Cache cleared successfully')
  } catch (error) {
    window.logService.error('Failed to refresh cache:', error)
  } finally {
    refreshingCache.value = false
  }
}

const runPipeline = async () => {
  runningPipeline.value = true
  try {
    // Get all sources and trigger them
    const response = await fetch('/api/progress/status', {
      headers: {
        Authorization: `Bearer ${authStore.accessToken}`
      }
    })
    if (!response.ok) throw new Error('Failed to fetch sources')
    const sources = await response.json()

    // Trigger each data source
    const triggers = sources.data
      .filter(s => s.category === 'data_source')
      .map(s =>
        fetch(`/api/progress/trigger/${s.source_name}`, {
          method: 'POST',
          headers: {
            Authorization: `Bearer ${authStore.accessToken}`
          }
        })
      )

    await Promise.all(triggers)
    window.logService.info('All pipelines triggered successfully')
  } catch (error) {
    window.logService.error('Failed to run pipelines:', error)
  } finally {
    runningPipeline.value = false
  }
}

const cleanupLogs = async () => {
  cleaningLogs.value = true
  try {
    const response = await fetch('/api/admin/logs/cleanup?days=30', {
      method: 'DELETE',
      headers: {
        Authorization: `Bearer ${authStore.accessToken}`
      }
    })
    if (!response.ok) throw new Error('Failed to cleanup logs')
    const result = await response.json()
    window.logService.info(`Deleted ${result.logs_deleted} old log entries`)
  } catch (error) {
    window.logService.error('Failed to cleanup logs:', error)
  } finally {
    cleaningLogs.value = false
  }
}

const exportStats = async () => {
  exportingStats.value = true
  try {
    // Collect all statistics
    const [users, cache, pipeline, staging, logs] = await Promise.all([
      fetchUserStats(),
      fetchCacheStats(),
      fetchPipelineStats(),
      fetchStagingStats(),
      fetch('/api/admin/logs/statistics?hours=24', {
        headers: { Authorization: `Bearer ${authStore.accessToken}` }
      }).then(r => r.json())
    ])

    const exportData = {
      timestamp: new Date().toISOString(),
      users,
      cache,
      pipeline,
      staging,
      logs: logs.data || logs
    }

    // Create and download JSON file
    const blob = new Blob([JSON.stringify(exportData, null, 2)], {
      type: 'application/json'
    })
    const url = URL.createObjectURL(blob)
    const a = document.createElement('a')
    a.href = url
    a.download = `admin-stats-${new Date().toISOString().split('T')[0]}.json`
    a.click()
    URL.revokeObjectURL(url)

    window.logService.info('Statistics exported successfully')
  } catch (error) {
    window.logService.error('Failed to export statistics:', error)
  } finally {
    exportingStats.value = false
  }
}

// Lifecycle
onMounted(() => {
  loadStats()
  // Refresh stats every 30 seconds
  setInterval(loadStats, 30000)
})
</script>

<style scoped>
.gap-2 {
  gap: 0.5rem;
}
</style>
