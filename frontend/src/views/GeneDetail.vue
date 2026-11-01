<template>
  <div :class="PAGE_CONTAINER">
    <!-- Not Found State (HTTP 404 only) -->
    <div v-if="notFound" class="py-12 text-center">
      <CircleAlert class="mx-auto mb-4 size-16 text-danger" aria-hidden="true" />
      <h1 class="mb-2 text-2xl font-semibold">Gene Not Found</h1>
      <p class="mb-4 text-base text-muted-foreground">
        The gene "{{ $route.params.symbol }}" could not be found in our database.
      </p>
      <Button as-child>
        <RouterLink to="/genes">
          <ArrowLeft :size="16" aria-hidden="true" />
          Back to Gene Browser
        </RouterLink>
      </Button>
    </div>

    <template v-else>
      <PageHeader :title="symbol">
        <template #breadcrumb>
          <Breadcrumb>
            <BreadcrumbList>
              <template v-for="(crumb, index) in breadcrumbs" :key="crumb.title">
                <BreadcrumbItem>
                  <BreadcrumbPage v-if="index === breadcrumbs.length - 1">{{
                    crumb.title
                  }}</BreadcrumbPage>
                  <BreadcrumbLink v-else as-child>
                    <RouterLink :to="crumb.to" class="inline-flex items-center gap-1">
                      <Home v-if="index === 0" class="size-4" aria-hidden="true" />
                      {{ crumb.title }}
                    </RouterLink>
                  </BreadcrumbLink>
                </BreadcrumbItem>
                <BreadcrumbSeparator v-if="index < breadcrumbs.length - 1" />
              </template>
            </BreadcrumbList>
          </Breadcrumb>
        </template>

        <template #description>
          <span class="flex flex-wrap items-center gap-x-2 gap-y-1" data-testid="gene-identity">
            <!-- Two bars wrap like name + MANE + location do, so nothing jumps on load -->
            <template v-if="loading || loadingAnnotations">
              <span
                v-for="w in ['w-48', 'w-60']"
                :key="w"
                :class="['inline-block h-6 rounded-md bg-muted motion-safe:animate-pulse', w]"
                aria-hidden="true"
              />
            </template>
            <template v-for="(id, i) in identifiers" v-else :key="id.id">
              <span v-if="i > 0" class="text-border" aria-hidden="true">·</span>
              <OntologyTerm :id="id.id" :href="id.href" :name="id.name" />
            </template>
            <template v-if="hgnc?.location && !loadingAnnotations">
              <span class="text-border" aria-hidden="true">·</span>
              <span class="text-sm" title="Cytogenetic location">{{ hgnc.location }}</span>
            </template>
          </span>
        </template>

        <!-- Rendered before the gene loads: on mobile the row wraps under the title and shifted the page -->
        <template #actions>
          <Tooltip>
            <TooltipTrigger as-child>
              <Button
                variant="outline"
                size="icon-sm"
                :aria-label="copied === 'symbol' ? 'Symbol copied' : 'Copy gene symbol'"
                @click="copy(symbol, 'symbol', 'Gene symbol copied')"
              >
                <Check v-if="copied === 'symbol'" aria-hidden="true" />
                <Copy v-else aria-hidden="true" />
              </Button>
            </TooltipTrigger>
            <TooltipContent>{{
              copied === 'symbol' ? 'Copied' : 'Copy gene symbol'
            }}</TooltipContent>
          </Tooltip>

          <Button
            variant="outline"
            size="sm"
            :aria-label="copied === 'link' ? 'Link copied' : 'Copy link to this gene'"
            @click="copy(shareUrl, 'link', 'Link copied')"
          >
            <Check v-if="copied === 'link'" aria-hidden="true" />
            <Share2 v-else aria-hidden="true" />
            <span class="hidden sm:inline">{{ copied === 'link' ? 'Copied' : 'Share' }}</span>
          </Button>

          <DropdownMenu>
            <DropdownMenuTrigger as-child>
              <Button variant="outline" size="sm" :disabled="!gene" aria-label="Export gene data">
                <Download aria-hidden="true" />
                <span class="hidden sm:inline">Export</span>
              </Button>
            </DropdownMenuTrigger>
            <DropdownMenuContent align="end">
              <DropdownMenuItem @click="exportJson">
                <FileJson aria-hidden="true" />
                Export as JSON
              </DropdownMenuItem>
              <DropdownMenuItem @click="exportCsv">
                <FileSpreadsheet aria-hidden="true" />
                Export as CSV
              </DropdownMenuItem>
              <DropdownMenuItem @click="printPdf(gene?.approved_symbol ?? symbol)">
                <FileText aria-hidden="true" />
                Export as PDF
              </DropdownMenuItem>
            </DropdownMenuContent>
          </DropdownMenu>

          <VolunteerDialog :symbol="symbol" />

          <Button variant="outline" size="sm" as-child>
            <RouterLink :to="`/genes/${symbol}/structure`">
              <Dna aria-hidden="true" />
              Structure
            </RouterLink>
          </Button>
        </template>
      </PageHeader>

      <DataState
        :loading="loading"
        :error="loadError"
        error-title="Could not load gene"
        @retry="fetchGeneDetails"
      >
        <template #loading>
          <div class="grid grid-cols-12 gap-6" aria-hidden="true">
            <div class="col-span-12 h-90 rounded-xl border bg-card md:order-last md:col-span-4" />
            <div class="col-span-12 h-90 rounded-xl border bg-card md:col-span-8" />
          </div>
        </template>

        <div v-if="gene" class="space-y-6">
          <div class="grid grid-cols-12 items-stretch gap-6">
            <!-- Evidence score first on mobile -->
            <div class="order-first col-span-12 flex md:order-last md:col-span-4">
              <ScoreBreakdown
                :score="gene.evidence_score"
                :tier="gene.evidence_tier"
                :breakdown="gene.score_breakdown"
                :renal-neoplasia="gene.renal_neoplasia"
                class="flex-1"
              />
            </div>
            <div class="col-span-12 flex md:col-span-8">
              <GeneInformationCard
                :gene="gene"
                :annotations="annotations"
                :loading="loadingAnnotations"
                :error="annotationsError"
                class="flex-1"
                @retry="fetchAnnotations"
              />
            </div>
          </div>

          <MondoDiseases
            :annotations="annotations"
            :loading="loadingAnnotations"
            :error="annotationsError"
            @retry="fetchAnnotations"
          />

          <GeneCuratedAssociations :records="curated" />

          <section aria-labelledby="evidence-heading" class="space-y-3">
            <h2 id="evidence-heading" class="text-xl font-semibold">Evidence by source</h2>
            <DataState
              :loading="loadingEvidence"
              :error="evidenceError"
              :empty="!sortedEvidence.length"
              error-title="Could not load evidence"
              empty-message="No evidence records available for this gene."
              @retry="fetchEvidence"
            >
              <template #loading>
                <div class="space-y-3" aria-hidden="true">
                  <!-- One card per source the gene has, so the list does not grow on load -->
                  <div
                    v-for="n in gene?.evidence_count || 4"
                    :key="n"
                    class="h-[6.5rem] rounded-xl border bg-card px-4 py-3"
                  >
                    <div class="h-5 w-32 rounded-md bg-muted motion-safe:animate-pulse" />
                    <div class="mt-2 h-4 w-2/3 rounded-md bg-muted motion-safe:animate-pulse" />
                    <div class="mt-2 h-4 w-40 rounded-md bg-muted motion-safe:animate-pulse" />
                  </div>
                </div>
              </template>
              <div class="space-y-3">
                <EvidenceCard
                  v-for="item in sortedEvidence"
                  :key="`${item.source_name}_${item.id}`"
                  :evidence="item"
                  :gene="gene"
                  :context="evidenceContext"
                />
              </div>
            </DataState>
          </section>
        </div>
      </DataState>
    </template>
  </div>
