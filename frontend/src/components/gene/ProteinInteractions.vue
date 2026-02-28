<template>
  <div v-if="stringPpiData" class="protein-interactions">
    <div class="text-caption text-medium-emphasis mb-2">Protein Interactions (STRING):</div>

    <!-- Show special message if no interactions available -->
    <div
      v-if="stringPpiData.ppi_degree === 0 || stringPpiData.no_data_available"
      class="d-flex align-center"
    >
      <v-chip color="grey" variant="tonal" size="small">
        <Info class="size-3 mr-1" />
        No interactions available
      </v-chip>
    </div>

    <div v-else class="d-flex align-center flex-wrap ga-2">
      <!-- PPI Score chip -->
      <v-tooltip location="bottom">
        <template #activator="{ props: tooltipProps }">
          <v-chip color="primary" variant="tonal" size="small" v-bind="tooltipProps">
            Score: {{ stringPpiData.ppi_score?.toFixed(1) || '0' }}
          </v-chip>
        </template>
        <div class="pa-2">
          <div class="font-weight-medium">
            PPI Score: {{ stringPpiData.ppi_score?.toFixed(1) || '0' }}
          </div>
          <div class="text-caption">Weighted protein interaction score (0-100 scale)</div>
          <div class="text-caption mt-1">
            <strong>Percentile Rank:</strong>
            {{
              stringPpiData.ppi_percentile
                ? `${(stringPpiData.ppi_percentile * 100).toFixed(0)}th percentile`
                : 'N/A'
            }}
          </div>
          <div class="text-caption mt-2">
            <strong>Calculation:</strong><br />
            Σ(STRING/1000 × partner_evidence) / √degree
          </div>
          <div class="text-caption mt-2 text-warning">
            <strong>Note:</strong> This is NOT a percentage. It's a normalized score based on
            interaction confidence and partner relevance.
          </div>
        </div>
      </v-tooltip>

      <!-- Percentile Rank chip (separate for clarity) -->
      <v-tooltip v-if="stringPpiData.ppi_percentile" location="bottom">
        <template #activator="{ props: tooltipProps }">
          <v-chip color="info" variant="outlined" size="small" v-bind="tooltipProps">
            <ChartSpline class="size-3 mr-1" />
            {{ (stringPpiData.ppi_percentile * 100).toFixed(0) }}<sup>th</sup> percentile
          </v-chip>
        </template>
        <div class="pa-2">
          <div class="font-weight-medium">Percentile Rank</div>
          <div class="text-caption">
            This gene's PPI score ranks higher than
            {{ (stringPpiData.ppi_percentile * 100).toFixed(0) }}% of all kidney genes
          </div>
          <div class="text-caption mt-1">
            Higher percentile = stronger protein interactions relative to other genes
          </div>
        </div>
      </v-tooltip>

      <!-- Network degree chip -->
      <v-tooltip location="bottom">
        <template #activator="{ props: tooltipProps }">
          <v-chip color="secondary" variant="outlined" size="small" v-bind="tooltipProps">
            {{ stringPpiData.ppi_degree }} partners
          </v-chip>
        </template>
        <div class="pa-2">
          <div class="font-weight-medium">Network Degree</div>
          <div class="text-caption">Number of kidney gene interaction partners</div>
        </div>
      </v-tooltip>

      <!-- Top partners display -->
      <span v-if="topPartners.length > 0" class="text-body-2 ml-2">
        <span class="text-medium-emphasis">Top:</span>
        <span v-for="(partner, index) in topPartners.slice(0, 3)" :key="partner.partner_symbol">
          <v-tooltip location="bottom">
            <template #activator="{ props: tooltipProps }">
              <span v-bind="tooltipProps" class="partner-name">
                {{ partner.partner_symbol }}
              </span>
            </template>
            <div class="pa-2">
              <div class="font-weight-medium">{{ partner.partner_symbol }}</div>
              <div class="text-caption">
                STRING: {{ partner.string_score }}/1000<br />
                Evidence: {{ partner.partner_evidence }}/100<br />
                Weighted: {{ partner.weighted_score.toFixed(1) }}
              </div>
            </div>
          </v-tooltip>
          <span v-if="index < Math.min(2, topPartners.length - 1)" class="text-medium-emphasis"
            >,
          </span>
        </span>
        <span v-if="topPartners.length > 3" class="text-medium-emphasis">
          +{{ topPartners.length - 3 }}
        </span>
      </span>
    </div>
  </div>
</template>

<script setup>
import { computed } from 'vue'
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

<style scoped>
.protein-interactions {
  padding: 0;
}

.partner-name {
  font-weight: 500;
  color: rgb(var(--v-theme-primary));
  cursor: help;
}

.partner-name:hover {
  text-decoration: underline;
}
</style>
