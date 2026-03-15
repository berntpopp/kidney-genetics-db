<template>
  <div>
    <!-- Hero Section -->
    <div class="w-full bg-gradient-to-br from-primary/10 via-background to-primary/5 py-12 px-4">
      <div class="container mx-auto text-center">
        <!-- Logo with integrated text -->
        <div class="flex items-center justify-center mb-6">
          <KGDBLogo
            :size="logoSize"
            variant="with-text"
            text-layout="horizontal"
            :animated="true"
            :breathing="true"
            :interactive="true"
            @click="router.push('/')"
          />
        </div>

        <h1 class="text-lg md:text-xl font-semibold text-foreground mb-2">
          Kidney Genetics Database
        </h1>
        <p class="text-base md:text-lg text-muted-foreground mx-auto max-w-[600px] mb-6">
          Evidence-based renal &amp; nephrology gene curation with multi-source integration
        </p>
        <form class="flex items-center gap-2 max-w-md mx-auto" @submit.prevent="handleSearch">
          <input
            v-model="searchQuery"
            type="text"
            placeholder="Search PKD1, HGNC:9008, polycystin..."
            aria-label="Search genes"
            class="flex h-10 w-full rounded-md border border-input bg-background px-3 py-2 text-sm ring-offset-background placeholder:text-muted-foreground focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring"
          />
          <button
            type="submit"
            class="inline-flex items-center justify-center rounded-md text-sm font-medium h-10 px-4 bg-primary text-primary-foreground hover:bg-primary/90"
          >
            <Search class="size-4" />
          </button>
        </form>
      </div>
    </div>

    <div class="container mx-auto px-4 -mt-8">
      <!-- Statistics Cards with Gradients -->
      <div class="grid grid-cols-1 sm:grid-cols-2 md:grid-cols-3 gap-4">
        <template v-if="statsLoaded">
          <div
            v-for="(stat, index) in stats"
            :key="stat.title"
            class="stat-card overflow-hidden rounded-lg shadow-sm transition-all"
            :class="{ 'stat-card-clickable cursor-pointer': stat.route }"
            @mouseenter="hoveredCard = index"
            @mouseleave="hoveredCard = null"
            @click="stat.route ? router.push(stat.route) : null"
          >
            <div
              class="p-4 text-center rounded-lg"
              :style="`background: linear-gradient(135deg, ${getGradientColors(stat.color)});`"
            >
              <component :is="stat.icon" class="size-8 text-white mb-2 mx-auto" />
              <div class="text-3xl font-bold text-white">
                {{ stat.value }}
              </div>
              <div class="text-sm text-white/95">
                {{ stat.title }}
              </div>
            </div>
          </div>
        </template>
        <template v-else>
          <div v-for="n in 3" :key="n" class="overflow-hidden rounded-lg shadow-sm">
            <div class="p-4 text-center rounded-lg bg-muted animate-pulse">
              <div class="size-8 rounded-full bg-muted-foreground/20 mb-2 mx-auto" />
              <div class="h-9 w-20 rounded bg-muted-foreground/20 mx-auto mb-2" />
              <div class="h-4 w-28 rounded bg-muted-foreground/20 mx-auto" />
            </div>
          </div>
        </template>
      </div>

      <!-- Data Sources Strip -->
      <div class="mt-8 py-6 bg-muted/50 -mx-4 px-4 rounded-lg">
        <p class="text-sm text-muted-foreground text-center mb-4">
          Integrated from 7 authoritative genomic sources
        </p>
        <div class="flex flex-wrap items-center justify-center gap-4 md:gap-8">
          <RouterLink
            v-for="source in dataSources"
            :key="source.name"
            to="/data-sources"
            class="flex items-center gap-1.5 text-sm font-medium text-muted-foreground hover:text-foreground transition-colors"
          >
            <component :is="source.icon" class="size-4" />
            {{ source.name }}
          </RouterLink>
        </div>
      </div>

      <!-- Key Benefits -->
      <div class="mt-8">
        <h2 class="text-2xl font-medium text-center mb-6">Why Use This Database?</h2>

        <div class="grid grid-cols-1 sm:grid-cols-2 md:grid-cols-3 gap-4">
          <div v-for="benefit in keyBenefits" :key="benefit.title" class="text-center p-4">
            <div
              class="flex h-16 w-16 items-center justify-center rounded-full mx-auto mb-4"
              :style="{ backgroundColor: benefit.bgColor }"
            >
              <component :is="benefit.icon" class="size-6 text-white" />
            </div>
            <h3 class="text-lg font-semibold mb-2">{{ benefit.title }}</h3>
            <p class="text-sm text-muted-foreground">{{ benefit.description }}</p>
          </div>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import {
  Dna,
  DatabaseZap,
  AlarmClockCheck,
  ShieldCheck,
  RefreshCw,
  Microscope,
  Search,
  Unlock,
  Code2
} from 'lucide-vue-next'
import { ref, computed, onMounted } from 'vue'
import { useWindowSize } from '@vueuse/core'
import { useRouter } from 'vue-router'
import { datasourceApi } from '../api/datasources'
import { KGDBLogo } from '@/components/branding'
import { useSeoMeta } from '@/composables/useSeoMeta'
import { useJsonLd, getDatasetSchema } from '@/composables/useJsonLd'

