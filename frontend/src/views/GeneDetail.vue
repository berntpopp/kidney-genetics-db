<template>
  <div>
    <!-- Loading State -->
    <v-container v-if="loading" class="text-center py-12">
      <v-progress-circular indeterminate color="primary" size="64" />
      <p class="text-h6 mt-4 text-medium-emphasis">Loading gene information...</p>
    </v-container>

    <!-- Main Content -->
    <div v-else-if="gene">
      <!-- Breadcrumb Navigation -->
      <v-container fluid class="pa-0">
        <v-breadcrumbs :items="breadcrumbs" density="compact" class="px-6 py-2 bg-surface-light">
          <template #prepend>
            <v-icon icon="mdi-home" size="small" />
          </template>
          <template #divider>
            <v-icon icon="mdi-chevron-right" size="small" />
          </template>
        </v-breadcrumbs>
      </v-container>

      <v-container>
        <!-- Gene Header -->
        <div class="d-flex align-start justify-space-between mb-6">
          <div class="flex-grow-1">
            <div class="d-flex align-center mb-2">
              <v-btn
                icon="mdi-arrow-left"
                variant="text"
                to="/genes"
                class="mr-3"
                title="Back to gene browser"
              />
              <div>
                <h1 class="text-h3 font-weight-bold mb-1">
                  {{ gene.approved_symbol }}
                </h1>
                <p class="text-h6 text-medium-emphasis">
                  {{ gene.approved_name || 'Gene information' }}
                </p>
              </div>
            </div>
          </div>

          <!-- Action Buttons -->
          <div class="d-flex ga-2 flex-wrap">
            <v-btn prepend-icon="mdi-bookmark-outline" variant="outlined" @click="addToFavorites">
              Save
            </v-btn>
            <v-btn prepend-icon="mdi-share-variant" variant="outlined" @click="shareGene">
              Share
            </v-btn>
            <v-btn prepend-icon="mdi-download" variant="outlined" @click="exportGene">
              Export
            </v-btn>
            <v-menu>
              <template #activator="{ props }">
                <v-btn icon="mdi-dots-vertical" variant="outlined" v-bind="props" />
              </template>
              <v-list density="compact">
                <v-list-item
                  v-for="link in externalLinks"
                  :key="link.name"
                  :prepend-icon="link.icon"
                  :title="link.name"
                  :href="link.url"
                  target="_blank"
                />
              </v-list>
            </v-menu>
          </div>
        </div>

        <!-- Overview Cards -->
        <v-row class="mb-6">
          <!-- Gene Information Card -->
          <v-col cols="12" md="6" lg="4">
            <v-card height="100%" class="info-card">
              <v-card-item>
                <template #prepend>
                  <v-avatar color="primary" size="40">
                    <v-icon icon="mdi-dna" color="white" />
                  </v-avatar>
                </template>
                <v-card-title>Gene Information</v-card-title>
              </v-card-item>
              <v-card-text class="pb-2 pt-2">
                <!-- Combined Gene Info & MANE Row - Ultra Compact -->
                <div class="d-flex align-center flex-wrap ga-1 text-caption">
                  <span class="font-weight-bold text-body-2">{{ gene.approved_symbol }}</span>
                  <span class="text-medium-emphasis">•</span>
                  <span>{{ gene.hgnc_id }}</span>
                  <template v-if="hgncData?.mane_select">
                    <span class="text-medium-emphasis">•</span>
                    <v-tooltip location="bottom">
                      <template #activator="{ props }">
                        <span class="font-mono" v-bind="props" style="cursor: help">
                          {{ hgncData.mane_select.refseq_transcript_id || 'N/A' }}
                        </span>
                      </template>
                      <div class="pa-2">
                        <div class="font-weight-medium mb-1">MANE Select Transcripts</div>
                        <div class="text-caption">
                          <div v-if="hgncData.mane_select.refseq_transcript_id">
                            <span class="text-medium-emphasis">RefSeq:</span>
                            <span class="font-mono">{{
                              hgncData.mane_select.refseq_transcript_id
                            }}</span>
                          </div>
                          <div v-if="hgncData.mane_select.ensembl_transcript_id">
                            <span class="text-medium-emphasis">Ensembl:</span>
                            <span class="font-mono">{{
                              hgncData.mane_select.ensembl_transcript_id
                            }}</span>
                          </div>
                        </div>
                        <div class="text-caption mt-1 text-medium-emphasis">
                          Matched Annotation from NCBI and EMBL-EBI
                        </div>
                      </div>
                    </v-tooltip>
                  </template>
                </div>

                <v-divider class="my-1" />

                <!-- gnomAD Constraint Scores - Inline Compact -->
                <div v-if="gnomadData" class="d-flex align-center flex-wrap ga-1">
                  <span class="text-caption text-medium-emphasis mr-1">Constraint:</span>
                  <!-- pLI Score -->
                  <v-tooltip location="bottom">
                    <template #activator="{ props }">
                      <v-chip
                        :color="getPLIColor(gnomadData.pli)"
                        variant="tonal"
                        size="x-small"
                        density="compact"
                        v-bind="props"
                      >
                        pLI: {{ formatPLI(gnomadData.pli) }}
                      </v-chip>
                    </template>
                    <div class="pa-2">
                      <div class="font-weight-medium">Loss-of-Function Intolerance</div>
                      <div class="text-caption">Probability of LoF intolerance (pLI)</div>
                      <div class="text-caption mt-1">
                        Score: {{ gnomadData.pli?.toFixed(4) || 'N/A' }}
                      </div>
                      <div class="text-caption">
                        {{ getPLIInterpretation(gnomadData.pli) }}
                      </div>
                    </div>
                  </v-tooltip>

                  <!-- Missense Z-score -->
                  <v-tooltip location="bottom">
                    <template #activator="{ props }">
                      <v-chip
                        :color="getZScoreColor(gnomadData.mis_z)"
                        variant="tonal"
                        size="x-small"
                        density="compact"
                        v-bind="props"
                      >
                        Mis Z: {{ formatZScore(gnomadData.mis_z) }}
                      </v-chip>
                    </template>
                    <div class="pa-2">
                      <div class="font-weight-medium">Missense Constraint</div>
                      <div class="text-caption">Z-score for missense variants</div>
                      <div class="text-caption mt-1">
                        Score: {{ gnomadData.mis_z?.toFixed(2) || 'N/A' }}
                      </div>
                      <div class="text-caption">
                        {{ getZScoreInterpretation(gnomadData.mis_z) }}
                      </div>
                    </div>
                  </v-tooltip>

                  <!-- LoF Z-score (secondary) -->
                  <v-tooltip v-if="gnomadData.lof_z" location="bottom">
                    <template #activator="{ props }">
                      <v-chip
                        color="grey"
                        variant="outlined"
                        size="x-small"
                        density="compact"
                        v-bind="props"
                      >
                        LoF Z: {{ formatZScore(gnomadData.lof_z) }}
                      </v-chip>
                    </template>
                    <div class="pa-2">
                      <div class="font-weight-medium">LoF Constraint</div>
                      <div class="text-caption">Z-score for loss-of-function variants</div>
                      <div class="text-caption mt-1">
                        Score: {{ gnomadData.lof_z?.toFixed(2) || 'N/A' }}
                      </div>
                      <div class="text-caption">
                        {{ getZScoreInterpretation(gnomadData.lof_z) }}
                      </div>
                    </div>
                  </v-tooltip>
                </div>

                <!-- Kidney Expression Section -->
                <div v-if="gtexData || descartesData" class="mt-2">
                  <v-divider class="my-1" />
                  <div class="text-caption text-medium-emphasis mb-1">Kidney Expression:</div>

                  <!-- GTEx Expression -->
                  <div v-if="gtexData" class="d-flex align-center flex-wrap ga-1 mb-1">
                    <span class="text-caption text-medium-emphasis" style="width: 45px">GTEx:</span>
                    <!-- Kidney Cortex -->
                    <v-tooltip v-if="gtexData.tissues?.Kidney_Cortex" location="bottom">
                      <template #activator="{ props }">
                        <v-chip
                          :color="getTPMColor(gtexData.tissues.Kidney_Cortex.median_tpm)"
                          variant="tonal"
                          size="x-small"
                          density="compact"
                          v-bind="props"
                        >
                          Cortex: {{ formatTPM(gtexData.tissues.Kidney_Cortex.median_tpm) }}
                        </v-chip>
                      </template>
                      <div class="pa-2">
                        <div class="font-weight-medium">Kidney Cortex Expression</div>
                        <div class="text-caption">GTEx v8 median TPM</div>
                        <div class="text-caption mt-1">
                          Value:
                          {{ gtexData.tissues.Kidney_Cortex.median_tpm?.toFixed(2) || 'N/A' }} TPM
                        </div>
                        <div class="text-caption">
                          {{ getTPMInterpretation(gtexData.tissues.Kidney_Cortex.median_tpm) }}
                        </div>
                      </div>
                    </v-tooltip>
                    <!-- Kidney Medulla -->
                    <v-tooltip v-if="gtexData.tissues?.Kidney_Medulla" location="bottom">
                      <template #activator="{ props }">
                        <v-chip
                          :color="getTPMColor(gtexData.tissues.Kidney_Medulla.median_tpm)"
                          variant="tonal"
                          size="x-small"
                          density="compact"
                          v-bind="props"
                        >
                          Medulla: {{ formatTPM(gtexData.tissues.Kidney_Medulla.median_tpm) }}
                        </v-chip>
                      </template>
                      <div class="pa-2">
                        <div class="font-weight-medium">Kidney Medulla Expression</div>
                        <div class="text-caption">GTEx v8 median TPM</div>
                        <div class="text-caption mt-1">
                          Value:
                          {{ gtexData.tissues.Kidney_Medulla.median_tpm?.toFixed(2) || 'N/A' }} TPM
                        </div>
                        <div class="text-caption">
                          {{ getTPMInterpretation(gtexData.tissues.Kidney_Medulla.median_tpm) }}
                        </div>
                      </div>
                    </v-tooltip>
                    <!-- No GTEx data -->
                    <span
                      v-if="!gtexData.tissues?.Kidney_Cortex && !gtexData.tissues?.Kidney_Medulla"
                      class="text-caption text-medium-emphasis"
                    >
                      No data
                    </span>
                  </div>

                  <!-- Descartes Expression -->
                  <div v-if="descartesData" class="d-flex align-center flex-wrap ga-1">
                    <span class="text-caption text-medium-emphasis" style="width: 45px"
                      >scRNA:</span
                    >
                    <!-- Kidney TPM -->
                    <v-tooltip v-if="descartesData.kidney_tpm !== null" location="bottom">
                      <template #activator="{ props }">
                        <v-chip
                          :color="getTPMColor(descartesData.kidney_tpm)"
                          variant="tonal"
                          size="x-small"
                          density="compact"
                          v-bind="props"
                        >
                          TPM: {{ formatTPM(descartesData.kidney_tpm) }}
                        </v-chip>
                      </template>
                      <div class="pa-2">
                        <div class="font-weight-medium">Single-cell Kidney Expression</div>
                        <div class="text-caption">Descartes Human Cell Atlas</div>
                        <div class="text-caption mt-1">
                          TPM: {{ descartesData.kidney_tpm?.toFixed(2) || 'N/A' }}
                        </div>
                        <div v-if="descartesData.kidney_percentage" class="text-caption">
                          Cells expressing:
                          {{ (descartesData.kidney_percentage * 100)?.toFixed(2) }}%
                        </div>
                        <div class="text-caption">
                          {{ getTPMInterpretation(descartesData.kidney_tpm) }}
                        </div>
                      </div>
                    </v-tooltip>
                    <!-- Cell percentage -->
                    <v-tooltip v-if="descartesData.kidney_percentage !== null" location="bottom">
                      <template #activator="{ props }">
                        <v-chip
                          :color="getPercentageColor(descartesData.kidney_percentage)"
                          variant="outlined"
                          size="x-small"
                          density="compact"
                          v-bind="props"
                        >
                          {{ (descartesData.kidney_percentage * 100)?.toFixed(2) }}% cells
                        </v-chip>
                      </template>
                      <div class="pa-2">
                        <div class="font-weight-medium">Cell Expression Percentage</div>
                        <div class="text-caption">Descartes Human Cell Atlas</div>
                        <div class="text-caption mt-1">
                          {{ (descartesData.kidney_percentage * 100)?.toFixed(2) }}% of kidney cells
                          express this gene
                        </div>
                      </div>
                    </v-tooltip>
                    <!-- No Descartes data -->
                    <span
                      v-if="
                        descartesData.kidney_tpm === null &&
                        descartesData.kidney_percentage === null
                      "
                      class="text-caption text-medium-emphasis"
                    >
                      No data
                    </span>
                  </div>
                </div>

                <!-- Loading indicator for annotations -->
                <div v-else-if="loadingAnnotations">
                  <div
                    class="text-caption font-weight-medium mb-1 text-uppercase text-medium-emphasis"
                  >
                    Constraint
                  </div>
                  <v-skeleton-loader type="chip@2" class="d-inline-flex" />
                </div>
              </v-card-text>
            </v-card>
          </v-col>

          <!-- Evidence Score Visualization with Breakdown -->
          <v-col cols="12" md="6" lg="4">
            <ScoreBreakdown
              :score="gene.evidence_score"
              :breakdown="gene.score_breakdown"
              variant="card"
            />
          </v-col>

          <!-- Data Sources -->
          <v-col cols="12" lg="4">
            <v-card height="100%" class="sources-card">
              <v-card-item>
                <template #prepend>
                  <v-avatar color="info" size="40">
                    <v-icon icon="mdi-database" color="white" />
                  </v-avatar>
                </template>
                <v-card-title>Data Sources</v-card-title>
                <template #append>
                  <v-chip size="small" variant="tonal">
                    {{ gene.sources?.length || 0 }}
                  </v-chip>
                </template>
              </v-card-item>
              <v-card-text>
                <div v-if="gene.sources?.length" class="d-flex flex-wrap ga-2">
                  <v-chip
                    v-for="source in gene.sources"
                    :key="source"
                    :color="getSourceColor(source)"
                    variant="tonal"
                    size="small"
                  >
                    <v-icon :icon="getSourceIcon(source)" size="x-small" start />
                    {{ source }}
                  </v-chip>
                </div>
                <div v-else class="text-center py-4">
                  <v-icon icon="mdi-database-off" size="large" class="text-medium-emphasis mb-2" />
                  <p class="text-body-2 text-medium-emphasis">No source information available</p>
                </div>
              </v-card-text>
            </v-card>
          </v-col>
        </v-row>

        <!-- Evidence Details Section -->
        <div class="mb-6">
          <div class="d-flex align-center justify-space-between mb-4">
            <h2 class="text-h4 font-weight-medium">Evidence Details</h2>
            <div class="d-flex ga-2">
              <v-btn
                prepend-icon="mdi-refresh"
                variant="outlined"
                size="small"
                :loading="loadingEvidence"
                @click="refreshEvidence"
              >
                Refresh
              </v-btn>
              <v-btn
                prepend-icon="mdi-filter-variant"
                variant="outlined"
                size="small"
                @click="showEvidenceFilters = !showEvidenceFilters"
              >
                Filter
              </v-btn>
            </div>
          </div>

          <!-- Evidence Filters -->
          <v-expand-transition>
            <v-card v-if="showEvidenceFilters" class="mb-4" rounded="lg">
              <v-card-text>
                <v-row>
                  <v-col cols="12" md="4">
                    <v-select
                      v-model="selectedEvidenceSources"
                      :items="availableEvidenceSources"
                      label="Filter by Source"
                      multiple
                      chips
                      density="comfortable"
                      variant="outlined"
                    />
                  </v-col>
                  <v-col cols="12" md="4">
                    <v-select
                      v-model="evidenceSortOrder"
                      :items="evidenceSortOptions"
                      label="Sort by"
                      density="comfortable"
                      variant="outlined"
                    />
                  </v-col>
                  <v-col cols="12" md="4" class="d-flex align-center">
                    <v-btn variant="text" @click="clearEvidenceFilters"> Clear Filters </v-btn>
                  </v-col>
                </v-row>
              </v-card-text>
            </v-card>
          </v-expand-transition>

          <!-- Evidence Loading State -->
          <v-card v-if="loadingEvidence" class="text-center py-12" rounded="lg">
            <v-progress-circular indeterminate color="primary" size="48" />
            <p class="text-body-1 mt-4 text-medium-emphasis">Loading evidence data...</p>
          </v-card>

          <!-- Evidence Content -->
          <div v-else-if="filteredEvidence?.length" class="evidence-section">
            <v-expansion-panels variant="accordion" class="mb-4">
              <EvidenceCard
                v-for="(item, index) in filteredEvidence"
                :key="`${item.source_name}-${index}`"
                :evidence="item"
              />
            </v-expansion-panels>
          </div>

          <!-- No Evidence State -->
          <v-card v-else class="text-center py-12" rounded="lg">
            <v-icon icon="mdi-file-document-search" size="64" class="mb-4 text-medium-emphasis" />
            <h3 class="text-h6 mb-2">No Evidence Data</h3>
            <p class="text-body-2 text-medium-emphasis mb-4">
              {{
                selectedEvidenceSources.length > 0
                  ? 'No evidence matches your current filters'
                  : 'No evidence data available for this gene'
              }}
            </p>
            <v-btn
              v-if="selectedEvidenceSources.length > 0"
              color="primary"
              variant="outlined"
              @click="clearEvidenceFilters"
            >
              Clear Filters
            </v-btn>
          </v-card>
        </div>

        <!-- Related Genes Section -->
        <div v-if="relatedGenes?.length" class="mb-6">
          <h2 class="text-h4 font-weight-medium mb-4">Related Genes</h2>
          <v-row>
            <v-col
              v-for="relatedGene in relatedGenes.slice(0, 6)"
              :key="relatedGene.approved_symbol"
              cols="12"
              sm="6"
              md="4"
            >
              <v-card :to="`/genes/${relatedGene.approved_symbol}`" class="related-gene-card" hover>
                <v-card-text>
                  <div class="d-flex align-center justify-space-between">
                    <div>
                      <div class="text-h6 font-weight-medium">
                        {{ relatedGene.approved_symbol }}
                      </div>
                      <div class="text-body-2 text-medium-emphasis">{{ relatedGene.hgnc_id }}</div>
                    </div>
                    <v-chip
                      v-if="relatedGene.evidence_score"
                      :color="getScoreColor(relatedGene.evidence_score)"
                      size="small"
                      variant="tonal"
                    >
                      {{ relatedGene.evidence_score.toFixed(1) }}
                    </v-chip>
                  </div>
                </v-card-text>
              </v-card>
            </v-col>
          </v-row>
        </div>
      </v-container>
    </div>

    <!-- Error State -->
    <v-container v-else class="text-center py-12">
      <v-icon icon="mdi-alert-circle" size="64" color="error" class="mb-4" />
      <h2 class="text-h4 mb-2">Gene Not Found</h2>
      <p class="text-body-1 text-medium-emphasis mb-4">
        The gene "{{ $route.params.symbol }}" could not be found in our database.
      </p>
      <v-btn color="primary" to="/genes" prepend-icon="mdi-arrow-left">
        Back to Gene Browser
      </v-btn>
    </v-container>
  </div>
