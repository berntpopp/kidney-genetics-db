<template>
  <div v-if="hpoData">
    <div class="text-xs text-muted-foreground mb-2">Human Phenotypes (HPO):</div>

    <div
      v-if="hpoData.phenotype_count === 0 || hpoData.no_data_available"
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
      <!-- Clinical Group -->
      <TooltipProvider v-if="hpoData.classification?.clinical_group?.primary">
        <Tooltip>
          <TooltipTrigger as-child>
            <Badge
              variant="outline"
              class="cursor-help"
              :style="{
                backgroundColor:
                  getClinicalGroupColor(hpoData.classification.clinical_group.primary) + '20',
                color: getClinicalGroupColor(hpoData.classification.clinical_group.primary),
                borderColor:
                  getClinicalGroupColor(hpoData.classification.clinical_group.primary) + '40'
              }"
            >
              {{ formatClinicalGroup(hpoData.classification.clinical_group.primary) }}
            </Badge>
          </TooltipTrigger>
          <TooltipContent class="max-w-xs">
            <p class="font-medium text-xs">Clinical Classification</p>
            <p class="text-xs text-muted-foreground mb-1">
              Primary: {{ formatClinicalGroup(hpoData.classification.clinical_group.primary) }}
            </p>
            <p class="text-xs">
              Score:
              {{
                (
                  hpoData.classification.clinical_group.scores[
                    hpoData.classification.clinical_group.primary
                  ] * 100
                ).toFixed(0)
              }}%
            </p>
          </TooltipContent>
        </Tooltip>
      </TooltipProvider>

      <!-- Onset Group -->
      <TooltipProvider v-if="hpoData.classification?.onset_group?.primary">
        <Tooltip>
          <TooltipTrigger as-child>
            <Badge
              variant="outline"
              class="cursor-help"
              :style="{ color: '#6b7280', borderColor: '#6b728040' }"
            >
              {{ formatOnsetGroup(hpoData.classification.onset_group.primary) }} onset
            </Badge>
          </TooltipTrigger>
          <TooltipContent class="max-w-xs">
            <p class="font-medium text-xs">Age of Onset</p>
            <p class="text-xs text-muted-foreground">
              {{ formatOnsetGroup(hpoData.classification.onset_group.primary) }}
              ({{
                (
                  hpoData.classification.onset_group.scores[
                    hpoData.classification.onset_group.primary
                  ] * 100
                ).toFixed(0)
              }}%)
            </p>
          </TooltipContent>
        </Tooltip>
      </TooltipProvider>

      <!-- Syndromic Badge -->
      <TooltipProvider v-if="hpoData.classification?.syndromic_assessment">
        <Tooltip>
          <TooltipTrigger as-child>
            <Badge
              variant="outline"
              class="cursor-help"
              :style="{
                backgroundColor: hpoData.classification.syndromic_assessment.is_syndromic
                  ? '#f59e0b20'
                  : undefined,
                color: hpoData.classification.syndromic_assessment.is_syndromic
                  ? '#f59e0b'
                  : '#6b7280',
                borderColor: hpoData.classification.syndromic_assessment.is_syndromic
                  ? '#f59e0b40'
                  : '#6b728040'
              }"
            >
              {{
                hpoData.classification.syndromic_assessment.is_syndromic ? 'Syndromic' : 'Isolated'
              }}
            </Badge>
          </TooltipTrigger>
          <TooltipContent class="max-w-xs">
            <p class="font-medium text-xs">Presentation Type</p>
            <p class="text-xs text-muted-foreground">
              {{
                hpoData.classification.syndromic_assessment.is_syndromic
                  ? 'Syndromic kidney disease'
                  : 'Isolated kidney phenotype'
              }}
            </p>
            <p
              v-if="hpoData.classification.syndromic_assessment.extra_renal_categories?.length"
              class="text-xs mt-1"
            >
              Extra-renal:
              {{ hpoData.classification.syndromic_assessment.extra_renal_categories.join(', ') }}
            </p>
          </TooltipContent>
        </Tooltip>
      </TooltipProvider>

      <!-- Phenotype Count -->
      <TooltipProvider>
        <Tooltip>
          <TooltipTrigger as-child>
            <Badge
              variant="outline"
              class="cursor-help"
              :style="{ color: '#0ea5e9', borderColor: '#0ea5e940' }"
            >
              {{ hpoData.kidney_phenotype_count }}/{{ hpoData.phenotype_count }} kidney
            </Badge>
          </TooltipTrigger>
          <TooltipContent class="max-w-xs">
            <p class="font-medium text-xs">HPO Phenotypes</p>
            <p class="text-xs text-muted-foreground">
              {{ hpoData.kidney_phenotype_count }} kidney-related phenotypes out of
              {{ hpoData.phenotype_count }} total
            </p>
          </TooltipContent>
        </Tooltip>
      </TooltipProvider>

      <!-- Disease associations -->
      <TooltipProvider v-if="hpoData.disease_count > 0">
        <Tooltip>
          <TooltipTrigger as-child>
            <Badge
              variant="outline"
              class="cursor-help"
              :style="{ color: '#3b82f6', borderColor: '#3b82f640' }"
            >
              {{ hpoData.disease_count }} diseases
            </Badge>
          </TooltipTrigger>
          <TooltipContent class="max-w-xs">
            <p class="font-medium text-xs">Disease Associations</p>
            <p class="text-xs text-muted-foreground">
              {{ hpoData.disease_count }} disease associations in HPO
            </p>
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
  hpoData: {
    type: Object,
    default: null
  }
})

const getClinicalGroupColor = group => {
  const colors = {
    complement: '#8b5cf6',
    cakut: '#3b82f6',
    glomerulopathy: '#ef4444',
    cyst_cilio: '#14b8a6',
    tubulopathy: '#f97316',
    nephrolithiasis: '#92400e'
  }
  return colors[group] || '#6b7280'
}

const formatClinicalGroup = group => {
  const labels = {
    complement: 'Complement',
    cakut: 'CAKUT',
    glomerulopathy: 'Glomerulopathy',
    cyst_cilio: 'Cystic/Ciliopathy',
    tubulopathy: 'Tubulopathy',
    nephrolithiasis: 'Nephrolithiasis'
  }
  return labels[group] || group
}

const formatOnsetGroup = group => {
  const labels = {
    adult: 'Adult',
    pediatric: 'Pediatric',
    congenital: 'Congenital'
  }
  return labels[group] || group
}
</script>
