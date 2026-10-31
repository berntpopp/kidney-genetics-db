<template>
  <div v-if="stringPpiData">
    <h3 class="mb-2 text-xs font-medium text-muted-foreground">Protein interactions (STRING)</h3>

    <p
      v-if="stringPpiData.ppi_degree === 0 || stringPpiData.no_data_available"
      class="text-sm text-muted-foreground"
    >
      No interactions with other kidney genes.
    </p>

    <div v-else class="flex flex-wrap items-center gap-1.5">
      <Chip
        kind="neutral"
        class="tabular-nums"
        :label="`PPI score ${stringPpiData.ppi_score?.toFixed(1) ?? '0'}`"
        tooltip="Weighted protein interaction score: Σ(STRING score/1000 × partner evidence score) / √partners. Not a percentage."
      />
      <Chip
        v-if="stringPpiData.ppi_percentile"
        kind="neutral"
        class="tabular-nums"
        :label="`${percentile}th percentile`"
        :tooltip="`The PPI score ranks higher than ${percentile}% of kidney genes`"
      />
      <Chip
        kind="neutral"
        class="tabular-nums"
        :label="`${stringPpiData.ppi_degree} kidney-gene ${stringPpiData.ppi_degree === 1 ? 'partner' : 'partners'}`"
        tooltip="Number of interaction partners among the kidney genes"
      />
      <span v-if="topPartners.length" class="text-sm">
        <span class="text-muted-foreground">Top partners: </span>
        <template v-for="(partner, index) in topPartners" :key="partner.partner_symbol">
          <Tooltip>
            <TooltipTrigger as-child>
              <RouterLink
                :to="`/genes/${partner.partner_symbol}`"
                class="rounded-sm font-medium text-primary underline-offset-4 hover:underline focus-visible:ring-2 focus-visible:ring-ring focus-visible:outline-none"
                >{{ partner.partner_symbol }}</RouterLink
              >
            </TooltipTrigger>
            <TooltipContent>
              STRING {{ partner.string_score }}/1000 · partner evidence
              {{ partner.partner_evidence }}/100 · weighted {{ partner.weighted_score?.toFixed(1) }}
            </TooltipContent>
          </Tooltip>
          <span v-if="index < topPartners.length - 1" class="text-muted-foreground">, </span>
        </template>
        <span v-if="moreCount" class="text-muted-foreground"> and {{ moreCount }} more</span>
      </span>
    </div>
  </div>
</template>

<script setup>
import { computed } from 'vue'
import { RouterLink } from 'vue-router'
import { Chip } from '@/components/shared'
import { Tooltip, TooltipContent, TooltipTrigger } from '@/components/ui/tooltip'

const props = defineProps({
  stringPpiData: { type: Object, default: null },
  version: { type: String, default: '12.0' }
})

const percentile = computed(() => ((props.stringPpiData?.ppi_percentile ?? 0) * 100).toFixed(0))
const partners = computed(() => props.stringPpiData?.interactions ?? [])
const topPartners = computed(() => partners.value.slice(0, 3))
const moreCount = computed(() => Math.max(0, partners.value.length - 3))
</script>