</template>

<script setup>
import { ref, computed, onMounted } from 'vue'
import { useRoute } from 'vue-router'
import { geneApi } from '../api/genes'
import ScoreBreakdown from '../components/ScoreBreakdown.vue'
import EvidenceCard from '../components/evidence/EvidenceCard.vue'

const route = useRoute()

// Data
const gene = ref(null)
const evidence = ref(null)
const annotations = ref(null)
const relatedGenes = ref([])
const loading = ref(true)
const loadingEvidence = ref(true)
const loadingAnnotations = ref(true)
const showEvidenceFilters = ref(false)
const selectedEvidenceSources = ref([])
const evidenceSortOrder = ref('newest')

// Filter options
const availableEvidenceSources = [
  { title: 'PanelApp', value: 'PanelApp' },
  { title: 'HPO', value: 'HPO' },
  { title: 'PubTator', value: 'PubTator' },
  { title: 'Literature', value: 'Literature' }
]

const evidenceSortOptions = [
  { title: 'Newest First', value: 'newest' },
  { title: 'Oldest First', value: 'oldest' },
  { title: 'Source Name', value: 'source' },
  { title: 'Most Panels', value: 'panels' }
]

// Computed properties
const breadcrumbs = computed(() => [
  { title: 'Home', to: '/' },
  { title: 'Gene Browser', to: '/genes' },
  { title: gene.value?.approved_symbol || 'Gene', disabled: true }
])

