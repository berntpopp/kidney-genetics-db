<template>
  <div v-if="mouseData">
    <div class="text-xs text-muted-foreground mb-2">Mouse Phenotypes (MGI/MPO):</div>

    <div
      v-if="mouseData.phenotype_count === 0 || mouseData.no_data_available"
      class="flex items-center"
    >
      <Badge
        variant="outline"
        class="text-xs"
        :style="{ backgroundColor: '#6b728020', color: '#6b7280' }"
      >
        <Info :size="12" class="mr-1" />
        No phenotypes available
      </Badge>
    </div>

    <div v-else class="flex items-center flex-wrap gap-2">
      <!-- Phenotype count -->
      <TooltipProvider>
        <Tooltip>
          <TooltipTrigger as-child>
            <Badge
              variant="outline"
              class="cursor-help"
              :style="{
                color: getPhenotypeCountColor(mouseData.phenotype_count),
                borderColor: getPhenotypeCountColor(mouseData.phenotype_count) + '40'
              }"
            >
              {{ mouseData.phenotype_count }} phenotypes
            </Badge>
          </TooltipTrigger>
          <TooltipContent class="max-w-xs">
            <p class="font-medium text-xs">Kidney-Related Phenotypes</p>
            <p class="text-xs text-muted-foreground mb-2">
              {{ mouseData.phenotype_count }} phenotypes found in mouse models
            </p>
            <div v-if="mouseData.phenotypes?.length" class="text-xs">
              <p class="font-medium mb-1">Sample phenotypes:</p>
              <div
                v-for="phenotype in mouseData.phenotypes.slice(0, 5)"
                :key="phenotype.term"
                class="mb-1"
              >
                <span class="font-mono">{{ phenotype.term }}</span
                >: {{ phenotype.name }}
              </div>
              <p v-if="mouseData.phenotype_count > 5" class="text-muted-foreground">
                +{{ mouseData.phenotype_count - 5 }} more phenotypes
              </p>
            </div>
          </TooltipContent>
        </Tooltip>
      </TooltipProvider>

      <!-- Zygosity breakdown -->
      <TooltipProvider v-if="mouseData.zygosity_analysis?.homozygous?.phenotype_count > 0">
        <Tooltip>
          <TooltipTrigger as-child>
            <Badge
              variant="outline"
              class="cursor-help"
              :style="{ color: '#ef4444', borderColor: '#ef444440' }"
            >
              {{ mouseData.zygosity_analysis.homozygous.phenotype_count }} hm
            </Badge>
          </TooltipTrigger>
          <TooltipContent>
            <p class="font-medium text-xs">Homozygous Knockout</p>
            <p class="text-xs text-muted-foreground">
              {{ mouseData.zygosity_analysis.homozygous.phenotype_count }} kidney phenotypes
            </p>
          </TooltipContent>
        </Tooltip>
      </TooltipProvider>

      <TooltipProvider v-if="mouseData.zygosity_analysis?.heterozygous?.phenotype_count > 0">
        <Tooltip>
          <TooltipTrigger as-child>
            <Badge
              variant="outline"
              class="cursor-help"
              :style="{ color: '#f59e0b', borderColor: '#f59e0b40' }"
            >
              {{ mouseData.zygosity_analysis.heterozygous.phenotype_count }} ht
            </Badge>
          </TooltipTrigger>
          <TooltipContent>
            <p class="font-medium text-xs">Heterozygous Knockout</p>
            <p class="text-xs text-muted-foreground">
              {{ mouseData.zygosity_analysis.heterozygous.phenotype_count }} kidney phenotypes
            </p>
          </TooltipContent>
        </Tooltip>
      </TooltipProvider>

      <TooltipProvider v-if="mouseData.zygosity_analysis?.conditional?.phenotype_count > 0">
        <Tooltip>
          <TooltipTrigger as-child>
            <Badge
              variant="outline"
              class="cursor-help"
              :style="{ color: '#3b82f6', borderColor: '#3b82f640' }"
            >
              {{ mouseData.zygosity_analysis.conditional.phenotype_count }} cn
            </Badge>
          </TooltipTrigger>
          <TooltipContent>
            <p class="font-medium text-xs">Conditional Knockout</p>
            <p class="text-xs text-muted-foreground">
              {{ mouseData.zygosity_analysis.conditional.phenotype_count }} kidney phenotypes
            </p>
          </TooltipContent>
        </Tooltip>
      </TooltipProvider>
    </div>

    <!-- System analysis -->
    <div
      v-if="mouseData.system_analysis?.renal_urinary"
      class="flex items-center flex-wrap gap-2 mt-2"
    >
      <Badge variant="outline" :style="{ color: '#8b5cf6', borderColor: '#8b5cf640' }">
        Renal: {{ mouseData.system_analysis.renal_urinary.phenotype_count }} phenotypes
      </Badge>
    </div>
  </div>
</template>

<script setup>
import { Badge } from '@/components/ui/badge'
import { Tooltip, TooltipContent, TooltipProvider, TooltipTrigger } from '@/components/ui/tooltip'
import { Info } from 'lucide-vue-next'

defineProps({
  mouseData: {
    type: Object,
    default: null
  }
})

const getPhenotypeCountColor = count => {
  if (!count || count === 0) return '#6b7280'
  if (count >= 20) return '#ef4444'
  if (count >= 10) return '#f59e0b'
  if (count >= 5) return '#3b82f6'
  return '#22c55e'
}
</script>
