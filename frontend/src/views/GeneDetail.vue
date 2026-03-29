<template>
  <div>
    <!-- Loading State -->
    <div v-if="loading" class="text-center py-12">
      <div
        class="mx-auto h-16 w-16 animate-spin rounded-full border-4 border-primary border-t-transparent"
      />
      <p class="text-lg mt-4 text-muted-foreground">Loading gene information...</p>
    </div>

    <!-- Main Content -->
    <div v-else-if="gene">
      <!-- Breadcrumb Navigation -->
      <div class="px-6 py-2 bg-muted">
        <Breadcrumb>
          <BreadcrumbList>
            <template v-for="(crumb, index) in breadcrumbs" :key="index">
              <BreadcrumbItem>
                <BreadcrumbLink v-if="crumb.to" :href="crumb.to">
                  <Home v-if="index === 0" class="size-4 mr-1 inline-block" />
                  {{ crumb.title }}
                </BreadcrumbLink>
                <BreadcrumbPage v-else>{{ crumb.title }}</BreadcrumbPage>
              </BreadcrumbItem>
              <BreadcrumbSeparator v-if="index < breadcrumbs.length - 1" />
            </template>
          </BreadcrumbList>
        </Breadcrumb>
      </div>

      <div class="container mx-auto px-4 py-6">
        <!-- Gene Header -->
        <div class="flex items-start justify-between gap-2 mb-6">
          <div class="flex items-center min-w-0">
            <RouterLink to="/genes" aria-label="Back to gene browser">
              <Button
                variant="ghost"
                size="icon"
                class="mr-2 shrink-0"
                aria-label="Back to gene browser"
              >
                <ArrowLeft :size="16" />
              </Button>
            </RouterLink>
            <div class="min-w-0">
              <div class="flex items-center gap-1">
                <h1 class="text-2xl sm:text-3xl font-bold truncate">
                  {{ gene.approved_symbol }}
                </h1>
                <Button
                  variant="ghost"
                  size="icon"
                  class="shrink-0 size-7"
                  aria-label="Copy gene symbol"
                  @click="copyGeneSymbol"
                >
                  <Copy :size="14" class="text-muted-foreground" />
                </Button>
              </div>
            </div>
          </div>

          <!-- Action Buttons -->
          <div class="flex gap-1 sm:gap-2 shrink-0">
            <!-- Curator/Admin Edit Button -->
            <Button v-if="authStore.isCurator" variant="secondary" size="sm" @click="editGene">
              <Pencil :size="16" />
              <span class="hidden sm:inline">Edit</span>
            </Button>

            <!-- Share: copies URL -->
            <Button variant="outline" size="sm" aria-label="Copy link to gene" @click="shareGene">
              <Share2 :size="16" />
              <span class="hidden sm:inline">Share</span>
            </Button>

            <!-- Export dropdown with JSON/CSV -->
            <DropdownMenu>
              <DropdownMenuTrigger as-child>
                <Button variant="outline" size="sm" aria-label="Export gene data">
                  <Download :size="16" />
                  <span class="hidden sm:inline">Export</span>
                </Button>
              </DropdownMenuTrigger>
              <DropdownMenuContent align="end">
                <DropdownMenuItem @click="exportJson">
                  <FileJson :size="16" class="mr-2" />
                  Export as JSON
                </DropdownMenuItem>
                <DropdownMenuItem @click="exportCsv">
                  <FileSpreadsheet :size="16" class="mr-2" />
                  Export as CSV
                </DropdownMenuItem>
              </DropdownMenuContent>
            </DropdownMenu>
          </div>
        </div>

        <!-- Overview Cards -->
        <div class="grid grid-cols-12 gap-6 mb-6 items-stretch">
          <!-- Evidence Score Visualization with Breakdown (shown first on mobile) -->
          <div class="col-span-12 md:col-span-4 flex order-first md:order-last">
            <ScoreBreakdown
              :score="gene.evidence_score"
              :breakdown="gene.score_breakdown"
              variant="card"
              class="flex-1"
            />
          </div>

          <!-- Gene Information Card -->
          <div class="col-span-12 md:col-span-8 flex">
            <GeneInformationCard
              :gene="gene"
              :annotations="annotations"
              :loading-annotations="loadingAnnotations"
              class="flex-1"
            />
          </div>
        </div>

        <!-- Evidence Details Section -->
        <div class="mb-6">
          <h2 class="text-2xl font-medium mb-4">Evidence Details</h2>

          <!-- Evidence Cards -->
          <Accordion v-if="sortedEvidence.length > 0" type="multiple" class="space-y-2">
            <EvidenceCard
              v-for="item in sortedEvidence"
              :key="`${item.source}_${item.source_id}`"
              :evidence="item"
            />
          </Accordion>
          <div v-else-if="loadingEvidence" class="text-center py-8">
            <div
              class="mx-auto h-8 w-8 animate-spin rounded-full border-4 border-primary border-t-transparent"
            />
            <p class="text-sm mt-2 text-muted-foreground">Loading evidence...</p>
          </div>
          <div v-else class="text-center py-8">
            <Info class="mx-auto size-12 text-muted-foreground" />
            <p class="text-base mt-2 text-muted-foreground">No evidence records available</p>
          </div>
        </div>
      </div>
    </div>

    <!-- Error State -->
    <div v-else class="text-center py-12">
      <CircleAlert class="mx-auto size-16 text-destructive mb-4" />
      <h2 class="text-2xl mb-2">Gene Not Found</h2>
      <p class="text-base text-muted-foreground mb-4">
        The gene "{{ $route.params.symbol }}" could not be found in our database.
      </p>
      <RouterLink to="/genes">
        <Button>
          <ArrowLeft :size="16" />
          Back to Gene Browser
        </Button>
      </RouterLink>
    </div>
  </div>