const gnomadData = computed(() => {
  if (!annotations.value?.annotations?.gnomad?.[0]) return null
  return annotations.value.annotations.gnomad[0].data
})

const hgncData = computed(() => {
  if (!annotations.value?.annotations?.hgnc?.[0]) return null
  return annotations.value.annotations.hgnc[0].data
})

const gtexData = computed(() => {
  if (!annotations.value?.annotations?.gtex?.[0]) return null
  return annotations.value.annotations.gtex[0].data
})

const descartesData = computed(() => {
  // Handle both array format (like gtex) and direct object format
  const descartes = annotations.value?.annotations?.descartes
  if (!descartes) return null

  // If it's an array (old format), use first element's data
  if (Array.isArray(descartes) && descartes[0]?.data) {
    return descartes[0].data
  }

  // If it's an object with data property (new format)
  if (descartes?.data) {
    return descartes.data
  }

  return null
})

const externalLinks = computed(() => {
  if (!gene.value) return []

  return [
    {
      name: 'HGNC',
      icon: 'mdi-open-in-new',
      url: `https://www.genenames.org/data/gene-symbol-report/#!/hgnc_id/${gene.value.hgnc_id.replace('HGNC:', '')}`
    },
    {
      name: 'NCBI Gene',
      icon: 'mdi-open-in-new',
      url: `https://www.ncbi.nlm.nih.gov/gene/?term=${gene.value.approved_symbol}[sym]`
    },
    {
      name: 'UniProt',
      icon: 'mdi-open-in-new',
      url: `https://www.uniprot.org/uniprot/?query=gene:${gene.value.approved_symbol}`
    },
    {
      name: 'OMIM',
      icon: 'mdi-open-in-new',
      url: `https://www.omim.org/search/?index=entry&start=1&search=${gene.value.approved_symbol}`
    }
  ]
})

