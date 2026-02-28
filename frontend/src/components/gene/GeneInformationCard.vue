<template>
  <Card class="h-full">
    <CardHeader class="flex flex-row items-center gap-3 pb-2">
      <div class="flex h-10 w-10 items-center justify-center rounded-full bg-primary/10">
        <Dna :size="20" class="text-primary" />
      </div>
      <div class="flex-1">
        <CardTitle class="flex items-center flex-wrap text-base">
          <span>Gene Information</span>
          <span class="ml-3 text-sm font-normal text-muted-foreground">
            {{ gene.approved_symbol }} &bull; {{ gene.hgnc_id }}
            <template v-if="hgncData?.mane_select?.refseq_transcript_id">
              &bull; {{ hgncData.mane_select.refseq_transcript_id }}
            </template>
          </span>
        </CardTitle>
      </div>
      <Button variant="outline" size="sm" as="a" :href="`/genes/${gene.approved_symbol}/structure`">
        <Database :size="14" class="mr-1" />
        Structure
      </Button>
    </CardHeader>

    <CardContent class="pt-2 pb-2">
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
        class="flex items-center justify-center"
        style="min-height: 200px"
      >
        <div class="text-center">
          <Database :size="56" class="mx-auto text-muted-foreground mb-3" />
          <div class="text-base font-medium">No Additional Annotations</div>
          <div class="text-xs text-muted-foreground mt-1">
            Additional annotations will appear here when available
          </div>
        </div>
      </div>

      <!-- Otherwise show normal two-column layout -->
      <div v-else class="grid grid-cols-1 md:grid-cols-2 gap-4">
        <!-- Left Column: Gene Identity & Clinical Data -->
        <div class="space-y-4">
          <GeneConstraints
            v-if="gnomadData || gnomadNoData"
            :gnomad-data="gnomadData || gnomadNoData"
          />

          <template v-if="clinvarData">
            <Separator />
            <ClinVarVariants :clinvar-data="clinvarData" :gene-symbol="gene.approved_symbol" />
          </template>

          <template v-if="gtexData || descartesData">
            <Separator />
            <GeneExpression :gtex-data="gtexData" :descartes-data="descartesData" />
          </template>
        </div>

        <!-- Right Column: Phenotypes & Molecular Interactions -->
        <div class="space-y-4">
          <GenePhenotypes v-if="hpoData" :hpo-data="hpoData" />

          <template v-if="mouseData">
            <Separator v-if="hpoData" />
            <MousePhenotypes :mouse-data="mouseData" />
          </template>

          <template v-if="stringPpiData">
            <Separator v-if="hpoData || mouseData" />
            <ProteinInteractions :string-ppi-data="stringPpiData" />
          </template>
        </div>
      </div>

      <!-- Loading indicator for annotations -->
      <div v-if="loadingAnnotations && !hasAnnotations" class="text-center py-4">
        <div
          class="h-8 w-8 mx-auto animate-spin rounded-full border-2 border-primary border-t-transparent"
        />
        <div class="text-xs text-muted-foreground mt-2">Loading annotations...</div>
      </div>
    </CardContent>
  </Card>
</template>

<script setup>
import { computed } from 'vue'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { Button } from '@/components/ui/button'
import { Separator } from '@/components/ui/separator'
import { Dna, Database } from 'lucide-vue-next'
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
  if (data?.constraint_not_available) return null
  return data
})

const gnomadNoData = computed(() => {
  if (!props.annotations?.annotations?.gnomad?.[0]) return null
  const data = props.annotations.annotations.gnomad[0].data
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