</template>

<script setup>
import {
  Home,
  ChevronRight,
  Info,
  CircleAlert,
  ArrowLeft,
  Download,
  Share2,
  Pencil,
  Copy,
  FileJson,
  FileSpreadsheet
} from 'lucide-vue-next'
import { ref, computed, onMounted } from 'vue'
import { RouterLink, useRoute } from 'vue-router'
import { geneApi } from '../api/genes'
import { useAuthStore } from '../stores/auth'
import { getGeneDetailBreadcrumbs } from '@/utils/publicBreadcrumbs'
import { useSeoMeta } from '@/composables/useSeoMeta'
import { useJsonLd, getGeneSchema, getBreadcrumbSchema } from '@/composables/useJsonLd'
import ScoreBreakdown from '../components/ScoreBreakdown.vue'
import EvidenceCard from '../components/evidence/EvidenceCard.vue'
import GeneInformationCard from '../components/gene/GeneInformationCard.vue'

import { Button } from '@/components/ui/button'
import { Accordion } from '@/components/ui/accordion'
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

// Suppress unused import warning for icons used only in template
void ChevronRight

const route = useRoute()
const authStore = useAuthStore()

// Data
const gene = ref(null)
const evidence = ref([])
const annotations = ref(null)
const loading = ref(true)
const loadingEvidence = ref(false)
const loadingAnnotations = ref(false)

// SEO meta tags (reactive — updates when gene data loads)
useSeoMeta({
  title: computed(() => {
    if (!gene.value) return 'Gene Detail'
    const name = gene.value.approved_name || ''
    return name
      ? `${gene.value.approved_symbol} (${name}) — Kidney Disease Gene Evidence`
      : `${gene.value.approved_symbol} — Kidney Disease Gene Evidence`
  }),
  description: computed(() => {
    if (!gene.value) return 'Detailed gene information with evidence scores and annotations.'
    const g = gene.value
    const parts = [`${g.approved_symbol} kidney disease gene`]
    if (g.approved_name) parts.push(g.approved_name)
    if (g.hgnc_id) parts.push(g.hgnc_id)
    if (g.evidence_score != null)
      parts.push(`evidence score ${Math.round(g.evidence_score * 10) / 10}`)
    return parts.join(' — ') + '. Multi-source evidence and annotations from KGDB.'
  }),
  canonicalPath: computed(() => `/genes/${route.params.symbol}`)
})