const filteredEvidence = computed(() => {
  if (!evidence.value?.evidence) return []

  let filtered = evidence.value.evidence

  if (selectedEvidenceSources.value.length > 0) {
    filtered = filtered.filter(item => selectedEvidenceSources.value.includes(item.source_name))
  }

  // Sort evidence
  switch (evidenceSortOrder.value) {
    case 'oldest':
      filtered = filtered.sort(
        (a, b) =>
          new Date(a.evidence_data?.last_updated || 0) -
          new Date(b.evidence_data?.last_updated || 0)
      )
      break
    case 'source':
      filtered = filtered.sort((a, b) => a.source_name.localeCompare(b.source_name))
      break
    case 'panels':
      filtered = filtered.sort(
        (a, b) => (b.evidence_data?.panels?.length || 0) - (a.evidence_data?.panels?.length || 0)
      )
      break
    default: // newest
      filtered = filtered.sort(
        (a, b) =>
          new Date(b.evidence_data?.last_updated || 0) -
          new Date(a.evidence_data?.last_updated || 0)
      )
  }

  return filtered
})

// Methods
const getSourceColor = source => {
  const colors = {
    PanelApp: 'primary',
    HPO: 'secondary',
    PubTator: 'info',
    Literature: 'success',
    Diagnostic: 'warning'
  }
  return colors[source] || 'grey'
}

