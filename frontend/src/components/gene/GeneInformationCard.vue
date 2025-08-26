<template>
  <v-card class="info-card h-100">
    <v-card-item>
      <template #prepend>
        <v-avatar color="primary" size="40">
          <v-icon icon="mdi-dna" color="white" />
        </v-avatar>
      </template>
      <v-card-title>Gene Information</v-card-title>
    </v-card-item>
    
    <v-card-text class="pb-2 pt-2">
      <v-row dense>
        <!-- Left Column: Basic Info, Constraint, Expression -->
        <v-col cols="12" md="6">
          <GeneBasicInfo :gene="gene" :hgnc-data="hgncData" />
          
          <v-divider class="my-3" />
          
          <GeneConstraints :gnomad-data="gnomadData" />
          
          <template v-if="gtexData || descartesData">
            <v-divider class="my-3" />
            <GeneExpression :gtex-data="gtexData" :descartes-data="descartesData" />
          </template>
        </v-col>

        <!-- Right Column: ClinVar, HPO, Mouse -->
        <v-col cols="12" md="6">
          <ClinVarVariants
            :clinvar-data="clinvarData"
            :gene-symbol="gene.approved_symbol"
          />
          
          <template v-if="hpoData">
            <v-divider class="my-3" />
            <GenePhenotypes :hpo-data="hpoData" />
          </template>
          
          <template v-if="mouseData">
            <v-divider class="my-3" />
            <MousePhenotypes :mouse-data="mouseData" />
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

<script setup lang="ts">
import { computed } from 'vue'
import type { Gene } from '@/types/gene'
import GeneBasicInfo from './GeneBasicInfo.vue'
import GeneConstraints from './GeneConstraints.vue'
import GeneExpression from './GeneExpression.vue'
import ClinVarVariants from './ClinVarVariants.vue'
import GenePhenotypes from './GenePhenotypes.vue'
import MousePhenotypes from './MousePhenotypes.vue'

interface Props {
  gene: Gene
  annotations?: any
  loadingAnnotations?: boolean
}

const props = defineProps<Props>()

// Extract annotation data
const hgncData = computed(() => {
  if (!props.annotations?.annotations?.hgnc?.[0]) return null
  return props.annotations.annotations.hgnc[0].data
})

const gnomadData = computed(() => {
  if (!props.annotations?.annotations?.gnomad?.[0]) return null
  return props.annotations.annotations.gnomad[0].data
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

const hasAnnotations = computed(() => {
  return !!(hgncData.value || gnomadData.value || gtexData.value || descartesData.value || clinvarData.value || hpoData.value || mouseData.value)
})
</script>