<template>
  <div v-if="gtexData || descartesData">
    <div class="text-xs text-muted-foreground mb-2">Kidney Expression (GTEx/scRNA):</div>

    <div v-if="hasNoData" class="flex items-center">
      <Badge
        variant="outline"
        class="text-xs"
        :style="{ backgroundColor: '#6b728020', color: '#6b7280' }"
      >
        <Info :size="12" class="mr-1" />
        No expression data available
      </Badge>
    </div>

    <div v-else class="flex items-center flex-wrap gap-2">
      <!-- GTEx Expression -->
      <template v-if="gtexData">
        <span class="text-xs text-muted-foreground">GTEx:</span>

        <!-- Kidney Cortex -->
        <TooltipProvider v-if="gtexData.tissues?.Kidney_Cortex">
          <Tooltip>
            <TooltipTrigger as-child>
              <Badge
                variant="outline"
                class="cursor-help"
                :style="{
                  backgroundColor: getTPMColor(gtexData.tissues.Kidney_Cortex.median_tpm) + '20',
                  color: getTPMColor(gtexData.tissues.Kidney_Cortex.median_tpm),
                  borderColor: getTPMColor(gtexData.tissues.Kidney_Cortex.median_tpm) + '40'
                }"
              >
                Cortex: {{ formatTPM(gtexData.tissues.Kidney_Cortex.median_tpm) }}
              </Badge>
            </TooltipTrigger>
            <TooltipContent class="max-w-xs">
              <p class="font-medium text-xs">Kidney Cortex Expression</p>
              <p class="text-xs text-muted-foreground">GTEx v8 median TPM</p>
              <p class="text-xs mt-1">
                Value: {{ gtexData.tissues.Kidney_Cortex.median_tpm?.toFixed(2) || 'N/A' }} TPM
              </p>
              <p class="text-xs">
                {{ getTPMInterpretation(gtexData.tissues.Kidney_Cortex.median_tpm) }}
              </p>
            </TooltipContent>
          </Tooltip>
        </TooltipProvider>

        <!-- Kidney Medulla -->
        <TooltipProvider v-if="gtexData.tissues?.Kidney_Medulla">
          <Tooltip>
            <TooltipTrigger as-child>
              <Badge
                variant="outline"
                class="cursor-help"
                :style="{
                  backgroundColor: getTPMColor(gtexData.tissues.Kidney_Medulla.median_tpm) + '20',
                  color: getTPMColor(gtexData.tissues.Kidney_Medulla.median_tpm),
                  borderColor: getTPMColor(gtexData.tissues.Kidney_Medulla.median_tpm) + '40'
                }"
              >
                Medulla: {{ formatTPM(gtexData.tissues.Kidney_Medulla.median_tpm) }}
              </Badge>
            </TooltipTrigger>
            <TooltipContent class="max-w-xs">
              <p class="font-medium text-xs">Kidney Medulla Expression</p>
              <p class="text-xs text-muted-foreground">GTEx v8 median TPM</p>
              <p class="text-xs mt-1">
                Value: {{ gtexData.tissues.Kidney_Medulla.median_tpm?.toFixed(2) || 'N/A' }} TPM
              </p>
              <p class="text-xs">
                {{ getTPMInterpretation(gtexData.tissues.Kidney_Medulla.median_tpm) }}
              </p>
            </TooltipContent>
          </Tooltip>
        </TooltipProvider>

        <span
          v-if="!gtexData.tissues?.Kidney_Cortex && !gtexData.tissues?.Kidney_Medulla"
          class="text-xs text-muted-foreground"
        >
          No data
        </span>
      </template>

      <!-- Descartes Expression -->
      <template v-if="descartesData">
        <span class="text-xs text-muted-foreground ml-3">scRNA:</span>

        <!-- Kidney TPM -->
        <TooltipProvider v-if="descartesData.kidney_tpm !== null">
          <Tooltip>
            <TooltipTrigger as-child>
              <Badge
                variant="outline"
                class="cursor-help"
                :style="{
                  backgroundColor: getTPMColor(descartesData.kidney_tpm) + '20',
                  color: getTPMColor(descartesData.kidney_tpm),
                  borderColor: getTPMColor(descartesData.kidney_tpm) + '40'
                }"
              >
                TPM: {{ formatTPM(descartesData.kidney_tpm) }}
              </Badge>
            </TooltipTrigger>
            <TooltipContent class="max-w-xs">
              <p class="font-medium text-xs">Single-cell Kidney Expression</p>
              <p class="text-xs text-muted-foreground">Descartes Human Cell Atlas</p>
              <p class="text-xs mt-1">TPM: {{ descartesData.kidney_tpm?.toFixed(2) || 'N/A' }}</p>
              <p v-if="descartesData.kidney_percentage" class="text-xs">
                Cells expressing: {{ (descartesData.kidney_percentage * 100)?.toFixed(2) }}%
              </p>
              <p class="text-xs">{{ getTPMInterpretation(descartesData.kidney_tpm) }}</p>
            </TooltipContent>
          </Tooltip>
        </TooltipProvider>

        <!-- Cell percentage -->
        <TooltipProvider v-if="descartesData.kidney_percentage !== null">
          <Tooltip>
            <TooltipTrigger as-child>
              <Badge
                variant="outline"
                class="cursor-help"
                :style="{
                  color: getPercentageColor(descartesData.kidney_percentage),
                  borderColor: getPercentageColor(descartesData.kidney_percentage) + '40'
                }"
              >
                {{ (descartesData.kidney_percentage * 100)?.toFixed(2) }}% cells
              </Badge>
            </TooltipTrigger>
            <TooltipContent class="max-w-xs">
              <p class="font-medium text-xs">Cell Expression Percentage</p>
              <p class="text-xs text-muted-foreground">Descartes Human Cell Atlas</p>
              <p class="text-xs mt-1">
                {{ (descartesData.kidney_percentage * 100)?.toFixed(2) }}% of kidney cells express
                this gene
              </p>
            </TooltipContent>
          </Tooltip>
        </TooltipProvider>

        <span
          v-if="descartesData.kidney_tpm === null && descartesData.kidney_percentage === null"
          class="text-xs text-muted-foreground"
        >
          No data
        </span>
      </template>
    </div>
  </div>