const getSourceIcon = source => {
  const icons = {
    PanelApp: 'mdi-view-dashboard',
    HPO: 'mdi-human',
    PubTator: 'mdi-file-document',
    Literature: 'mdi-book-open',
    Diagnostic: 'mdi-test-tube'
  }
  return icons[source] || 'mdi-database'
}

const getScoreColor = score => {
  if (score >= 95) return 'success'
  if (score >= 80) return 'success'
  if (score >= 70) return 'info'
  if (score >= 50) return 'warning'
  if (score >= 30) return 'orange'
  return 'error'
}

// gnomAD constraint score helpers
const formatPLI = value => {
  if (value === null || value === undefined) return 'N/A'
  // pLI is a probability (0-1), show as 1.00 if very close to 1
  if (value >= 0.9999) return '1.00'
  return value.toFixed(2)
}

const formatZScore = value => {
  if (value === null || value === undefined) return 'N/A'
  // Z-scores can be any value, just format to 2 decimals
  return value.toFixed(2)
}

const getPLIColor = pli => {
  if (!pli && pli !== 0) return 'grey'
  if (pli >= 0.9) return 'error' // Highly intolerant
  if (pli >= 0.5) return 'warning' // Moderately intolerant
  return 'success' // Tolerant
}

const getZScoreColor = zscore => {
  if (!zscore && zscore !== 0) return 'grey'
  const absZ = Math.abs(zscore)
  if (absZ >= 3.09) return 'error' // p < 0.002, highly constrained
  if (absZ >= 2) return 'warning' // p < 0.05, moderately constrained
  return 'success' // Not significantly constrained
}

