<template>
  <div :class="PAGE_CONTAINER">
    <PageHeader
      :title="gene?.approved_symbol ?? symbol"
      description="Gene structure and protein domains with ClinVar variants"
    >
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
      <template #actions>
        <Button variant="outline" size="sm" as-child>
          <RouterLink :to="`/genes/${symbol}`">
            <ArrowLeft aria-hidden="true" />
            Gene details
          </RouterLink>
        </Button>
      </template>
    </PageHeader>

    <DataState
      :loading="loading"
      :error="error"
      error-title="Could not load gene data"
      min-height="24rem"
      @retry="fetchGeneData"
    >
      <div v-if="gene">
        <!-- Tabbed Visualization -->
        <Tabs v-model="activeTab">
          <TabsList class="mb-3">
            <TabsTrigger value="gene">
              <Dna class="size-4 mr-1.5" />
              Gene Structure
              <span v-if="ensemblData" class="ml-2 text-xs text-muted-foreground hidden sm:inline">
                {{ ensemblData.exon_count }} exons &middot;
                {{ ensemblData.gene_length?.toLocaleString() }} bp
              </span>
            </TabsTrigger>
            <TabsTrigger value="protein">
              <Atom class="size-4 mr-1.5" />
              Protein Domains
              <span v-if="uniprotData" class="ml-2 text-xs text-muted-foreground hidden sm:inline">
                {{ uniprotData.length?.toLocaleString() }} aa &middot;
                {{ uniprotData.domain_count }} domains
              </span>
            </TabsTrigger>
          </TabsList>

          <!-- Gene Structure Tab -->
          <TabsContent value="gene" class="mt-0">
            <Card>
              <CardHeader class="py-2 px-4">
                <div
                  v-if="ensemblData"
                  class="flex flex-wrap items-center gap-x-2 gap-y-0.5 text-xs text-muted-foreground"
                >
                  <a
                    v-if="ensemblData.canonical_transcript?.refseq_transcript_id"
                    :href="`https://www.ncbi.nlm.nih.gov/nuccore/${ensemblData.canonical_transcript.refseq_transcript_id}`"
                    target="_blank"
                    rel="noopener noreferrer"
                    class="hover:underline"
                  >
                    {{ ensemblData.canonical_transcript.refseq_transcript_id }}
                    <ExternalLink :size="10" class="inline" />
                  </a>
                  <span class="text-muted-foreground/40">|</span>
                  <a
                    :href="`https://www.ensembl.org/Homo_sapiens/Gene/Summary?g=${ensemblData.gene_id}`"
                    target="_blank"
                    rel="noopener noreferrer"
                    class="hover:underline"
                  >
                    {{ ensemblData.gene_id }}
                    <ExternalLink :size="10" class="inline" />
                  </a>
                  <span class="text-muted-foreground/40">|</span>
                  <span>
                    chr{{ ensemblData.chromosome }}:{{ ensemblData.start?.toLocaleString() }}-{{
                      ensemblData.end?.toLocaleString()
                    }}
                    ({{ ensemblData.strand }})
                  </span>
                </div>
              </CardHeader>
              <CardContent>
                <DataState v-if="loadingEnsembl" loading min-height="280px" />
                <div v-else-if="!ensemblData" class="text-center py-8">
                  <CircleAlert class="mx-auto size-12 text-warning" aria-hidden="true" />
                  <p class="text-base mt-2 text-muted-foreground">
                    Gene structure data not available from Ensembl
                  </p>
                  <Button variant="outline" size="sm" class="mt-2" @click="fetchEnsemblData">
                    Retry
                  </Button>
                </div>
                <ErrorBoundary
                  v-else
                  fallback-message="Gene structure visualization failed to render."
                >
                  <GeneStructureVisualization
                    :gene-symbol="gene.approved_symbol"
                    :ensembl-data="ensemblData"
                    :clinvar-data="clinvarData"
                    :uniprot-data="uniprotData"
                  />
                </ErrorBoundary>
              </CardContent>
            </Card>
          </TabsContent>

          <!-- Protein Domains Tab -->
          <TabsContent value="protein" class="mt-0">
            <Card>
              <CardHeader class="py-2 px-4">
                <div
                  v-if="uniprotData"
                  class="flex flex-wrap items-center gap-x-2 gap-y-0.5 text-xs text-muted-foreground"
                >
                  <a
                    :href="`https://www.uniprot.org/uniprotkb/${uniprotData.accession}`"
                    target="_blank"
                    rel="noopener noreferrer"
                    class="hover:underline"
                  >
                    {{ uniprotData.accession }}
                    <ExternalLink :size="10" class="inline" />
                  </a>
                  <span class="text-muted-foreground/40">|</span>
                  <span>{{ uniprotData.entry_name }}</span>
                  <span v-if="uniprotData.has_transmembrane" class="text-muted-foreground/40">
                    |
                  </span>
                  <span v-if="uniprotData.has_transmembrane">Transmembrane</span>
                </div>
              </CardHeader>
              <CardContent>
                <DataState v-if="loadingUniprot" loading min-height="280px" />
                <div v-else-if="!uniprotData" class="text-center py-8">
                  <CircleAlert class="mx-auto size-12 text-warning" aria-hidden="true" />
                  <p class="text-base mt-2 text-muted-foreground">
                    Protein domain data not available from UniProt
                  </p>
                  <Button variant="outline" size="sm" class="mt-2" @click="fetchUniprotData">
                    Retry
                  </Button>
                </div>
                <ErrorBoundary
                  v-else
                  fallback-message="Protein domain visualization failed to render."
                >
                  <ProteinDomainVisualization
                    :uniprot-data="uniprotData"
                    :clinvar-data="clinvarData"
                  />
                </ErrorBoundary>
              </CardContent>
            </Card>
          </TabsContent>
        </Tabs>
      </div>
    </DataState>
  </div>