const router = useRouter()

const { width } = useWindowSize()
const hoveredCard = ref<number | null>(null)
const statsLoaded = ref(false)

const searchQuery = ref('')
function handleSearch() {
  const q = searchQuery.value.trim()
  if (q) router.push({ path: '/genes', query: { search: q } })
}

// Responsive logo sizing
const logoSize = computed(() => {
  if (width.value < 640) return 60
  if (width.value < 960) return 100
  return 180
})

const stats = ref([
  {
    title: 'Genes with Evidence',
    value: 0 as number | string,
    color: 'primary',
    icon: Dna,
    route: '/genes'
  },
  {
    title: 'Active Sources',
    value: 0 as number | string,
    color: 'success',
    icon: DatabaseZap,
    route: '/data-sources'
  },
  {
    title: 'Last Update',
    value: 'Loading...' as number | string,
    color: 'info',
    icon: AlarmClockCheck,
    route: null
  }
])

// Reactive gene count for SEO
const geneCountLabel = computed(() => {
  const raw = stats.value[0].value
  if (typeof raw === 'string') {
    const n = parseInt(raw.replace(/,/g, ''), 10)
    return n > 0 ? raw : '5,000+'
  }
  return (raw as number) > 0 ? (raw as number).toLocaleString() : '5,000+'
})

useSeoMeta({
  title: 'Kidney Genetics Database — Renal & Nephrology Gene Evidence Scores',
  description: computed(
    () =>
      `Kidney Genetics Database (KGDB) — the definitive nephrology gene panel and renal genetics resource. Evidence-based curation of ${geneCountLabel.value} kidney disease genes from ClinGen, PanelApp, GenCC, and more.`
  ),
  canonicalPath: '/'
})

// Dataset JSON-LD (reactive — updates when stats load)
useJsonLd(
  computed(() => {
    const geneCount =
      typeof stats.value[0].value === 'string'
        ? parseInt(stats.value[0].value.replace(/,/g, ''), 10) || undefined
        : (stats.value[0].value as number) || undefined
    return getDatasetSchema(geneCount)
  })
)

const dataSources = [
  { name: 'PanelApp', icon: DatabaseZap },
  { name: 'ClinGen', icon: ShieldCheck },
  { name: 'GenCC', icon: RefreshCw },
  { name: 'HPO', icon: Dna },
  { name: 'PubTator', icon: Microscope },
  { name: 'Literature', icon: Search },
  { name: 'Diagnostic Panels', icon: AlarmClockCheck }
]