const getPLIInterpretation = pli => {
  if (!pli && pli !== 0) return 'No data available'
  if (pli >= 0.9) return 'Extremely intolerant to loss-of-function'
  if (pli >= 0.5) return 'Moderately intolerant to loss-of-function'
  return 'Tolerant to loss-of-function'
}

const getZScoreInterpretation = zscore => {
  if (!zscore && zscore !== 0) return 'No data available'
  const absZ = Math.abs(zscore)
  if (absZ >= 3.09) return 'Highly constrained (p < 0.002)'
  if (absZ >= 2) return 'Moderately constrained (p < 0.05)'
  return 'Not significantly constrained'
}

// GTEx helper functions
const formatTPM = tpm => {
  if (tpm === null || tpm === undefined) return 'N/A'
  if (tpm < 1) return tpm.toFixed(2)
  if (tpm < 10) return tpm.toFixed(1)
  return Math.round(tpm).toString()
}

const getTPMColor = tpm => {
  if (!tpm && tpm !== 0) return 'grey'
  if (tpm >= 50) return 'success' // High expression
  if (tpm >= 10) return 'info' // Moderate expression
  if (tpm >= 1) return 'warning' // Low expression
  return 'grey' // Very low/no expression
}

const getTPMInterpretation = tpm => {
  if (!tpm && tpm !== 0) return 'No expression data'
  if (tpm >= 50) return 'High expression (≥50 TPM)'
  if (tpm >= 10) return 'Moderate expression (10-50 TPM)'
  if (tpm >= 1) return 'Low expression (1-10 TPM)'
  if (tpm > 0) return 'Very low expression (<1 TPM)'
  return 'No detectable expression'
}

