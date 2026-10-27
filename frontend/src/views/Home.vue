<template>
  <div>
    <!-- Hero: identity, search and the current state of the ledger -->
    <section class="border-b bg-card">
      <div class="mx-auto w-full max-w-7xl px-4 py-10 text-center sm:px-6 md:py-14 lg:px-8">
        <div class="mb-5 flex items-center justify-center">
          <KGDBLogo
            :size="logoSize"
            variant="with-text"
            text-layout="horizontal"
            :animated="true"
            :breathing="false"
            :interactive="false"
          />
        </div>

        <h1 class="sr-only">
          Kidney-Genetics Database — Renal &amp; Nephrology Gene Evidence Curation
        </h1>
        <p
          class="mx-auto mb-8 max-w-[60ch] text-base text-balance text-muted-foreground md:text-lg"
        >
          One reproducible evidence score and tier for every kidney-disease gene, traceable to its
          sources.
        </p>

        <form
          role="search"
          class="mx-auto mb-6 flex max-w-xl items-center gap-2"
          @submit.prevent="handleSearch"
        >
          <div class="relative w-full">
            <Search
              class="pointer-events-none absolute top-1/2 left-3 size-4 -translate-y-1/2 text-muted-foreground"
              aria-hidden="true"
            />
            <Input
              v-model="searchQuery"
              type="search"
              placeholder="Gene symbol or HGNC ID, e.g. PKD1"
              aria-label="Search genes"
              class="h-11 pl-10"
            />
          </div>
          <Button type="submit" class="h-11 px-5">Search</Button>
        </form>

        <!-- Ledger line: every number comes from the data-sources API -->
        <div class="mx-auto max-w-xl text-left">
          <DataState
            :loading="!statsLoaded"
            :error="statsError"
            error-title="Database statistics are unavailable right now"
            @retry="loadStats"
          >
            <template #loading>
              <div
                class="mx-auto h-5 w-80 max-w-full rounded-md bg-muted motion-safe:animate-pulse"
              />
            </template>
            <p class="flex flex-wrap justify-center gap-x-5 gap-y-1 text-sm text-muted-foreground">
              <RouterLink to="/genes" class="hover:text-foreground hover:underline">
                <span class="font-semibold text-foreground tabular-nums">{{
                  geneCount?.toLocaleString()
                }}</span>
                genes with evidence
              </RouterLink>
              <RouterLink to="/data-sources" class="hover:text-foreground hover:underline">
                <span class="font-semibold text-foreground tabular-nums">{{ activeSources }}</span>
                <template v-if="totalSources"> of {{ totalSources }}</template> sources active
              </RouterLink>
              <span>
                Data updated
                <span class="font-semibold text-foreground tabular-nums">{{ lastUpdate }}</span>
              </span>
            </p>
          </DataState>
        </div>
      </div>
    </section>

    <div class="mx-auto w-full max-w-7xl px-4 sm:px-6 lg:px-8">
      <!-- The evidence story: how a gene earns its tier -->
      <section class="grid gap-10 py-12 lg:grid-cols-2 lg:gap-16" aria-labelledby="how-heading">
        <div>
          <h2 id="how-heading" class="mb-2 text-xl font-semibold">
            From sources to an evidence tier
          </h2>
          <p class="mb-6 max-w-[65ch] text-sm text-muted-foreground">
            Each gene's score is computed from named sources with a documented weighting, so every
            number can be audited back to its line items.
          </p>
          <ol class="space-y-5">
            <li v-for="(step, i) in pipelineSteps" :key="step.title" class="flex gap-4">
              <span
                class="flex size-7 shrink-0 items-center justify-center rounded-full border text-xs font-semibold text-muted-foreground tabular-nums"
                aria-hidden="true"
                >{{ i + 1 }}</span
              >
              <div>
                <h3 class="font-semibold">{{ step.title }}</h3>
                <p class="max-w-[65ch] text-sm text-muted-foreground">{{ step.description }}</p>
              </div>
            </li>
          </ol>
        </div>

        <div>
          <h2 class="mb-2 text-xl font-semibold">Evidence tiers</h2>
          <p class="mb-6 max-w-[65ch] text-sm text-muted-foreground">
            Tiers combine the evidence score with the number of supporting sources.
          </p>
          <ul class="divide-y rounded-xl border bg-card">
            <li
              v-for="tier in tiers"
              :key="tier.key"
              class="flex flex-col gap-1 px-4 py-3 sm:flex-row sm:items-center sm:gap-4"
            >
              <RouterLink
                :to="{ path: '/genes', query: { tier: tier.key } }"
                class="shrink-0 rounded-md focus-visible:ring-2 focus-visible:ring-ring focus-visible:outline-none sm:w-52"
              >
                <Chip :tier="tier.key" tooltip="" class="hover:brightness-95" />
              </RouterLink>
              <span class="text-sm text-muted-foreground">{{ tier.description }}</span>
            </li>
          </ul>
        </div>
      </section>

      <!-- Sources -->
      <section class="border-t py-10" aria-labelledby="sources-heading">
        <div class="flex flex-col gap-4 md:flex-row md:items-baseline md:justify-between">
          <h2 id="sources-heading" class="text-xl font-semibold">Evidence sources</h2>
          <RouterLink to="/data-sources" class="text-sm font-medium text-primary hover:underline">
            Source status and versions
          </RouterLink>
        </div>
        <ul class="mt-4 flex flex-wrap gap-x-6 gap-y-3 text-sm">
          <li v-for="source in SOURCE_NAMES" :key="source">
            <SourceLabel :source="source" />
          </li>
        </ul>
      </section>

      <!-- Why and for whom -->
      <section class="border-t py-10" aria-labelledby="why-heading">
        <h2 id="why-heading" class="mb-6 text-xl font-semibold">Why use this database</h2>
        <dl class="grid gap-6 sm:grid-cols-2 lg:grid-cols-4">
          <div v-for="benefit in keyBenefits" :key="benefit.title">
            <dt class="font-semibold">{{ benefit.title }}</dt>
            <dd class="mt-1 text-sm text-muted-foreground">{{ benefit.description }}</dd>
          </div>
        </dl>
      </section>

      <section class="border-t py-10" aria-labelledby="who-heading">
        <h2 id="who-heading" class="mb-6 text-xl font-semibold">Who is this for</h2>
        <div class="grid gap-8 md:grid-cols-3">
          <div v-for="audience in audiences" :key="audience.title">
            <h3 class="font-semibold">{{ audience.title }}</h3>
            <p class="mt-1 mb-3 text-sm text-muted-foreground">{{ audience.description }}</p>
            <RouterLink
              :to="audience.ctaRoute"
              class="inline-flex items-center gap-1 text-sm font-medium text-primary hover:underline"
            >
              {{ audience.cta }}
              <ArrowRight class="size-3.5" aria-hidden="true" />
            </RouterLink>
          </div>
        </div>
      </section>

      <!-- How to Cite + Affiliation -->
      <section class="border-t py-10 mb-6" aria-labelledby="cite-heading">
        <div class="max-w-3xl">
          <h2 id="cite-heading" class="mb-4 text-xl font-semibold">How to cite</h2>
          <div class="relative mb-3 rounded-md border bg-card p-4 text-sm">
            <p class="pr-10 text-foreground">{{ primaryCitation }}</p>
            <Tooltip>
              <TooltipTrigger as-child>
                <Button
                  variant="ghost"
                  size="icon-sm"
                  class="absolute top-2 right-2"
                  :aria-label="citationCopied ? 'Citation copied' : 'Copy citation'"
                  @click="copyCitation"
                >
                  <Check v-if="citationCopied" class="size-4 text-success" aria-hidden="true" />
                  <Copy v-else class="size-4 text-muted-foreground" aria-hidden="true" />
                </Button>
              </TooltipTrigger>
              <TooltipContent>{{ citationCopied ? 'Copied' : 'Copy citation' }}</TooltipContent>
            </Tooltip>
            <span class="sr-only" aria-live="polite">{{
              citationCopied ? 'Citation copied to clipboard' : ''
            }}</span>
          </div>
          <p class="mb-6 text-xs text-muted-foreground">
            Or cite as: Kidney-Genetics Database. https://kidney-genetics.org. Accessed
            {{ new Date().toISOString().slice(0, 10) }}.
          </p>

          <div class="flex flex-wrap items-center gap-x-4 gap-y-2 text-sm text-muted-foreground">
            <span>Halbritter Lab — Nephrology &amp; Clinical Genetics</span>
            <span aria-hidden="true">·</span>
            <a
              href="https://github.com/berntpopp/kidney-genetics-db"
              target="_blank"
              rel="noopener noreferrer"
              class="inline-flex items-center gap-1.5 transition-colors hover:text-foreground"
            >
              <Github class="size-4" aria-hidden="true" />
              Open source on GitHub
            </a>
            <span aria-hidden="true">·</span>
            <span>CC BY 4.0</span>
          </div>
        </div>
      </section>
    </div>
  </div>
