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
        <Card class="mb-6">
          <CardHeader>
            <CardTitle class="flex items-center">
              <Dna class="size-5 mr-2" />
              Gene Structure
            </CardTitle>
            <CardDescription v-if="ensemblData">
              {{
                ensemblData.canonical_transcript?.refseq_transcript_id ||
                ensemblData.canonical_transcript?.transcript_id ||
                'Canonical transcript'
              }}
              <span
                v-if="
                  ensemblData.canonical_transcript?.refseq_transcript_id &&
                  ensemblData.canonical_transcript?.transcript_id
                "
                class="text-muted-foreground"
              >
                ({{ ensemblData.canonical_transcript?.transcript_id }})
              </span>
            </CardDescription>
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
            <GeneStructureVisualization
              v-else
              :gene-symbol="gene.approved_symbol"
              :ensembl-data="ensemblData"
              :clinvar-data="clinvarData"
              :uniprot-data="uniprotData"
            />
          </CardContent>
        </Card>

        <!-- Protein Domain Visualization -->
        <Card class="mb-6">
          <CardHeader>
            <CardTitle class="flex items-center">
              <Atom class="size-5 mr-2" />
              Protein Domains
            </CardTitle>
            <CardDescription v-if="uniprotData">
              {{ uniprotData.accession }} - {{ uniprotData.entry_name }}
            </CardDescription>
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
            <ProteinDomainVisualization
              v-else
              :uniprot-data="uniprotData"
              :clinvar-data="clinvarData"
            />
          </CardContent>
        </Card>

        <!-- Additional Information Cards -->
        <div class="grid grid-cols-1 md:grid-cols-2 gap-6">
          <!-- Ensembl Details -->
          <Card v-if="ensemblData">
            <CardHeader>
              <CardTitle class="flex items-center">
                <Info class="size-5 mr-2" />
                Gene Information
              </CardTitle>
            </CardHeader>
            <CardContent>
              <div class="space-y-3">
                <div
                  v-if="ensemblData.canonical_transcript?.refseq_transcript_id"
                  class="flex items-center gap-3"
                >
                  <IdCard :size="16" class="text-muted-foreground shrink-0" />
                  <div>
                    <div class="text-xs text-muted-foreground">RefSeq Transcript</div>
                    <a
                      :href="`https://www.ncbi.nlm.nih.gov/nuccore/${ensemblData.canonical_transcript.refseq_transcript_id}`"
                      target="_blank"
                      rel="noopener noreferrer"
                      class="text-sm hover:underline"
                    >
                      {{ ensemblData.canonical_transcript.refseq_transcript_id }}
                      <ExternalLink :size="12" class="inline ml-1" />
                    </a>
                  </div>
                </div>
                <div class="flex items-center gap-3">
                  <IdCard :size="16" class="text-muted-foreground shrink-0" />
                  <div>
                    <div class="text-xs text-muted-foreground">Ensembl Gene ID</div>
                    <a
                      :href="`https://www.ensembl.org/Homo_sapiens/Gene/Summary?g=${ensemblData.gene_id}`"
                      target="_blank"
                      rel="noopener noreferrer"
                      class="text-sm hover:underline"
                    >
                      {{ ensemblData.gene_id }}
                      <ExternalLink :size="12" class="inline ml-1" />
                    </a>
                  </div>
                </div>
                <div
                  v-if="ensemblData.canonical_transcript?.transcript_id"
                  class="flex items-center gap-3"
                >
                  <Dna :size="16" class="text-muted-foreground shrink-0" />
                  <div>
                    <div class="text-xs text-muted-foreground">Ensembl Transcript</div>
                    <a
                      :href="`https://www.ensembl.org/Homo_sapiens/Transcript/Summary?t=${ensemblData.canonical_transcript.transcript_id}`"
                      target="_blank"
                      rel="noopener noreferrer"
                      class="text-sm hover:underline"
                    >
                      {{ ensemblData.canonical_transcript.transcript_id }}
                      <ExternalLink :size="12" class="inline ml-1" />
                    </a>
                  </div>
                </div>
                <div class="flex items-center gap-3">
                  <MapPin :size="16" class="text-muted-foreground shrink-0" />
                  <div>
                    <div class="text-xs text-muted-foreground">Location</div>
                    <div class="text-sm">
                      chr{{ ensemblData.chromosome }}:{{
                        ensemblData.start?.toLocaleString()
                      }}-{{ ensemblData.end?.toLocaleString() }}
                      ({{ ensemblData.strand }})
                    </div>
                  </div>
                </div>
                <div class="flex items-center gap-3">
                  <Ruler :size="16" class="text-muted-foreground shrink-0" />
                  <div>
                    <div class="text-xs text-muted-foreground">Gene Length</div>
                    <div class="text-sm">{{ ensemblData.gene_length?.toLocaleString() }} bp</div>
                  </div>
                </div>
                <div class="flex items-center gap-3">
                  <Hash :size="16" class="text-muted-foreground shrink-0" />
                  <div>
                    <div class="text-xs text-muted-foreground">Exons</div>
                    <div class="text-sm">
                      {{ ensemblData.exon_count }} exons in canonical transcript
                    </div>
                  </div>
                </div>
              </div>
            </CardContent>
          </Card>

          <!-- UniProt Details -->
          <Card v-if="uniprotData">
            <CardHeader>
              <CardTitle class="flex items-center">
                <Dna class="size-5 mr-2" />
                Protein Information
              </CardTitle>
            </CardHeader>
            <CardContent>
              <div class="space-y-3">
                <div class="flex items-center gap-3">
                  <IdCard :size="16" class="text-muted-foreground shrink-0" />
                  <div>
                    <div class="text-xs text-muted-foreground">UniProt Accession</div>
                    <a
                      :href="`https://www.uniprot.org/uniprotkb/${uniprotData.accession}`"
                      target="_blank"
                      rel="noopener noreferrer"
                      class="text-sm hover:underline"
                    >
                      {{ uniprotData.accession }}
                      <ExternalLink :size="12" class="inline ml-1" />
                    </a>
                  </div>
                </div>
                <div class="flex items-center gap-3">
                  <Ruler :size="16" class="text-muted-foreground shrink-0" />
                  <div>
                    <div class="text-xs text-muted-foreground">Protein Length</div>
                    <div class="text-sm">
                      {{ uniprotData.length?.toLocaleString() }} amino acids
                    </div>
                  </div>
                </div>
                <div class="flex items-center gap-3">
                  <Shapes :size="16" class="text-muted-foreground shrink-0" />
                  <div>
                    <div class="text-xs text-muted-foreground">Domains</div>
                    <div class="text-sm">{{ uniprotData.domain_count }} annotated domains</div>
                  </div>
                </div>
                <div v-if="uniprotData.has_transmembrane" class="flex items-center gap-3">
                  <Network :size="16" class="text-muted-foreground shrink-0" />
                  <div>
                    <div class="text-xs text-muted-foreground">Transmembrane</div>
                    <div class="text-sm">Contains transmembrane domains</div>
                  </div>
                </div>
              </div>
            </CardContent>
          </Card>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, computed, onMounted, onUnmounted } from 'vue'
import { geneApi } from '@/api/genes'
import { getGeneStructureBreadcrumbs } from '@/utils/publicBreadcrumbs'
import GeneStructureVisualization from '@/components/visualizations/GeneStructureVisualization.vue'
import ProteinDomainVisualization from '@/components/visualizations/ProteinDomainVisualization.vue'
import { Card, CardHeader, CardTitle, CardDescription, CardContent } from '@/components/ui/card'
import { Alert, AlertTitle, AlertDescription } from '@/components/ui/alert'
import { Button } from '@/components/ui/button'
import {
  Breadcrumb,
  BreadcrumbItem,
  BreadcrumbLink,
  BreadcrumbList,
  BreadcrumbPage,
  BreadcrumbSeparator,
} from '@/components/ui/breadcrumb'
import {
  ArrowLeft,
  Atom,
  CircleAlert,
  Dna,
  ExternalLink,
  Hash,
  Home,
  IdCard,
  Info,
  MapPin,
  Network,
  Ruler,
  Shapes,
} from 'lucide-vue-next'

// Props
const props = defineProps({
  symbol: {
    type: String,
    required: true,
  },
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