const getPercentageColor = proportion => {
  if (!proportion && proportion !== 0) return 'grey'
  const percentage = proportion * 100
  if (percentage >= 75) return 'success' // Most cells express
  if (percentage >= 50) return 'info' // Many cells express
  if (percentage >= 25) return 'warning' // Some cells express
  if (percentage >= 10) return 'warning' // Some cells express
  return 'grey' // Few cells express
}

// Removed unused score and format functions - handled by ScoreBreakdown component

const clearEvidenceFilters = () => {
  selectedEvidenceSources.value = []
  evidenceSortOrder.value = 'newest'
}

const refreshEvidence = async () => {
  loadingEvidence.value = true
  try {
    evidence.value = await geneApi.getGeneEvidence(route.params.symbol)
  } catch (error) {
    console.error('Error refreshing evidence:', error)
  } finally {
    loadingEvidence.value = false
  }
}

const addToFavorites = () => {
  console.log('Add to favorites:', gene.value.approved_symbol)
}

const shareGene = () => {
  if (navigator.share) {
    navigator.share({
      title: `${gene.value.approved_symbol} - Kidney Genetics Database`,
      url: window.location.href
    })
  } else {
    navigator.clipboard.writeText(window.location.href)
  }
}

const exportGene = () => {
  console.log('Export gene:', gene.value.approved_symbol)
}