</template>

<script setup lang="ts">
import { formatDate } from '@/utils/formatDate'
import { ArrowRight, Search, Copy, Check, Github } from 'lucide-vue-next'
import { ref, computed, onMounted } from 'vue'
import { useWindowSize } from '@vueuse/core'
import { RouterLink, useRouter } from 'vue-router'
import { datasourceApi } from '../api/datasources'
import { KGDBLogo } from '@/components/branding'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { Tooltip, TooltipContent, TooltipTrigger } from '@/components/ui/tooltip'
import { Chip, DataState, SourceLabel } from '@/components/shared'
import { useSeoMeta } from '@/composables/useSeoMeta'
import { useJsonLd, getDatasetSchema } from '@/composables/useJsonLd'
import { TIER_CONFIG, type TierName } from '@/utils/evidenceTiers'
import { SOURCE_NAMES } from '@/utils/sources'

const router = useRouter()

const { width } = useWindowSize()

const searchQuery = ref('')
function handleSearch() {
  const q = searchQuery.value.trim()
  router.push(q ? { path: '/genes', query: { search: q } } : '/genes')
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
  if (width.value < 960) return 96
  return 140
})

const tiers = (Object.entries(TIER_CONFIG) as [TierName, (typeof TIER_CONFIG)[TierName]][]).map(
  ([key, config]) => ({ key, ...config })
)

