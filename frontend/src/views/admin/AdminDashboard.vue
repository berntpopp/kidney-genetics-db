<template>
  <div class="container mx-auto px-4 py-6">
    <!-- Admin Header -->
    <AdminHeader
      title="Admin Dashboard"
      subtitle="System administration and management"
      :icon="LayoutDashboard"
      icon-color="primary"
      :breadcrumbs="ADMIN_BREADCRUMBS.dashboard"
    />

    <!-- Stats Overview -->
    <div class="mb-6 grid grid-cols-1 gap-4 sm:grid-cols-2 md:grid-cols-3 lg:grid-cols-5">
      <AdminStatsCard
        title="Active Users"
        :value="stats.activeUsers"
        :loading="statsLoading"
        :icon="UserCheck"
        color="success"
      />
      <AdminStatsCard
        title="Cache Hit Rate"
        :value="stats.cacheHitRate"
        :loading="statsLoading"
        format="percent"
        :icon="Gauge"
        color="info"
      />
      <AdminStatsCard
        title="Pipeline Jobs"
        :value="stats.pipelineJobs"
        :loading="statsLoading"
        :icon="Minus"
        color="warning"
      />
      <AdminStatsCard
        title="Pending Staging"
        :value="stats.pendingStaging"
        :loading="statsLoading"
        :icon="ClockAlert"
        color="error"
      />
      <AdminStatsCard
        title="Data Releases"
        :value="stats.totalReleases"
        :loading="statsLoading"
        :icon="Package"
        color="indigo"
      />
    </div>

    <!-- Admin Function Cards -->
    <div class="grid grid-cols-1 gap-4 md:grid-cols-2 lg:grid-cols-3">
      <Card
        v-for="section in adminSections"
        :key="section.id"
        class="cursor-pointer transition-shadow hover:shadow-md"
        @click="navigateTo(section.route)"
      >
        <CardHeader class="flex flex-row items-center gap-3 pb-2">
          <div class="flex h-10 w-10 items-center justify-center rounded-lg bg-primary/10">
            <component :is="section.icon" :size="20" class="text-primary" />
          </div>
          <div>
            <CardTitle class="text-base">{{ section.title }}</CardTitle>
            <CardDescription class="text-xs">{{ section.description }}</CardDescription>
          </div>
        </CardHeader>
        <CardContent>
          <ul class="space-y-1 text-xs text-muted-foreground">
            <li v-for="feature in section.features" :key="feature" class="flex items-center gap-2">
              <CircleCheck :size="14" class="text-green-600 dark:text-green-400" />
              <span>{{ feature }}</span>
            </li>
          </ul>
        </CardContent>
      </Card>
    </div>
  </div>
</template>

<script setup>
import { ref, onMounted } from 'vue'
import { useRouter } from 'vue-router'
import { useAuthStore } from '@/stores/auth'
import { getCacheStats } from '@/api/admin/cache'
import { getDashboardData } from '@/api/admin/pipeline'
import { getStagingStats } from '@/api/admin/staging'
import { listReleases } from '@/api/admin/releases'
import AdminHeader from '@/components/admin/AdminHeader.vue'
import AdminStatsCard from '@/components/admin/AdminStatsCard.vue'
import { ADMIN_BREADCRUMBS } from '@/utils/adminBreadcrumbs'
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card'
import {
  CircleCheck,
  ClockAlert,
  Cog,
  DatabaseBackup,
  DatabaseZap,
  Dna,
  FileText,
  Gauge,
  LayoutDashboard,
  MemoryStick,
  Minus,
  Package,
  Tags,
  UserCheck,
  Users
} from 'lucide-vue-next'

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

// Admin sections configuration
const adminSections = [
  {
    id: 'users',
    title: 'User Management',
    description: 'Manage user accounts and permissions',
    icon: Users,
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
    icon: MemoryStick,
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
    icon: FileText,
    route: '/admin/logs',
    features: ['Filter by severity', 'Search log entries', 'Export log data', 'View error trends']
  },
  {
    id: 'pipeline',
    title: 'Data Pipeline',
    description: 'Control data ingestion pipelines',
    icon: Minus,
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
    icon: Dna,
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
    icon: Tags,
    route: '/admin/annotations',
    features: ['Configure sources', 'Update annotations', 'View statistics', 'Schedule updates']
  },
  {
    id: 'releases',
    title: 'Data Releases',
    description: 'Create and manage CalVer data releases',
    icon: Package,
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
    icon: DatabaseBackup,
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
    icon: Cog,
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
    icon: DatabaseZap,
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
    const data = (await getCacheStats()).data
    return data.data || data
  } catch (error) {
    window.logService.error('Failed to fetch cache stats:', error)
    return null
  }
}

const fetchPipelineStats = async () => {
  try {
    const data = (await getDashboardData()).data
    return data.data?.summary || null
  } catch (error) {
    window.logService.error('Failed to fetch pipeline stats:', error)
    return null
  }
}

const fetchStagingStats = async () => {
  try {
    const data = (await getStagingStats()).data
    return data.data || data
  } catch (error) {
    window.logService.error('Failed to fetch staging stats:', error)
    return null
  }
}

const fetchReleasesStats = async () => {
  try {
    const data = (await listReleases()).data
    return {
      total: data.meta?.total || 0,
      published: data.data?.filter(r => r.status === 'published').length || 0
    }
  } catch (error) {
    window.logService.error('Failed to fetch releases stats:', error)
    return null
  }
}

// Lifecycle
onMounted(() => {
  loadStats()
  setInterval(loadStats, 30000)
})
</script>