// Removed unused functions - will implement when needed

// Lifecycle
onMounted(async () => {
  const symbol = route.params.symbol

  try {
    gene.value = await geneApi.getGene(symbol)
  } catch (error) {
    console.error('Error loading gene:', error)
  } finally {
    loading.value = false
  }

  // Fetch annotations if we have a gene ID
  if (gene.value?.id) {
    try {
      annotations.value = await geneApi.getGeneAnnotations(gene.value.id)
    } catch (error) {
      console.error('Error loading annotations:', error)
    } finally {
      loadingAnnotations.value = false
    }
  } else {
    loadingAnnotations.value = false
  }

  try {
    evidence.value = await geneApi.getGeneEvidence(symbol)
  } catch (error) {
    console.error('Error loading evidence:', error)
  } finally {
    loadingEvidence.value = false
  }

  // Load related genes (mock for now)
  try {
    // This would be a real API call
    relatedGenes.value = []
  } catch (error) {
    console.error('Error loading related genes:', error)
  }
})
</script>

<style scoped>
.info-card,
.score-card,
.sources-card {
  transition: all 0.3s cubic-bezier(0.4, 0, 0.2, 1);
}

.info-card:hover,
.score-card:hover,
.sources-card:hover {
  transform: translateY(-2px);
}

.score-circle {
  filter: drop-shadow(0 4px 8px rgba(0, 0, 0, 0.1));
}

.evidence-panel {
  border: 1px solid rgb(var(--v-theme-surface-variant));
  margin-bottom: 8px;
  border-radius: 12px;
  overflow: hidden;
}

.evidence-panel:hover {
  border-color: rgb(var(--v-theme-primary));
}

.phenotypes-grid {
  max-height: 200px;
  overflow-y: auto;
}

.related-gene-card {
  transition: all 0.3s cubic-bezier(0.4, 0, 0.2, 1);
}

.related-gene-card:hover {
  transform: translateY(-2px);
  box-shadow: 0 8px 25px rgba(0, 0, 0, 0.1);
}

.font-mono {
  font-family: 'JetBrains Mono', 'Roboto Mono', monospace;
  font-size: 0.9em;
}

.transparent {
  background: transparent !important;
}

:deep(.v-expansion-panel-title) {
  padding: 16px 24px;
}

:deep(.v-expansion-panel-text__wrapper) {
  padding: 0 24px 16px;
}

/* Dark mode adjustments */
.v-theme--dark .evidence-panel {
  background: rgb(var(--v-theme-surface-bright));
}

.v-theme--dark .score-circle {
  filter: drop-shadow(0 4px 8px rgba(255, 255, 255, 0.1));
}
</style>