// Database statistics (from the data-sources API)
const statsLoaded = ref(false)
const statsError = ref<string | null>(null)
const geneCount = ref<number | null>(null)
const activeSources = ref<number | null>(null)
const totalSources = ref<number | null>(null)
const lastUpdate = ref<string | null>(null)

// Reactive gene count for SEO; prerendered pages state no number rather than a guessed one
const geneCountLabel = computed(() =>
  geneCount.value && geneCount.value > 0 ? `${geneCount.value.toLocaleString()} ` : ''
)

useSeoMeta({
  title: 'Kidney Genetics Database — Renal & Nephrology Gene Evidence Scores',
  description: computed(
    () =>
      `Kidney Genetics Database (KGDB) — the definitive nephrology gene panel and renal genetics resource. Evidence-based curation of ${geneCountLabel.value}kidney disease genes from ClinGen, PanelApp, GenCC, and more.`
  ),
  canonicalPath: '/'
})

// Dataset JSON-LD (reactive — updates when stats load)
useJsonLd(computed(() => getDatasetSchema(geneCount.value || undefined)))

// Configured sources (the chips above) until the API reports its own count

const keyBenefits = computed(() => [
  {
    title: 'Evidence-based',
    description: 'Weighted multi-source scoring from 0 to 100 with a tier per gene'
  },
  {
    title: 'Multi-source',
    description: 'Aggregated from clinical and research databases, each with its provenance'
  },
  {
    title: 'Research-grade',
    description: 'Expert curation workflow with complete audit trails'
  },
  {
    title: 'Open access',
    description: 'Free under CC BY 4.0; no registration required for browsing'
  }
])

const pipelineSteps = [
  {
    title: 'Collect',
    description:
      'Gene-disease associations are gathered from PanelApp, ClinGen, GenCC, HPO, PubTator, curated literature and diagnostic panels.'
  },
  {
    title: 'Score',
    description: `Evidence is aggregated into a weighted score from 0 to 100 and a tier from ${TIER_CONFIG.comprehensive_support.label} to ${TIER_CONFIG.minimal_evidence.label}.`
  },
  {
    title: 'Curate',
    description:
      'Genes are annotated with expression, variants, interactions and phenotypes, and associations are expert-reviewed.'
  }
]

const audiences = [
  {
    title: 'Nephrologists',
    description:
      'Explore evidence-scored gene panels for kidney disease diagnostics and precision medicine.',
    cta: 'Browse genes',
    ctaRoute: '/genes'
  },
  {
    title: 'Geneticists',
    description:
      'Access curated gene-disease associations with cross-referenced variant and phenotype data.',
    cta: 'View data sources',
    ctaRoute: '/data-sources'
  },
  {
    title: 'Bioinformaticians',
    description: 'Query the REST API, download gene lists and integrate with analysis pipelines.',
    cta: 'API documentation',
    ctaRoute: '/about'
  }
]

async function loadStats() {
  statsLoaded.value = false
  statsError.value = null
  try {
    const sourceResponse = await datasourceApi.getDataSources()

    geneCount.value = sourceResponse.total_unique_genes || 0
    // Active = sources with evidence for at least one listed gene, out of all configured
    activeSources.value = sourceResponse.total_active
    totalSources.value = sourceResponse.total_sources ?? null

    const latest =
      sourceResponse.last_data_update ??
      sourceResponse.last_pipeline_run ??
      sourceResponse.sources
        .map((s: { stats?: { last_updated?: string } }) => s.stats?.last_updated)
        .filter((d: string | undefined): d is string => !!d)
        .sort()
        .at(-1)
    lastUpdate.value = latest ? formatDate(latest) : 'not yet'
  } catch (error) {
    window.logService.error('Error fetching stats:', error)
    statsError.value = 'Try again in a moment.'
  } finally {
    statsLoaded.value = true
  }
}

onMounted(loadStats)
</script>
