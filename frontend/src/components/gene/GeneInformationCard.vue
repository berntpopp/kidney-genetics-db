<template>
  <Card class="h-full gap-4">
    <CardHeader>
      <CardTitle tag="h2" class="text-base">Gene annotations</CardTitle>
    </CardHeader>

    <CardContent>
      <DataState
        :loading="loading"
        :error="error"
        :empty="!hasAnnotations"
        error-title="Could not load annotations"
        empty-message="No annotations for this gene yet."
        @retry="$emit('retry')"
      >
        <template #loading>
          <div class="grid grid-cols-1 gap-6 md:grid-cols-2" aria-hidden="true">
            <div v-for="col in 2" :key="col" class="space-y-5">
              <div v-for="row in 3" :key="row" class="space-y-2">
                <div class="h-3 w-32 rounded-md bg-muted motion-safe:animate-pulse" />
                <div class="flex gap-1.5">
                  <div
                    v-for="chip in 3"
                    :key="chip"
                    class="h-6 w-20 rounded-md bg-muted motion-safe:animate-pulse"
                  />
                </div>
              </div>
            </div>
          </div>
        </template>

        <div class="grid grid-cols-1 gap-x-6 gap-y-5 md:grid-cols-2">
          <div class="space-y-5">
            <GeneConstraints v-if="gnomadData" :gnomad-data="gnomadData" />
            <ClinVarVariants
              v-if="clinvarData"
              :clinvar-data="clinvarData"
              :gene-symbol="gene.approved_symbol"
            />
            <GeneExpression
              v-if="gtexData || descartesData"
              :gtex-data="gtexData"
              :descartes-data="descartesData"
            />
          </div>
          <div class="space-y-5">
            <GenePhenotypes v-if="hpoData" :hpo-data="hpoData" />
            <MousePhenotypes v-if="mouseData" :mouse-data="mouseData" />
            <ProteinInteractions v-if="stringPpiData" :string-ppi-data="stringPpiData" />
          </div>
        </div>
      </DataState>
    </CardContent>
  </Card>
</template>

<script setup>
import { computed } from 'vue'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { DataState } from '@/components/shared'
import GeneConstraints from './GeneConstraints.vue'
import GeneExpression from './GeneExpression.vue'
import ClinVarVariants from './ClinVarVariants.vue'
import GenePhenotypes from './GenePhenotypes.vue'
import MousePhenotypes from './MousePhenotypes.vue'
import ProteinInteractions from './ProteinInteractions.vue'

const props = defineProps({
  gene: { type: Object, required: true },
  annotations: { type: Object, default: null },
  loading: { type: Boolean, default: false },
  error: { type: [String, Object, Boolean], default: null }
})

defineEmits(['retry'])

const first = source => props.annotations?.annotations?.[source]?.[0]?.data ?? null

const gnomadData = computed(() => first('gnomad'))
const gtexData = computed(() => first('gtex'))
const descartesData = computed(() => first('descartes'))
const clinvarData = computed(() => first('clinvar'))
const hpoData = computed(() => first('hpo'))
const mouseData = computed(() => first('mpo_mgi'))
const stringPpiData = computed(() => first('string_ppi'))

const hasAnnotations = computed(
  () =>
    !!(
      gnomadData.value ||
      gtexData.value ||
      descartesData.value ||
      clinvarData.value ||
      hpoData.value ||
      mouseData.value ||
      stringPpiData.value
    )
)
</script>
