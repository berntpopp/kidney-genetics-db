<template>
  <div>
    <!-- Loading State -->
    <v-container v-if="loading" class="text-center py-12">
      <v-progress-circular indeterminate color="primary" size="64" />
      <p class="text-h6 mt-4 text-medium-emphasis">Loading gene structure data...</p>
    </v-container>

    <!-- Error State -->
    <v-container v-else-if="error">
      <v-alert type="error" variant="tonal" class="mb-4">
        <template #title>Error Loading Gene Data</template>
        {{ error }}
      </v-alert>
      <v-btn variant="outlined" prepend-icon="mdi-arrow-left" :to="`/genes/${symbol}`">
        Back to Gene Details
      </v-btn>
    </v-container>

    <!-- Main Content -->
    <div v-else-if="gene">
      <!-- Breadcrumb Navigation -->
      <v-container fluid class="pa-0">
        <v-breadcrumbs :items="breadcrumbs" density="compact" class="px-6 py-2 bg-surface-light">
          <template #prepend>
            <Home class="size-4" />
          </template>
          <template #divider>
            <ChevronRight class="size-4" />
          </template>
        </v-breadcrumbs>
      </v-container>

      <v-container>
        <!-- Page Header -->
        <div class="d-flex align-start justify-space-between mb-6">
          <div class="flex-grow-1">
            <div class="d-flex align-center mb-2">
              <v-btn
                icon="mdi-arrow-left"
                variant="text"
                size="small"
                :to="`/genes/${symbol}`"
                class="mr-3"
              />
              <div>
                <h1 class="text-h3 font-weight-bold">{{ gene.approved_symbol }}</h1>
                <p class="text-body-1 text-medium-emphasis">Gene Structure & Protein Domains</p>
              </div>
            </div>
          </div>
        </div>

        <!-- Gene Structure Visualization -->
        <v-card class="mb-6">
          <v-card-title class="d-flex align-center">
            <Dna class="size-5 mr-2" />
            Gene Structure
          </v-card-title>
          <v-card-subtitle v-if="ensemblData">
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
              class="text-medium-emphasis"
            >
              ({{ ensemblData.canonical_transcript?.transcript_id }})
            </span>
          </v-card-subtitle>
          <v-card-text>
            <div v-if="loadingEnsembl" class="text-center py-8">
              <v-progress-circular indeterminate color="primary" size="32" />
              <p class="text-body-2 mt-2 text-medium-emphasis">
                Loading gene structure from Ensembl...
              </p>
            </div>
            <div v-else-if="!ensemblData" class="text-center py-8">
              <CircleAlert class="size-12 text-yellow-600 dark:text-yellow-400" />
              <p class="text-body-1 mt-2 text-medium-emphasis">
                Gene structure data not available from Ensembl
              </p>
              <v-btn
                variant="tonal"
                color="primary"
                size="small"
                class="mt-2"
                @click="fetchEnsemblData"
              >
                Retry
              </v-btn>
            </div>
            <GeneStructureVisualization
              v-else
              :gene-symbol="gene.approved_symbol"
              :ensembl-data="ensemblData"
              :clinvar-data="clinvarData"
              :uniprot-data="uniprotData"
            />
          </v-card-text>
        </v-card>

        <!-- Protein Domain Visualization -->
        <v-card class="mb-6">
          <v-card-title class="d-flex align-center">
            <Atom class="size-5 mr-2" />
            Protein Domains
          </v-card-title>
          <v-card-subtitle v-if="uniprotData">
            {{ uniprotData.accession }} - {{ uniprotData.entry_name }}
          </v-card-subtitle>
          <v-card-text>
            <div v-if="loadingUniprot" class="text-center py-8">
              <v-progress-circular indeterminate color="primary" size="32" />
              <p class="text-body-2 mt-2 text-medium-emphasis">
                Loading protein domains from UniProt...
              </p>
            </div>
            <div v-else-if="!uniprotData" class="text-center py-8">
              <CircleAlert class="size-12 text-yellow-600 dark:text-yellow-400" />
              <p class="text-body-1 mt-2 text-medium-emphasis">
                Protein domain data not available from UniProt
              </p>
              <v-btn
                variant="tonal"
                color="primary"
                size="small"
                class="mt-2"
                @click="fetchUniprotData"
              >
                Retry
              </v-btn>
            </div>
            <ProteinDomainVisualization
              v-else
              :uniprot-data="uniprotData"
              :clinvar-data="clinvarData"
            />
          </v-card-text>
        </v-card>

        <!-- Additional Information Cards -->
        <v-row>
          <!-- Ensembl Details -->
          <v-col cols="12" md="6">
            <v-card v-if="ensemblData">
              <v-card-title>
                <Info class="size-5 mr-2" />
                Gene Information
              </v-card-title>
              <v-card-text>
                <v-list density="compact">
                  <v-list-item v-if="ensemblData.canonical_transcript?.refseq_transcript_id">
                    <template #prepend>
                      <IdCard class="size-4" />
                    </template>
                    <v-list-item-title>RefSeq Transcript</v-list-item-title>
                    <v-list-item-subtitle>
                      <a
                        :href="`https://www.ncbi.nlm.nih.gov/nuccore/${ensemblData.canonical_transcript.refseq_transcript_id}`"
                        target="_blank"
                        rel="noopener noreferrer"
                      >
                        {{ ensemblData.canonical_transcript.refseq_transcript_id }}
                        <ExternalLink class="size-3" />
                      </a>
                    </v-list-item-subtitle>
                  </v-list-item>
                  <v-list-item>
                    <template #prepend>
                      <IdCard class="size-4" />
                    </template>
                    <v-list-item-title>Ensembl Gene ID</v-list-item-title>
                    <v-list-item-subtitle>
                      <a
                        :href="`https://www.ensembl.org/Homo_sapiens/Gene/Summary?g=${ensemblData.gene_id}`"
                        target="_blank"
                        rel="noopener noreferrer"
                      >
                        {{ ensemblData.gene_id }}
                        <ExternalLink class="size-3" />
                      </a>
                    </v-list-item-subtitle>
                  </v-list-item>
                  <v-list-item v-if="ensemblData.canonical_transcript?.transcript_id">
                    <template #prepend>
                      <Dna class="size-4" />
                    </template>
                    <v-list-item-title>Ensembl Transcript</v-list-item-title>
                    <v-list-item-subtitle>
                      <a
                        :href="`https://www.ensembl.org/Homo_sapiens/Transcript/Summary?t=${ensemblData.canonical_transcript.transcript_id}`"
                        target="_blank"
                        rel="noopener noreferrer"
                      >
                        {{ ensemblData.canonical_transcript.transcript_id }}
                        <ExternalLink class="size-3" />
                      </a>
                    </v-list-item-subtitle>
                  </v-list-item>
                  <v-list-item>
                    <template #prepend>
                      <MapPin class="size-4" />
                    </template>
                    <v-list-item-title>Location</v-list-item-title>
                    <v-list-item-subtitle>
                      chr{{ ensemblData.chromosome }}:{{ ensemblData.start?.toLocaleString() }}-{{
                        ensemblData.end?.toLocaleString()
                      }}
                      ({{ ensemblData.strand }})
                    </v-list-item-subtitle>
                  </v-list-item>
                  <v-list-item>
                    <template #prepend>
                      <Ruler class="size-4" />
                    </template>
                    <v-list-item-title>Gene Length</v-list-item-title>
                    <v-list-item-subtitle>
                      {{ ensemblData.gene_length?.toLocaleString() }} bp
                    </v-list-item-subtitle>
                  </v-list-item>
                  <v-list-item>
                    <template #prepend>
                      <Hash class="size-4" />
                    </template>
                    <v-list-item-title>Exons</v-list-item-title>
                    <v-list-item-subtitle>
                      {{ ensemblData.exon_count }} exons in canonical transcript
                    </v-list-item-subtitle>
                  </v-list-item>
                </v-list>
              </v-card-text>
            </v-card>
          </v-col>

          <!-- UniProt Details -->
          <v-col cols="12" md="6">
            <v-card v-if="uniprotData">
              <v-card-title>
                <Dna class="size-5 mr-2" />
                Protein Information
              </v-card-title>
              <v-card-text>
                <v-list density="compact">
                  <v-list-item>
                    <template #prepend>
                      <IdCard class="size-4" />
                    </template>
                    <v-list-item-title>UniProt Accession</v-list-item-title>
                    <v-list-item-subtitle>
                      <a
                        :href="`https://www.uniprot.org/uniprotkb/${uniprotData.accession}`"
                        target="_blank"
                        rel="noopener noreferrer"
                      >
                        {{ uniprotData.accession }}
                        <ExternalLink class="size-3" />
                      </a>
                    </v-list-item-subtitle>
                  </v-list-item>
                  <v-list-item>
                    <template #prepend>
                      <Ruler class="size-4" />
                    </template>
                    <v-list-item-title>Protein Length</v-list-item-title>
                    <v-list-item-subtitle>
                      {{ uniprotData.length?.toLocaleString() }} amino acids
                    </v-list-item-subtitle>
                  </v-list-item>
                  <v-list-item>
                    <template #prepend>
                      <Shapes class="size-4" />
                    </template>
                    <v-list-item-title>Domains</v-list-item-title>
                    <v-list-item-subtitle>
                      {{ uniprotData.domain_count }} annotated domains
                    </v-list-item-subtitle>
                  </v-list-item>
                  <v-list-item v-if="uniprotData.has_transmembrane">
                    <template #prepend>
                      <Network class="size-4" />
                    </template>
                    <v-list-item-title>Transmembrane</v-list-item-title>
                    <v-list-item-subtitle>Contains transmembrane domains</v-list-item-subtitle>
                  </v-list-item>
                </v-list>
              </v-card-text>
            </v-card>
          </v-col>
        </v-row>
      </v-container>
    </div>
  </div>
</template>

<script setup>
import { ref, computed, onMounted, onUnmounted } from 'vue'
import { geneApi } from '@/api/genes'
import { getGeneStructureBreadcrumbs } from '@/utils/publicBreadcrumbs'
import GeneStructureVisualization from '@/components/visualizations/GeneStructureVisualization.vue'
import ProteinDomainVisualization from '@/components/visualizations/ProteinDomainVisualization.vue'
import {
  Atom,
  ChevronRight,
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
  Shapes
} from 'lucide-vue-next'

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

<style scoped>
.bg-surface-light {
  background-color: rgb(var(--v-theme-surface-light));
}

a {
  color: inherit;
  text-decoration: none;
}

a:hover {
  text-decoration: underline;
}
</style>