</template>

<script setup>
import { computed } from 'vue'
import { Badge } from '@/components/ui/badge'
import { Tooltip, TooltipContent, TooltipProvider, TooltipTrigger } from '@/components/ui/tooltip'
import { Info } from 'lucide-vue-next'

const props = defineProps({
  gtexData: {
    type: Object,
    default: null
  },
  descartesData: {
    type: Object,
    default: null
  }
})

const hasNoData = computed(() => {
  const gtexNoData =
    props.gtexData?.no_data_available ||
    (!props.gtexData?.tissues?.Kidney_Cortex && !props.gtexData?.tissues?.Kidney_Medulla)

  const descartesNoData =
    props.descartesData?.no_data_available ||
    (props.descartesData?.kidney_tpm === null && props.descartesData?.kidney_percentage === null)

  return (
    (props.gtexData && gtexNoData && !props.descartesData) ||
    (props.descartesData && descartesNoData && !props.gtexData) ||
    (props.gtexData && props.descartesData && gtexNoData && descartesNoData)
  )
})

const getTPMColor = tpm => {
  if (tpm === null || tpm === undefined) return '#6b7280'
  if (tpm >= 100) return '#22c55e'
  if (tpm >= 10) return '#3b82f6'
  if (tpm >= 1) return '#f59e0b'
  return '#9ca3af'
}

const getPercentageColor = percentage => {
  if (!percentage) return '#6b7280'
  if (percentage >= 0.5) return '#22c55e'
  if (percentage >= 0.1) return '#3b82f6'
  if (percentage >= 0.01) return '#f59e0b'
  return '#9ca3af'
}

const formatTPM = tpm => {
  if (tpm === null || tpm === undefined) return 'N/A'
  if (tpm < 0.01) return '<0.01'
  if (tpm < 1) return tpm.toFixed(2)
  if (tpm < 100) return tpm.toFixed(1)
  return Math.round(tpm).toString()
}

const getTPMInterpretation = tpm => {
  if (tpm === null || tpm === undefined) return 'No expression data'
  if (tpm >= 100) return 'Very high expression'
  if (tpm >= 10) return 'Moderate expression'
  if (tpm >= 1) return 'Low expression'
  if (tpm > 0) return 'Very low expression'
  return 'Not expressed'
}
</script>