</template>

<script setup>
import { ref, computed, onMounted, defineAsyncComponent } from 'vue'
import { RouterLink } from 'vue-router'
import ErrorBoundary from '@/components/ui/error-boundary/ErrorBoundary.vue'
import ComponentSkeleton from '@/components/ui/ComponentSkeleton.vue'
import ComponentError from '@/components/ui/ComponentError.vue'
import { geneApi } from '@/api/genes'
import { getGeneStructureBreadcrumbs } from '@/utils/publicBreadcrumbs'
import { useSeoMeta } from '@/composables/useSeoMeta'
import { useJsonLd, getGeneSchema, getBreadcrumbSchema } from '@/composables/useJsonLd'
const GeneStructureVisualization = defineAsyncComponent({
  loader: () => import('@/components/visualizations/GeneStructureVisualization.vue'),
  loadingComponent: ComponentSkeleton,
  errorComponent: ComponentError,
  delay: 200,
  timeout: 10000
})

const ProteinDomainVisualization = defineAsyncComponent({
  loader: () => import('@/components/visualizations/ProteinDomainVisualization.vue'),
  loadingComponent: ComponentSkeleton,
  errorComponent: ComponentError,
  delay: 200,
  timeout: 10000
})
import { Card, CardHeader, CardContent } from '@/components/ui/card'
import { DataState, PageHeader, PAGE_CONTAINER } from '@/components/shared'
import { Button } from '@/components/ui/button'
import {
  Breadcrumb,
  BreadcrumbItem,
  BreadcrumbLink,
  BreadcrumbList,
  BreadcrumbPage,
  BreadcrumbSeparator
} from '@/components/ui/breadcrumb'
import { Tabs, TabsList, TabsTrigger, TabsContent } from '@/components/ui/tabs'
import { ArrowLeft, Atom, CircleAlert, Dna, ExternalLink, Home } from 'lucide-vue-next'

// Props
const props = defineProps({
  symbol: {
    type: String,
    required: true
  }
})

// State
const loading = ref(true)
const error = ref(null)
const gene = ref(null)
const annotations = ref(null)
const loadingEnsembl = ref(false)
const loadingUniprot = ref(false)
const activeTab = ref('gene')

// Computed
const breadcrumbs = computed(() => getGeneStructureBreadcrumbs(props.symbol))

// SEO meta tags (reactive — updates when gene data loads)
useSeoMeta({
  title: computed(() =>
    gene.value
      ? `${gene.value.approved_symbol} Gene Structure — Exon Map & Protein Domains`
      : 'Gene Structure'
  ),
  description: computed(() => {
    if (!gene.value) return 'Gene structure visualization with exon maps and protein domains.'
    const g = gene.value
    return `${g.approved_symbol} gene structure: exon map, protein domains, and ClinVar variant overlay. Interactive visualization from KGDB.`
  }),
  canonicalPath: computed(() => `/genes/${props.symbol}/structure`)
})

// Gene JSON-LD (reactive — updates when gene data loads)
useJsonLd(
  computed(() => {
    if (!gene.value) return { '@context': 'https://schema.org', '@type': 'Gene', name: 'Loading' }
    return getGeneSchema(gene.value)
  })
)

// Breadcrumb JSON-LD
useJsonLd(computed(() => getBreadcrumbSchema(breadcrumbs.value)))

const ensemblData = computed(() => {
  if (!annotations.value?.annotations?.ensembl) return null
  const ensemblAnnotations = annotations.value.annotations.ensembl
  return ensemblAnnotations.length > 0 ? ensemblAnnotations[0].data : null
})

const uniprotData = computed(() => {
  if (!annotations.value?.annotations?.uniprot) return null
  const uniprotAnnotations = annotations.value.annotations.uniprot
  return uniprotAnnotations.length > 0 ? uniprotAnnotations[0].data : null
})

const clinvarData = computed(() => {
  if (!annotations.value?.annotations?.clinvar) return null
  const clinvarAnnotations = annotations.value.annotations.clinvar
  return clinvarAnnotations.length > 0 ? clinvarAnnotations[0].data : null
})

// Methods
async function fetchGeneData() {
  try {
    loading.value = true
    error.value = null

    // Fetch gene basic info
    gene.value = await geneApi.getGene(props.symbol)

    // Fetch annotations
    await fetchAnnotations()
  } catch (e) {
    window.logService?.error('Error fetching gene data:', e)
    error.value = e.message || 'Failed to load gene data'
  } finally {
    loading.value = false
  }
}

async function fetchAnnotations() {
  if (!gene.value?.id) return

  try {
    annotations.value = await geneApi.getGeneAnnotations(gene.value.id)
  } catch (e) {
    window.logService?.warn('Error fetching annotations:', e)
    // Don't set error - annotations are optional
  }
}

async function fetchEnsemblData() {
  if (!gene.value?.id) return

  loadingEnsembl.value = true
  try {
    await fetchAnnotations()
  } finally {
    loadingEnsembl.value = false
  }
}

async function fetchUniprotData() {
  if (!gene.value?.id) return

  loadingUniprot.value = true
  try {
    await fetchAnnotations()
  } finally {
    loadingUniprot.value = false
  }
}

// Lifecycle
onMounted(() => {
  fetchGeneData()
})
</script>
