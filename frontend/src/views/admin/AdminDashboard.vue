<template>
  <div :class="PAGE_CONTAINER">
    <AdminHeader title="Admin" subtitle="Live system status and entry points to each area" root />

    <!-- Sections: real links, each with its live status where one exists -->
    <nav aria-label="Admin sections">
      <ul class="grid grid-cols-1 gap-3 md:grid-cols-2 lg:grid-cols-3">
        <li v-for="section in sections" :key="section.id">
          <RouterLink
            :to="section.route"
            data-testid="admin-section"
            class="group flex h-full items-start gap-3 rounded-xl border bg-card p-4 transition-colors hover:border-primary/40 hover:bg-muted/50 focus-visible:ring-2 focus-visible:ring-ring focus-visible:outline-none"
          >
            <component
              :is="section.icon"
              class="mt-0.5 size-5 shrink-0 text-muted-foreground group-hover:text-primary"
              aria-hidden="true"
            />
            <div class="min-w-0 flex-1 space-y-2">
              <div class="flex items-center justify-between gap-2">
                <span class="font-semibold">{{ section.title }}</span>
                <ChevronRight
                  class="size-4 shrink-0 text-muted-foreground group-hover:text-primary"
                  aria-hidden="true"
                />
              </div>
              <p class="text-sm text-muted-foreground">{{ section.description }}</p>
              <div v-if="section.status" class="min-h-6">
                <div
                  v-if="statsLoading"
                  class="h-5 w-28 rounded-md bg-muted motion-safe:animate-pulse"
                  aria-hidden="true"
                />
                <StatusBadge v-else :status="section.status.status" :label="section.status.label" />
              </div>
            </div>
          </RouterLink>
        </li>
      </ul>
    </nav>
  </div>
</template>

<script setup>
import { computed, ref, onMounted, onUnmounted } from 'vue'
import { RouterLink } from 'vue-router'
import { ChevronRight } from 'lucide-vue-next'
import { useAuthStore } from '@/stores/auth'
import { getCacheStats } from '@/api/admin/cache'
import { getDashboardData } from '@/api/admin/pipeline'
import { getStagingStats } from '@/api/admin/staging'
import { getLogStatistics } from '@/api/admin/logs'
import { listReleases } from '@/api/admin/releases'
import AdminHeader from '@/components/admin/AdminHeader.vue'
import { PAGE_CONTAINER, StatusBadge } from '@/components/shared'
import { ADMIN_ICONS } from '@/utils/adminIcons'

const authStore = useAuthStore()

// null = could not load (rendered as "—" / "unavailable", never as 0)
const stats = ref({
  activeUsers: null,
  cacheHitRate: null,
  pipelineJobs: null,
  pendingStaging: null,
  totalReleases: null,
  errors24h: null
})
const statsLoading = ref(true)

const UNAVAILABLE = { status: 'unknown', label: 'Status unavailable' }
const count = (n, one, many) => `${n.toLocaleString()} ${n === 1 ? one : many}`

/** A live status line for sections with a metric; status maps to StatusBadge tones */
const liveStatus = {
  staging: s =>
    s.pendingStaging === null
      ? UNAVAILABLE
      : s.pendingStaging > 0
        ? { status: 'pending', label: count(s.pendingStaging, 'item to review', 'items to review') }
        : { status: 'completed', label: 'Nothing to review' },
  pipeline: s =>
    s.pipelineJobs === null
      ? UNAVAILABLE
      : s.pipelineJobs > 0
        ? { status: 'running', label: count(s.pipelineJobs, 'job running', 'jobs running') }
        : { status: 'idle', label: 'No job running' },
  logs: s =>
    s.errors24h === null
      ? UNAVAILABLE
      : s.errors24h > 0
        ? { status: 'error', label: count(s.errors24h, 'error in 24 h', 'errors in 24 h') }
        : { status: 'ok', label: 'No errors in 24 h' },
  releases: s =>
    s.totalReleases === null
      ? UNAVAILABLE
      : s.totalReleases > 0
        ? { status: 'info', label: count(s.totalReleases, 'release', 'releases') }
        : { status: 'draft', label: 'No release yet' },
  cache: s =>
    s.cacheHitRate === null
      ? UNAVAILABLE
      : { status: 'info', label: `${s.cacheHitRate}% hit rate` },
  users: s =>
    s.activeUsers === null
      ? UNAVAILABLE
      : { status: 'active', label: count(s.activeUsers, 'active user', 'active users') }
}

const SECTIONS = [
  [
    'staging',
    'Gene Staging',
    'Review gene texts that could not be matched to an HGNC symbol',
    '/admin/staging'
  ],
  ['pipeline', 'Data Pipeline', 'Run and monitor evidence source ingestion', '/admin/pipeline'],
  [
    'annotations',
    'Annotation Sources',
    'Update gene annotations and their schedule',
    '/admin/annotations'
  ],
  [
    'hybridSources',
    'Hybrid Sources',
    'Upload diagnostic panel and literature evidence',
    '/admin/hybrid-sources'
  ],
  [
    'geneCuratorImport',
    'Gene Curator Import',
    'Import finished Gene Curator curations as drafts',
    '/admin/gene-curator-import'
  ],
  [
    'releases',
    'Data Releases',
    'Create, publish and export CalVer data releases',
    '/admin/releases'
  ],
  [
    'backups',
    'Database Backups',
    'Create, restore and download database backups',
    '/admin/backups'
  ],
  ['logs', 'System Logs', 'Search and filter application logs', '/admin/logs'],
  ['cache', 'Cache Management', 'Inspect, warm and clear cache namespaces', '/admin/cache'],
  ['users', 'User Management', 'Manage accounts, roles and access', '/admin/users'],
  ['settings', 'System Settings', 'Review and change application settings', '/admin/settings']
]

const sections = computed(() =>
  SECTIONS.map(([id, title, description, route]) => ({
    id,
    title,
    description,
    route,
    icon: ADMIN_ICONS[id],
    status: liveStatus[id]?.(stats.value) ?? null
  }))
)

const settle = async (fn, pick) => {
  try {
    return pick(await fn())
  } catch (error) {
    window.logService.error('Failed to load dashboard metric:', error)
    return null
  }
}

const loadStats = async () => {
  const [activeUsers, cacheHitRate, pipelineJobs, pendingStaging, totalReleases, errors24h] =
    await Promise.all([
      settle(
        () => authStore.getAllUsers(),
        users => users.filter(u => u.is_active).length
      ),
      settle(getCacheStats, r => Math.round(((r.data.data || r.data).hit_rate || 0) * 100)),
      settle(getDashboardData, r => r.data.data?.summary?.running ?? 0),
      settle(getStagingStats, r => (r.data.data || r.data).total_pending ?? 0),
      settle(listReleases, r => r.data.meta?.total ?? 0),
      settle(
        () => getLogStatistics(24),
        r => (r.data.data || r.data).level_distribution?.find(l => l.level === 'ERROR')?.count ?? 0
      )
    ])
  stats.value = {
    activeUsers,
    cacheHitRate,
    pipelineJobs,
    pendingStaging,
    totalReleases,
    errors24h
  }
  statsLoading.value = false
}

let timer
onMounted(() => {
  loadStats()
  timer = setInterval(loadStats, 30000)
})
onUnmounted(() => clearInterval(timer))
</script>