const keyBenefits = [
  {
    title: 'Evidence-Based',
    description: 'Weighted multi-source scoring from 0-100 with tier classification',
    icon: ShieldCheck,
    bgColor: '#10B981'
  },
  {
    title: 'Multi-Source',
    description: 'Aggregated from 7 clinical and research databases',
    icon: RefreshCw,
    bgColor: '#0EA5E9'
  },
  {
    title: 'Research-Grade',
    description: 'Professional-quality curation workflow with complete audit trails',
    icon: Microscope,
    bgColor: '#8B5CF6'
  },
  {
    title: 'Regularly Updated',
    description: 'Automated pipeline with continuous synchronization',
    icon: AlarmClockCheck,
    bgColor: '#3B82F6'
  },
  {
    title: 'Open Access',
    description: 'Free under CC BY 4.0 — no registration required for browsing',
    icon: Unlock,
    bgColor: '#F59E0B'
  },
  {
    title: 'API Available',
    description: 'JSON:API compliant REST API for programmatic access',
    icon: Code2,
    bgColor: '#EF4444'
  }
]

const getGradientColors = (color: string) => {
  const gradients: Record<string, string> = {
    primary: '#0EA5E9, #0284C7',
    success: '#10B981, #059669',
    info: '#3B82F6, #2563EB',
    secondary: '#8B5CF6, #7C3AED',
    warning: '#F59E0B, #D97706',
    error: '#EF4444, #DC2626'
  }
  return gradients[color] || gradients.primary
}

const formatDate = (dateStr: string | null) => {
  if (!dateStr) return 'Never'
  const date = new Date(dateStr)
  const today = new Date()
  const diffDays = Math.floor((today.getTime() - date.getTime()) / (1000 * 60 * 60 * 24))

  if (diffDays === 0) return 'today'
  if (diffDays === 1) return 'yesterday'
  if (diffDays < 7) return `${diffDays} days ago`
  if (diffDays < 30) return `${Math.floor(diffDays / 7)} weeks ago`
  return date.toLocaleDateString()
}

onMounted(async () => {
  try {
    const sourceResponse = await datasourceApi.getDataSources()

    stats.value[0].value = (sourceResponse.total_unique_genes || 0).toLocaleString()
    stats.value[1].value = sourceResponse.total_active

    if (sourceResponse.last_data_update) {
      stats.value[2].value = formatDate(sourceResponse.last_data_update)
    } else if (sourceResponse.last_pipeline_run) {
      stats.value[2].value = formatDate(sourceResponse.last_pipeline_run)
    } else {
      const mostRecent = sourceResponse.sources
        .filter((s: { stats?: { last_updated?: string } }) => s.stats?.last_updated)
        .map((s: { stats: { last_updated: string } }) => new Date(s.stats.last_updated))
        .sort((a: Date, b: Date) => b.getTime() - a.getTime())[0]

      stats.value[2].value = mostRecent ? formatDate(mostRecent.toISOString()) : 'Never'
    }
  } catch (error) {
    window.logService.error('Error fetching stats:', error)
    stats.value[2].value = 'Error'
  } finally {
    statsLoaded.value = true
  }
})
</script>

<style scoped>
.stat-card {
  transition: all 0.3s cubic-bezier(0.4, 0, 0.2, 1);
}

.stat-card-clickable:hover {
  transform: translateY(-4px) scale(1.02);
  box-shadow:
    0 10px 15px -3px rgb(0 0 0 / 0.1),
    0 4px 6px -4px rgb(0 0 0 / 0.1);
}

.stat-card-clickable:active {
  transform: translateY(-2px) scale(1.01);
  transition-duration: 0.1s;
}

.stat-card-clickable:focus-visible {
  outline: 2px solid hsl(var(--primary));
  outline-offset: 2px;
}

@media (prefers-reduced-motion: reduce) {
  .stat-card {
    transition-duration: 0.01ms !important;
  }

  .stat-card-clickable:hover {
    transform: none;
  }
}
</style>
