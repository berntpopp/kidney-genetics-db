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
            :breathing="false"
            :interactive="true"
            @click="router.push('/')"
          />
        </div>

        <h1 class="sr-only">
          Kidney Genetics Database — Renal &amp; Nephrology Gene Evidence Curation
        </h1>
        <p
          class="text-base md:text-lg text-muted-foreground mx-auto max-w-[600px] md:whitespace-nowrap mb-10"
        >
          Evidence-based renal &amp; nephrology gene curation with multi-source integration
        </p>

        <!-- Gene search -->
        <form
          class="flex items-center gap-3 max-w-xl mx-auto px-4 mb-4"
          @submit.prevent="handleSearch"
        >
          <div class="relative w-full">
            <Search
              class="absolute left-3 top-1/2 -translate-y-1/2 size-4 text-muted-foreground pointer-events-none"
            />
            <input
              v-model="searchQuery"
              type="text"
              placeholder="Search by gene symbol, HGNC ID, or keyword..."
              aria-label="Search genes"
              class="flex h-11 w-full rounded-lg border border-input bg-background pl-10 pr-3 py-2 text-sm shadow-sm ring-offset-background placeholder:text-muted-foreground focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring"
            />
          </div>
          <button
            type="submit"
            aria-label="Search genes"
            class="inline-flex items-center justify-center rounded-lg text-sm font-medium h-11 px-5 bg-primary text-primary-foreground hover:bg-primary/90 shadow-sm"
          >
            Search
          </button>
        </form>
      </div>
    </div>

    <div class="container mx-auto px-4 -mt-8">
      <!-- Statistics Cards with Gradients -->
      <div class="grid grid-cols-1 sm:grid-cols-2 md:grid-cols-3 gap-4">
        <template v-if="statsLoaded">
          <div
            v-for="stat in stats"
            :key="stat.title"
            class="stat-card overflow-hidden rounded-lg shadow-sm transition-all"
            :class="{ 'stat-card-clickable cursor-pointer': stat.route }"
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
      <div class="py-12">
        <h2 class="text-2xl font-medium text-center mb-6">Why Use This Database?</h2>

        <div class="grid grid-cols-1 sm:grid-cols-2 gap-4">
          <div v-for="benefit in keyBenefits" :key="benefit.title" class="text-center p-4">
            <div
              class="flex h-12 w-12 items-center justify-center rounded-full bg-primary/10 text-primary mx-auto mb-4"
            >
              <component :is="benefit.icon" class="size-5" />
            </div>
            <h3 class="text-lg font-semibold mb-2">{{ benefit.title }}</h3>
            <p class="text-sm text-muted-foreground">{{ benefit.description }}</p>
          </div>
        </div>
      </div>

      <!-- How It Works -->
      <div class="py-12 bg-muted/30 -mx-4 px-4 rounded-lg">
        <h2 class="text-2xl font-medium text-center mb-8">How It Works</h2>
        <div class="grid grid-cols-1 md:grid-cols-3 gap-4">
          <div v-for="step in pipelineSteps" :key="step.step" class="text-center p-4">
            <div
              class="flex h-12 w-12 items-center justify-center rounded-full bg-primary/10 text-primary mx-auto mb-3"
            >
              <component :is="step.icon" class="size-6" />
            </div>
            <div class="text-xs font-bold text-primary mb-1">Step {{ step.step }}</div>
            <h3 class="text-lg font-semibold mb-2">{{ step.title }}</h3>
            <p class="text-sm text-muted-foreground">{{ step.description }}</p>
          </div>
        </div>
      </div>

      <!-- Who Is This For? -->
      <div class="py-12">
        <h2 class="text-2xl font-medium text-center mb-8">Who Is This For?</h2>
        <div class="grid grid-cols-1 md:grid-cols-3 gap-4">
          <div
            v-for="audience in audiences"
            :key="audience.title"
            class="rounded-lg border border-border p-6 text-center hover:shadow-sm transition-shadow"
          >
            <div
              class="flex h-14 w-14 items-center justify-center rounded-full bg-primary/10 text-primary mx-auto mb-4"
            >
              <component :is="audience.icon" class="size-7" />
            </div>
            <h3 class="text-lg font-semibold mb-2">{{ audience.title }}</h3>
            <p class="text-sm text-muted-foreground mb-4">{{ audience.description }}</p>
            <RouterLink
              :to="audience.ctaRoute"
              class="text-sm font-medium text-primary hover:text-primary/80"
            >
              {{ audience.cta }} &rarr;
            </RouterLink>
          </div>
        </div>
      </div>

      <!-- How to Cite + Affiliation -->
      <div class="py-12 bg-muted/30 -mx-4 px-4 rounded-lg mb-16">
        <div class="max-w-2xl mx-auto">
          <h2 class="text-2xl font-medium text-center mb-6">How to Cite</h2>
          <div class="relative rounded-md border-l-4 border-primary bg-background p-4 text-sm mb-3">
            <p class="text-muted-foreground pr-8">{{ primaryCitation }}</p>
            <button
              class="absolute top-3 right-3 p-1.5 rounded-md hover:bg-muted"
              :aria-label="citationCopied ? 'Citation copied' : 'Copy citation'"
              @click="copyCitation"
            >
              <Check v-if="citationCopied" class="size-4 text-green-600" />
              <Copy v-else class="size-4 text-muted-foreground" />
            </button>
            <span class="sr-only" aria-live="polite">{{
              citationCopied ? 'Citation copied to clipboard' : ''
            }}</span>
          </div>
          <p class="text-xs text-muted-foreground text-center mb-8">
            Or cite as: Kidney Genetics Database. https://kidney-genetics.org. Accessed
            {{ new Date().toISOString().slice(0, 10) }}.
          </p>

          <div class="flex items-center justify-center gap-4 text-sm text-muted-foreground">
            <span>Halbritter Lab — Nephrology &amp; Clinical Genetics</span>
            <span class="text-border">·</span>
            <a
              href="https://github.com/berntpopp/kidney-genetics-db"
              target="_blank"
              rel="noopener noreferrer"
              class="inline-flex items-center gap-1.5 hover:text-foreground transition-colors"
              aria-label="Open Source on GitHub"
            >
              <Github class="size-4" />
              Open Source
            </a>
            <span class="text-border">·</span>
            <span>CC BY 4.0</span>
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
  Code2,
  Download,
  BarChart3,
  CheckCircle,
  Stethoscope,
  Copy,
  Check,
  Github
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
const statsLoaded = ref(false)