</template>

<script setup>
import {
  ArrowLeft,
  Check,
  CircleAlert,
  Copy,
  Dna,
  Download,
  FileJson,
  FileSpreadsheet,
  FileText,
  Home,
  Share2
} from 'lucide-vue-next'
import { ref, computed, onMounted } from 'vue'
import { RouterLink, useRoute } from 'vue-router'
import { geneApi } from '../api/genes'
import { curationApi } from '@/api/curation'
import { getGeneDetailBreadcrumbs } from '@/utils/publicBreadcrumbs'
import { sourceDisplayName } from '@/utils/sources'
import { useShareExport, toCsv } from '@/composables/useShareExport'
import { useSeoMeta } from '@/composables/useSeoMeta'
import { useJsonLd, getGeneSchema, getBreadcrumbSchema } from '@/composables/useJsonLd'
import ScoreBreakdown from '../components/ScoreBreakdown.vue'
import EvidenceCard from '../components/evidence/EvidenceCard.vue'
import GeneInformationCard from '../components/gene/GeneInformationCard.vue'
import MondoDiseases from '../components/gene/MondoDiseases.vue'
import GeneCuratedAssociations from '../components/gene/GeneCuratedAssociations.vue'
import VolunteerDialog from '@/components/curation/VolunteerDialog.vue'
import { DataState, OntologyTerm, PageHeader, PAGE_CONTAINER } from '@/components/shared'
import { Button } from '@/components/ui/button'
import { Tooltip, TooltipContent, TooltipTrigger } from '@/components/ui/tooltip'
import {
  Breadcrumb,
  BreadcrumbItem,
  BreadcrumbLink,
  BreadcrumbList,
  BreadcrumbPage,
  BreadcrumbSeparator
} from '@/components/ui/breadcrumb'
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuTrigger
} from '@/components/ui/dropdown-menu'

