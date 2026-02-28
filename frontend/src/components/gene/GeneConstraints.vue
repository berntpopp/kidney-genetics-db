<template>
  <div v-if="gnomadData">
    <div class="text-xs text-muted-foreground mb-2">Constraint Scores (gnomAD):</div>

    <div v-if="gnomadData.constraint_not_available" class="flex items-center">
      <Badge
        variant="outline"
        class="text-xs"
        :style="{ backgroundColor: '#6b728020', color: '#6b7280' }"
      >
        <Info :size="12" class="mr-1" />
        No constraint scores available
      </Badge>
    </div>

    <div v-else class="flex flex-wrap gap-2">
      <!-- pLI Score -->
      <TooltipProvider>
        <Tooltip>
          <TooltipTrigger as-child>
            <Badge
              variant="outline"
              class="cursor-help"
              :style="{
                backgroundColor: getPLIColor(gnomadData.pli) + '20',
                color: getPLIColor(gnomadData.pli),
                borderColor: getPLIColor(gnomadData.pli) + '40'
              }"
            >
              pLI: {{ formatPLI(gnomadData.pli) }}
            </Badge>
          </TooltipTrigger>
          <TooltipContent class="max-w-xs">
            <p class="font-medium text-xs">Loss-of-Function Intolerance</p>
            <p class="text-xs text-muted-foreground">Probability of LoF intolerance (pLI)</p>
            <p class="text-xs mt-1">Score: {{ gnomadData.pli?.toFixed(4) || 'N/A' }}</p>
            <p class="text-xs">{{ getPLIInterpretation(gnomadData.pli) }}</p>
          </TooltipContent>
        </Tooltip>
      </TooltipProvider>

      <!-- Missense Z-score -->
      <TooltipProvider>
        <Tooltip>
          <TooltipTrigger as-child>
            <Badge
              variant="outline"
              class="cursor-help"
              :style="{
                backgroundColor: getZScoreColor(gnomadData.mis_z) + '20',
                color: getZScoreColor(gnomadData.mis_z),
                borderColor: getZScoreColor(gnomadData.mis_z) + '40'
              }"
            >
              Mis Z: {{ formatZScore(gnomadData.mis_z) }}
            </Badge>
          </TooltipTrigger>
          <TooltipContent class="max-w-xs">
            <p class="font-medium text-xs">Missense Constraint</p>
            <p class="text-xs text-muted-foreground">Z-score for missense variants</p>
            <p class="text-xs mt-1">Score: {{ gnomadData.mis_z?.toFixed(2) || 'N/A' }}</p>
            <p class="text-xs">{{ getZScoreInterpretation(gnomadData.mis_z) }}</p>
          </TooltipContent>
        </Tooltip>
      </TooltipProvider>

      <!-- LoF Z-score -->
      <TooltipProvider v-if="gnomadData.lof_z">
        <Tooltip>
          <TooltipTrigger as-child>
            <Badge
              variant="outline"
              class="cursor-help"
              :style="{ color: '#6b7280', borderColor: '#6b728040' }"
            >
              LoF Z: {{ formatZScore(gnomadData.lof_z) }}
            </Badge>
          </TooltipTrigger>
          <TooltipContent class="max-w-xs">
            <p class="font-medium text-xs">LoF Constraint</p>
            <p class="text-xs text-muted-foreground">Z-score for loss-of-function variants</p>
            <p class="text-xs mt-1">Score: {{ gnomadData.lof_z?.toFixed(2) || 'N/A' }}</p>
            <p class="text-xs">{{ getZScoreInterpretation(gnomadData.lof_z) }}</p>
          </TooltipContent>
        </Tooltip>
      </TooltipProvider>
    </div>
  </div>
</template>

<script setup>
import { Badge } from '@/components/ui/badge'
import { Tooltip, TooltipContent, TooltipProvider, TooltipTrigger } from '@/components/ui/tooltip'
import { Info } from 'lucide-vue-next'

defineProps({
  gnomadData: {
    type: Object,
    default: null
  }
})

const getPLIColor = pli => {
  if (!pli) return '#6b7280'
  if (pli >= 0.9) return '#ef4444'
  if (pli >= 0.5) return '#f59e0b'
  return '#22c55e'
}

const getZScoreColor = zScore => {
  if (!zScore) return '#6b7280'
  if (zScore >= 3.09) return '#ef4444'
  if (zScore >= 2) return '#f59e0b'
  return '#22c55e'
}

const formatPLI = pli => {
  if (!pli) return 'N/A'
  return pli.toFixed(2)
}

const formatZScore = zScore => {
  if (!zScore) return 'N/A'
  return zScore.toFixed(2)
}

const getPLIInterpretation = pli => {
  if (!pli) return 'No data available'
  if (pli >= 0.9) return 'Highly LoF intolerant'
  if (pli >= 0.5) return 'Moderately LoF intolerant'
  return 'LoF tolerant'
}

const getZScoreInterpretation = zScore => {
  if (!zScore) return 'No data available'
  if (zScore >= 3.09) return 'Extremely intolerant (p < 0.001)'
  if (zScore >= 2) return 'Intolerant'
  if (zScore >= 0) return 'Near expectation'
  return 'More tolerant than expected'
}
</script>
