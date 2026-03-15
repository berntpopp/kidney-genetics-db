<template>
  <div>
    <!-- Loading State -->
    <div v-if="loading" class="container mx-auto px-4 py-12 text-center">
      <div
        class="h-16 w-16 animate-spin rounded-full border-4 border-primary border-t-transparent mx-auto"
      />
      <p class="text-lg mt-4 text-muted-foreground">Loading gene structure data...</p>
    </div>

    <!-- Error State -->
    <div v-else-if="error" class="container mx-auto px-4 py-6">
      <Alert variant="destructive" class="mb-4">
        <AlertTitle>Error Loading Gene Data</AlertTitle>
        <AlertDescription>{{ error }}</AlertDescription>
      </Alert>
      <Button variant="outline" as-child>
        <router-link :to="`/genes/${symbol}`">
          <ArrowLeft :size="14" class="mr-1" />
          Back to Gene Details
        </router-link>
      </Button>
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
                  <Home v-if="index === 0" class="size-4 mr-1 inline" />
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
        <!-- Page Header -->
        <div class="flex items-start justify-between mb-6">
          <div class="flex-1">
            <div class="flex items-center mb-2">
              <Button variant="ghost" size="icon" as-child class="mr-3">
                <router-link :to="`/genes/${symbol}`">
                  <ArrowLeft :size="16" />
                </router-link>
              </Button>
              <div>
                <h1 class="text-3xl font-bold">{{ gene.approved_symbol }}</h1>
                <p class="text-base text-muted-foreground">Gene Structure & Protein Domains</p>
              </div>
            </div>
          </div>
        </div>

        <!-- Gene Structure Visualization -->
        <Card class="mb-4">
          <CardHeader class="py-3">
            <div class="flex items-center justify-between">
              <CardTitle class="flex items-center text-base">
                <Dna class="size-4 mr-2" />
                Gene Structure
              </CardTitle>
              <div v-if="ensemblData" class="flex items-center gap-2 text-xs text-muted-foreground">
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
                <span class="text-muted-foreground/50">|</span>
                <a
                  :href="`https://www.ensembl.org/Homo_sapiens/Gene/Summary?g=${ensemblData.gene_id}`"
                  target="_blank"
                  rel="noopener noreferrer"
                  class="hover:underline"
                >
                  {{ ensemblData.gene_id }}
                  <ExternalLink :size="10" class="inline" />
                </a>
                <span class="text-muted-foreground/50">|</span>
                <span>
                  chr{{ ensemblData.chromosome }}:{{ ensemblData.start?.toLocaleString() }}-{{
                    ensemblData.end?.toLocaleString()
                  }}
                </span>
                <span class="text-muted-foreground/50">|</span>
                <span>{{ ensemblData.exon_count }} exons</span>
                <span class="text-muted-foreground/50">|</span>
                <span>{{ ensemblData.gene_length?.toLocaleString() }} bp</span>
              </div>
            </div>
          </CardHeader>
          <CardContent>
            <div v-if="loadingEnsembl" class="text-center py-8">
              <div
                class="h-8 w-8 animate-spin rounded-full border-2 border-primary border-t-transparent mx-auto"
              />
              <p class="text-sm mt-2 text-muted-foreground">
                Loading gene structure from Ensembl...
              </p>
            </div>
            <div v-else-if="!ensemblData" class="text-center py-8">
              <CircleAlert class="size-12 text-yellow-600 dark:text-yellow-400 mx-auto" />
              <p class="text-base mt-2 text-muted-foreground">
                Gene structure data not available from Ensembl
              </p>
              <Button variant="outline" size="sm" class="mt-2" @click="fetchEnsemblData">
                Retry
              </Button>
            </div>
            <ErrorBoundary v-else fallback-message="Gene structure visualization failed to render.">
              <GeneStructureVisualization
                :gene-symbol="gene.approved_symbol"
                :ensembl-data="ensemblData"
                :clinvar-data="clinvarData"
                :uniprot-data="uniprotData"
              />
            </ErrorBoundary>
          </CardContent>
        </Card>

        <!-- Protein Domain Visualization -->
        <Card class="mb-4">
          <CardHeader class="py-3">
            <div class="flex items-center justify-between">
              <CardTitle class="flex items-center text-base">
                <Atom class="size-4 mr-2" />
                Protein Domains
              </CardTitle>
              <div v-if="uniprotData" class="flex items-center gap-2 text-xs text-muted-foreground">
                <a
                  :href="`https://www.uniprot.org/uniprotkb/${uniprotData.accession}`"
                  target="_blank"
                  rel="noopener noreferrer"
                  class="hover:underline"
                >
                  {{ uniprotData.accession }}
                  <ExternalLink :size="10" class="inline" />
                </a>
                <span class="text-muted-foreground/50">|</span>
                <span>{{ uniprotData.entry_name }}</span>
                <span class="text-muted-foreground/50">|</span>
                <span>{{ uniprotData.length?.toLocaleString() }} aa</span>
                <span class="text-muted-foreground/50">|</span>
                <span>{{ uniprotData.domain_count }} domains</span>
                <span v-if="uniprotData.has_transmembrane" class="text-muted-foreground/50">|</span>
                <span v-if="uniprotData.has_transmembrane">TM</span>
              </div>
            </div>
          </CardHeader>
          <CardContent>
            <div v-if="loadingUniprot" class="text-center py-8">
              <div
                class="h-8 w-8 animate-spin rounded-full border-2 border-primary border-t-transparent mx-auto"
              />
              <p class="text-sm mt-2 text-muted-foreground">
                Loading protein domains from UniProt...
              </p>
            </div>
            <div v-else-if="!uniprotData" class="text-center py-8">
              <CircleAlert class="size-12 text-yellow-600 dark:text-yellow-400 mx-auto" />
              <p class="text-base mt-2 text-muted-foreground">
                Protein domain data not available from UniProt
              </p>
              <Button variant="outline" size="sm" class="mt-2" @click="fetchUniprotData">
                Retry
              </Button>
            </div>
            <ErrorBoundary v-else fallback-message="Protein domain visualization failed to render.">
              <ProteinDomainVisualization :uniprot-data="uniprotData" :clinvar-data="clinvarData" />
            </ErrorBoundary>
          </CardContent>
        </Card>

        <!-- Info cards removed — all metadata now shown inline in card headers above -->
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, computed, onMounted, onUnmounted, defineAsyncComponent } from 'vue'
import ErrorBoundary from '@/components/ui/error-boundary/ErrorBoundary.vue'
import ComponentSkeleton from '@/components/ui/ComponentSkeleton.vue'
import ComponentError from '@/components/ui/ComponentError.vue'
import { geneApi } from '@/api/genes'
import { getGeneStructureBreadcrumbs } from '@/utils/publicBreadcrumbs'
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
import { Card, CardHeader, CardTitle, CardContent } from '@/components/ui/card'
import { Alert, AlertTitle, AlertDescription } from '@/components/ui/alert'
import { Button } from '@/components/ui/button'
import {
  Breadcrumb,
  BreadcrumbItem,
  BreadcrumbLink,
  BreadcrumbList,
  BreadcrumbPage,
  BreadcrumbSeparator
} from '@/components/ui/breadcrumb'
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

// Computed
const breadcrumbs = computed(() => getGeneStructureBreadcrumbs(props.symbol))

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
    console.error('Error fetching gene data:', e)
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
    console.warn('Error fetching annotations:', e)
    // Don't set error - annotations are optional
  }
}

async function fetchEnsemblData() {
  if (!gene.value?.id) return

  loadingEnsembl.value = true
  try {
    // Refresh annotations to get Ensembl data
    await fetchAnnotations()
  } finally {
    loadingEnsembl.value = false
  }
}

async function fetchUniprotData() {
  if (!gene.value?.id) return

  loadingUniprot.value = true
  try {
    // Refresh annotations to get UniProt data
    await fetchAnnotations()
  } finally {
    loadingUniprot.value = false
  }
}

// Lifecycle
onMounted(() => {
  fetchGeneData()
})

onUnmounted(() => {
  // Clean up any D3 elements (handled by child components)
})
</script>