const route = useRoute()

// Data: the gene call gates the page; evidence and annotations load progressively
const gene = ref(null)
const evidence = ref([])
const annotations = ref(null)
const loading = ref(true)
const loadingEvidence = ref(false)
const loadingAnnotations = ref(false)
const notFound = ref(false)
const loadError = ref(null)
const evidenceError = ref(null)
const annotationsError = ref(null)
const { copied, copy, download, printPdf } = useShareExport()
const curated = ref([])

const symbol = computed(() => gene.value?.approved_symbol ?? String(route.params.symbol ?? ''))
const firstAnnotation = source => annotations.value?.annotations?.[source]?.[0]?.data ?? null
const hgnc = computed(() => firstAnnotation('hgnc'))
const approvedName = computed(() => hgnc.value?.name ?? gene.value?.approved_name ?? null)

const identifiers = computed(() => {
  const ids = []
  const hgncId = gene.value?.hgnc_id ?? hgnc.value?.hgnc_id
  // The approved name is the HGNC record's name; shown first, ID muted
  if (hgncId) ids.push({ id: hgncId, name: approvedName.value })
  const mane = hgnc.value?.mane_select?.refseq_transcript_id
  if (mane)
    ids.push({
      id: mane,
      name: 'MANE Select',
      href: `https://www.ncbi.nlm.nih.gov/nuccore/${mane}`
    })
  return ids
})

const evidenceContext = computed(() => {
  const hpo = firstAnnotation('hpo')
  return {
    ncbiGeneId: hgnc.value?.ncbi_gene_id ?? hpo?.ncbi_gene_id ?? null
  }
})

// SEO meta tags (reactive — updates when gene data loads)
useSeoMeta({
  title: computed(() => {
    if (!gene.value) return 'Gene Detail'
    const name = approvedName.value || ''
    return name
      ? `${gene.value.approved_symbol} (${name}) — Kidney Disease Gene Evidence`
      : `${gene.value.approved_symbol} — Kidney Disease Gene Evidence`
  }),
  description: computed(() => {
    if (!gene.value) return 'Detailed gene information with evidence scores and annotations.'
    const g = gene.value
    const parts = [`${g.approved_symbol} kidney disease gene`]
    if (approvedName.value) parts.push(approvedName.value)
    if (g.hgnc_id) parts.push(g.hgnc_id)
    if (g.evidence_score != null)
      parts.push(`evidence score ${Math.round(g.evidence_score * 10) / 10}`)
    return parts.join(' — ') + '. Multi-source evidence and annotations from KGDB.'
  }),
  canonicalPath: computed(() => `/genes/${route.params.symbol}`)
})