// Computed - Using utility function for consistency
const breadcrumbs = computed(() =>
  getGeneDetailBreadcrumbs(gene.value?.approved_symbol || 'Loading...')
)

// Gene JSON-LD (reactive — updates when gene data loads)
useJsonLd(
  computed(() => {
    if (!gene.value) return { '@context': 'https://schema.org', '@type': 'Gene', name: 'Loading' }
    return getGeneSchema(gene.value)
  })
)

// Breadcrumb JSON-LD
useJsonLd(computed(() => getBreadcrumbSchema(breadcrumbs.value)))

const sortedEvidence = computed(() => {
  return [...evidence.value].sort((a, b) => (b.score || 0) - (a.score || 0))
})

const fetchGeneDetails = async () => {
  loading.value = true
  try {
    const response = await geneApi.getGene(route.params.symbol)
    gene.value = response
    await Promise.all([fetchEvidence(), fetchAnnotations()])
  } catch (error) {
    window.logService.error('Failed to fetch gene details:', error)
    gene.value = null
  } finally {
    loading.value = false
  }
}

const fetchEvidence = async () => {
  if (!gene.value) return

  loadingEvidence.value = true
  try {
    const response = await geneApi.getGeneEvidence(gene.value.approved_symbol)
    evidence.value = response.evidence || []
  } catch (error) {
    window.logService.error('Failed to fetch evidence:', error)
    evidence.value = []
  } finally {
    loadingEvidence.value = false
  }
}

const fetchAnnotations = async () => {
  if (!gene.value) return

  loadingAnnotations.value = true
  try {
    const response = await geneApi.getGeneAnnotations(gene.value.id)
    annotations.value = response
  } catch (error) {
    window.logService.error('Failed to fetch annotations:', error)
    annotations.value = null
  } finally {
    loadingAnnotations.value = false
  }
}

const copyGeneSymbol = () => {
  if (gene.value?.approved_symbol) {
    navigator.clipboard.writeText(gene.value.approved_symbol)
  }
}

const editGene = () => {
  // TODO: Implement gene editing functionality
  window.logService.info('Edit gene:', gene.value?.approved_symbol)
}

const shareGene = () => {
  navigator.clipboard.writeText(window.location.href)
}

const exportJson = () => {
  if (!gene.value) return
  const data = JSON.stringify(gene.value, null, 2)
  const blob = new Blob([data], { type: 'application/json' })
  const url = URL.createObjectURL(blob)
  const a = document.createElement('a')
  a.href = url
  a.download = `${gene.value.approved_symbol}.json`
  a.click()
  URL.revokeObjectURL(url)
}

const exportCsv = () => {
  if (!gene.value) return
  const headers = ['Symbol', 'HGNC ID', 'Evidence Score', 'Evidence Tier']
  const row = [
    gene.value.approved_symbol,
    gene.value.hgnc_id || '',
    gene.value.evidence_score ?? '',
    gene.value.evidence_tier || ''
  ]
  const csv = [headers.join(','), row.join(',')].join('\n')
  const blob = new Blob([csv], { type: 'text/csv' })
  const url = URL.createObjectURL(blob)
  const a = document.createElement('a')
  a.href = url
  a.download = `${gene.value.approved_symbol}.csv`
  a.click()
  URL.revokeObjectURL(url)
}

// Lifecycle
onMounted(() => {
  fetchGeneDetails()
})
</script>