const searchQuery = ref('')
function handleSearch() {
  const q = searchQuery.value.trim()
  if (q) router.push({ path: '/genes', query: { search: q } })
}

const citationCopied = ref(false)
const primaryCitation =
  'Popp B, Rank N, Wolff A, Halbritter J. Kidney-Genetics: An evidence-based database for kidney disease associated genes. Nephrol Dial Transplant. 2024;39(Supplement_1):gfae069-0787-2170.'

function copyCitation() {
  if (typeof navigator !== 'undefined' && navigator.clipboard) {
    navigator.clipboard.writeText(primaryCitation)
    citationCopied.value = true
    setTimeout(() => {
      citationCopied.value = false
    }, 2000)
  }
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
    color: 'primary',
    icon: DatabaseZap,
    route: '/data-sources'
  },
  {
    title: 'Last Update',
    value: 'Loading...' as number | string,
    color: 'primary',
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
    icon: ShieldCheck
  },
  {
    title: 'Multi-Source',
    description: 'Aggregated from 7 clinical and research databases',
    icon: RefreshCw
  },
  {
    title: 'Research-Grade',
    description: 'Professional-quality curation workflow with complete audit trails',
    icon: Microscope
  },
  {
    title: 'Open Access',
    description: 'Free under CC BY 4.0 — no registration required for browsing',
    icon: Unlock
  }
]

const pipelineSteps = [
  {
    step: 1,
    title: 'Collect',
    icon: Download,
    description:
      'Gene-disease associations gathered from PanelApp, ClinGen, GenCC, HPO, PubTator, literature, and diagnostic panels'
  },
  {
    step: 2,
    title: 'Score',
    icon: BarChart3,
    description:
      'Evidence aggregated into a weighted confidence score (0-100) with tier classification from Definitive to Minimal'
  },
  {
    step: 3,
    title: 'Curate',
    icon: CheckCircle,
    description:
      'Validated genes with annotations including expression, variants, interactions, and phenotypes'
  }
]

const audiences = [
  {
    title: 'Nephrologists',
    icon: Stethoscope,
    description:
      'Explore evidence-scored gene panels for kidney disease diagnostics and precision medicine',
    cta: 'Browse Genes',
    ctaRoute: '/genes'
  },
  {
    title: 'Geneticists',
    icon: Dna,
    description:
      'Access curated gene-disease associations with cross-referenced variant and phenotype data',
    cta: 'View Data Sources',
    ctaRoute: '/data-sources'
  },
  {
    title: 'Bioinformaticians',
    icon: Code2,
    description: 'Query via REST API, download gene lists, and integrate with analysis pipelines',
    cta: 'API Documentation',
    ctaRoute: '/about'
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