const breadcrumbs = computed(() => getGeneDetailBreadcrumbs(symbol.value))

// Gene JSON-LD (reactive — updates when gene data loads)
useJsonLd(
  computed(() => {
    if (!gene.value) return { '@context': 'https://schema.org', '@type': 'Gene', name: 'Loading' }
    return getGeneSchema(gene.value)
  })
)

// Breadcrumb JSON-LD
useJsonLd(computed(() => getBreadcrumbSchema(breadcrumbs.value)))

const sortedEvidence = computed(() =>
  [...evidence.value].sort((a, b) => (b.normalized_score ?? 0) - (a.normalized_score ?? 0))
)

// Above-the-fold calls get this long to settle before the body reveals; a slower one renders progressively
const REVEAL_BUDGET_MS = 1000

const fetchGeneDetails = async () => {
  loading.value = true
  loadError.value = null
  notFound.value = false
  // Evidence is the slowest call and keyed by symbol: start it with the gene call (it sits below the fold)
  fetchEvidence(route.params.symbol)
  try {
    gene.value = await geneApi.getGene(route.params.symbol)
  } catch (error) {
    window.logService.error('Failed to fetch gene details:', error)
    gene.value = null
    // Only a 404 means "not in the database"; anything else is a failed request
    if (error?.response?.status === 404) notFound.value = true
    else loadError.value = new Error("Couldn't load gene data from the server.")
    loading.value = false
    return
  }
  // One reveal: cards that would otherwise insert or collapse after first paint shifted the page
  await Promise.race([
    Promise.all([fetchAnnotations(), fetchCurated()]),
    new Promise(resolve => setTimeout(resolve, REVEAL_BUDGET_MS))
  ])
  loading.value = false
}

// Published records only (the public endpoint); none or a failed request shows nothing (issue 379)
const fetchCurated = async () => {
  try {
    curated.value = (
      await curationApi.listPublished({ gene_symbol: gene.value.approved_symbol })
    ).data
  } catch (error) {
    window.logService.warn('Curated associations unavailable', error)
  }
}

const fetchEvidence = async (symbol = gene.value?.approved_symbol) => {
  if (!symbol) return
  loadingEvidence.value = true
  evidenceError.value = null
  try {
    const response = await geneApi.getGeneEvidence(symbol)
    evidence.value = response.evidence || []
  } catch (error) {
    window.logService.error('Failed to fetch evidence:', error)
    evidence.value = []
    evidenceError.value = new Error("Couldn't load evidence from the server.")
  } finally {
    loadingEvidence.value = false
  }
}

const fetchAnnotations = async () => {
  if (!gene.value) return
  loadingAnnotations.value = true
  annotationsError.value = null
  try {
    annotations.value = await geneApi.getGeneAnnotations(gene.value.id)
  } catch (error) {
    window.logService.error('Failed to fetch annotations:', error)
    annotations.value = null
    annotationsError.value = new Error("Couldn't load annotations from the server.")
  } finally {
    loadingAnnotations.value = false
  }
}

const shareUrl = computed(() =>
  typeof window === 'undefined' ? '' : `${window.location.origin}/genes/${symbol.value}`
)

const exportJson = () => {
  if (!gene.value) return
  download(
    JSON.stringify(gene.value, null, 2),
    'application/json',
    `${gene.value.approved_symbol}.json`
  )
}

const exportCsv = () => {
  if (!gene.value) return
  const g = gene.value
  const sources = Object.entries(g.score_breakdown ?? {}).filter(([, v]) => Number.isFinite(v))
  const headers = [
    'Symbol',
    'Approved name',
    'HGNC ID',
    'Evidence score',
    'Evidence tier',
    ...sources.map(([s]) => `${sourceDisplayName(s)} score`)
  ]
  const row = [
    g.approved_symbol,
    approvedName.value,
    g.hgnc_id,
    g.evidence_score,
    g.evidence_tier,
    ...sources.map(([, v]) => v)
  ]
  download(toCsv([headers, row]), 'text/csv', `${g.approved_symbol}.csv`)
}

onMounted(fetchGeneDetails)
</script>
