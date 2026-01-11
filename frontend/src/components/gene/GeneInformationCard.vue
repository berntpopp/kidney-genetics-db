<template>
  <v-card class="info-card h-100">
    <v-card-item>
      <template #prepend>
        <v-avatar color="primary" size="40">
          <v-icon icon="mdi-dna" color="white" />
        </v-avatar>
      </template>
      <v-card-title class="d-flex align-center flex-wrap">
        <span>Gene Information</span>
        <span class="ml-3 text-body-1 font-weight-normal">
          {{ gene.approved_symbol }} • {{ gene.hgnc_id }}
          <template v-if="hgncData?.mane_select?.refseq_transcript_id">
            • {{ hgncData.mane_select.refseq_transcript_id }}
          </template>
        </span>
      </v-card-title>
      <template #append>
        <v-btn
          variant="tonal"
          size="small"
          color="primary"
          prepend-icon="mdi-dna"
          :to="`/genes/${gene.approved_symbol}/structure`"
        >
          Structure
        </v-btn>
      </template>
    </v-card-item>

    <v-card-text class="pb-2 pt-2">
      <!-- If no annotations at all, show centered message -->
      <div
        v-if="
          !gnomadData &&
          !clinvarData &&
          !gtexData &&
          !descartesData &&
          !hpoData &&
          !mouseData &&
          !stringPpiData
        "
        class="d-flex align-center justify-center"
        style="min-height: 200px"
      >
        <div class="text-center">
          <v-icon icon="mdi-database-off-outline" size="56" color="grey-lighten-1" class="mb-3" />
          <div class="text-body-1 font-weight-medium">No Additional Annotations</div>
          <div class="text-caption text-medium-emphasis mt-1">
            Additional annotations will appear here when available
          </div>
        </div>
      </div>

      <!-- Otherwise show normal two-column layout -->
      <v-row v-else dense>
        <!-- Left Column: Gene Identity & Clinical Data -->
        <v-col cols="12" md="6">
          <!-- Genomic Constraint -->
          <GeneConstraints
            v-if="gnomadData || gnomadNoData"
            :gnomad-data="gnomadData || gnomadNoData"
          />

          <!-- Clinical Variants -->
          <template v-if="clinvarData">
            <v-divider class="my-3" />
            <ClinVarVariants :clinvar-data="clinvarData" :gene-symbol="gene.approved_symbol" />
          </template>

          <!-- Expression Data -->
          <template v-if="gtexData || descartesData">
            <v-divider class="my-3" />
            <GeneExpression :gtex-data="gtexData" :descartes-data="descartesData" />
          </template>
        </v-col>

        <!-- Right Column: Phenotypes & Molecular Interactions -->
        <v-col cols="12" md="6">
          <!-- Human Phenotypes -->
          <template v-if="hpoData">
            <GenePhenotypes :hpo-data="hpoData" />
          </template>

          <!-- Mouse Phenotypes -->
          <template v-if="mouseData">
            <v-divider v-if="hpoData" class="my-3" />
            <template v-else><div style="margin-top: -3px"></div></template>
            <MousePhenotypes :mouse-data="mouseData" />
          </template>

          <!-- Protein Interactions -->
          <template v-if="stringPpiData">
            <v-divider v-if="hpoData || mouseData" class="my-3" />
            <template v-else><div style="margin-top: -3px"></div></template>
            <ProteinInteractions :string-ppi-data="stringPpiData" />
          </template>
        </v-col>
      </v-row>

      <!-- Loading indicator for annotations -->
      <div v-if="loadingAnnotations && !hasAnnotations" class="text-center py-4">
        <v-progress-circular indeterminate color="primary" size="32" />
        <div class="text-caption text-medium-emphasis mt-2">Loading annotations...</div>
      </div>
    </v-card-text>
  </v-card>
</template>

<script setup>
import { computed } from 'vue'
import GeneConstraints from './GeneConstraints.vue'
import GeneExpression from './GeneExpression.vue'
import ClinVarVariants from './ClinVarVariants.vue'
import GenePhenotypes from './GenePhenotypes.vue'
import MousePhenotypes from './MousePhenotypes.vue'
import ProteinInteractions from './ProteinInteractions.vue'

const props = defineProps({
  gene: {
    type: Object,
    required: true
  },
  annotations: {
    type: Object,
    default: null
  },
  loadingAnnotations: {
    type: Boolean,
    default: false
  }
})

// Extract annotation data
const hgncData = computed(() => {
  if (!props.annotations?.annotations?.hgnc?.[0]) return null
  return props.annotations.annotations.hgnc[0].data
})

const gnomadData = computed(() => {
  if (!props.annotations?.annotations?.gnomad?.[0]) return null
  const data = props.annotations.annotations.gnomad[0].data
  // Don't return data if it's a "no constraint available" response
  if (data?.constraint_not_available) return null
  return data
})

const gnomadNoData = computed(() => {
  if (!props.annotations?.annotations?.gnomad?.[0]) return null
  const data = props.annotations.annotations.gnomad[0].data
  // Only return if this is a "no constraint available" response
  if (data?.constraint_not_available) return data
  return null
})

const gtexData = computed(() => {
  if (!props.annotations?.annotations?.gtex?.[0]) return null
  return props.annotations.annotations.gtex[0].data
})

const descartesData = computed(() => {
  if (!props.annotations?.annotations?.descartes?.[0]) return null
  return props.annotations.annotations.descartes[0].data
})

const clinvarData = computed(() => {
  if (!props.annotations?.annotations?.clinvar?.[0]) return null
  return props.annotations.annotations.clinvar[0].data
})

const hpoData = computed(() => {
  if (!props.annotations?.annotations?.hpo?.[0]) return null
  return props.annotations.annotations.hpo[0].data
})

const mouseData = computed(() => {
  if (!props.annotations?.annotations?.mpo_mgi?.[0]) return null
  return props.annotations.annotations.mpo_mgi[0].data
})

const stringPpiData = computed(() => {
  if (!props.annotations?.annotations?.string_ppi?.[0]) return null
  return props.annotations.annotations.string_ppi[0].data
})

const hasAnnotations = computed(() => {
  return !!(
    hgncData.value ||
    gnomadData.value ||
    gtexData.value ||
    descartesData.value ||
    clinvarData.value ||
    hpoData.value ||
    mouseData.value ||
    stringPpiData.value
  )
})
</script>
