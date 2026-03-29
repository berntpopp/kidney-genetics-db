<template>
  <div v-if="stringPpiData">
    <div class="text-xs text-muted-foreground mb-2">Protein Interactions (STRING):</div>

    <div
      v-if="stringPpiData.ppi_degree === 0 || stringPpiData.no_data_available"
      class="flex items-center"
    >
      <Badge
        variant="outline"
        class="text-xs"
        :style="{ backgroundColor: '#6b728020', color: '#6b7280' }"
      >
        <Info :size="12" class="mr-1" />
        No interactions available
      </Badge>
    </div>

    <div v-else class="flex items-center flex-wrap gap-2">
      <!-- PPI Score -->
      <HoverPopover content-class="w-auto p-2 max-w-xs">
        <Badge
          variant="outline"
          class="cursor-pointer"
          :style="{ backgroundColor: '#0ea5e920', color: '#0ea5e9', borderColor: '#0ea5e940' }"
        >
          Score: {{ stringPpiData.ppi_score?.toFixed(1) || '0' }}
        </Badge>
        <template #content>
          <p class="font-medium text-xs">
            PPI Score: {{ stringPpiData.ppi_score?.toFixed(1) || '0' }}
          </p>
          <p class="text-xs text-muted-foreground">
            Weighted protein interaction score (0-100 scale)
          </p>
          <p class="text-xs mt-1">
            <strong>Percentile Rank:</strong>
            {{
              stringPpiData.ppi_percentile
                ? `${(stringPpiData.ppi_percentile * 100).toFixed(0)}th percentile`
                : 'N/A'
            }}
          </p>
          <p class="text-xs mt-2">
            <strong>Calculation:</strong><br />
            &Sigma;(STRING/1000 &times; partner_evidence) / &radic;degree
          </p>
          <p class="text-xs mt-2 text-yellow-600 dark:text-yellow-400">
            <strong>Note:</strong> This is NOT a percentage. It's a normalized score based on
            interaction confidence and partner relevance.
          </p>
        </template>
      </HoverPopover>

      <!-- Percentile Rank -->
      <HoverPopover v-if="stringPpiData.ppi_percentile" content-class="w-auto p-2 max-w-xs">
        <Badge
          variant="outline"
          class="cursor-pointer"
          :style="{ color: '#3b82f6', borderColor: '#3b82f640' }"
        >
          <ChartSpline :size="12" class="mr-1" />
          {{ (stringPpiData.ppi_percentile * 100).toFixed(0) }}<sup>th</sup> percentile
        </Badge>
        <template #content>
          <p class="font-medium text-xs">Percentile Rank</p>
          <p class="text-xs text-muted-foreground">
            This gene's PPI score ranks higher than
            {{ (stringPpiData.ppi_percentile * 100).toFixed(0) }}% of all kidney genes
          </p>
          <p class="text-xs mt-1 text-muted-foreground">
            Higher percentile = stronger protein interactions relative to other genes
          </p>
        </template>
      </HoverPopover>

      <!-- Network degree -->
      <HoverPopover content-class="w-auto p-2">
        <Badge
          variant="outline"
          class="cursor-pointer"
          :style="{ color: '#6b7280', borderColor: '#6b728040' }"
        >
          {{ stringPpiData.ppi_degree }} partners
        </Badge>
        <template #content>
          <p class="font-medium text-xs">Network Degree</p>
          <p class="text-xs text-muted-foreground">Number of kidney gene interaction partners</p>
        </template>
      </HoverPopover>

      <!-- Top partners -->
      <span v-if="topPartners.length > 0" class="text-sm ml-2">
        <span class="text-muted-foreground">Top:</span>
        <span v-for="(partner, index) in topPartners.slice(0, 3)" :key="partner.partner_symbol">
          <HoverPopover content-class="w-auto p-2 max-w-xs">
            <span class="font-medium text-primary cursor-pointer hover:underline">
              {{ partner.partner_symbol }}
            </span>
            <template #content>
              <p class="font-medium text-xs">{{ partner.partner_symbol }}</p>
              <div class="text-xs text-muted-foreground">
                STRING: {{ partner.string_score }}/1000<br />
                Evidence: {{ partner.partner_evidence }}/100<br />
                Weighted: {{ partner.weighted_score.toFixed(1) }}
              </div>
            </template>
          </HoverPopover>
          <span v-if="index < Math.min(2, topPartners.length - 1)" class="text-muted-foreground"
            >,
          </span>
        </span>
        <span v-if="topPartners.length > 3" class="text-muted-foreground">
          +{{ topPartners.length - 3 }}
        </span>
      </span>
    </div>
  </div>
</template>

<script setup>
import { computed } from 'vue'
import { Badge } from '@/components/ui/badge'
import HoverPopover from '@/components/ui/HoverPopover.vue'
import { Info, ChartSpline } from 'lucide-vue-next'

const props = defineProps({
  stringPpiData: {
    type: Object,
    default: null
  },
  version: {
    type: String,
    default: '12.0'
  }
})

const topPartners = computed(() => {
  if (!props.stringPpiData?.interactions) return []
  return props.stringPpiData.interactions
})
</script>
