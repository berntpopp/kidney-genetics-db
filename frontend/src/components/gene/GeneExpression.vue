<template>
  <div v-if="gtexData || descartesData" class="gene-expression">
    <div class="text-caption text-medium-emphasis mb-2">Kidney Expression:</div>

    <div class="d-flex align-center flex-wrap ga-2">
      <!-- GTEx Expression -->
      <template v-if="gtexData">
        <span class="text-caption text-medium-emphasis">GTEx:</span>

        <!-- Kidney Cortex -->
        <v-tooltip v-if="gtexData.tissues?.Kidney_Cortex" location="bottom">
          <template #activator="{ props: tooltipProps }">
            <v-chip
              :color="getTPMColor(gtexData.tissues.Kidney_Cortex.median_tpm)"
              variant="tonal"
              size="small"
              v-bind="tooltipProps"
            >
              Cortex: {{ formatTPM(gtexData.tissues.Kidney_Cortex.median_tpm) }}
            </v-chip>
          </template>
          <div class="pa-2">
            <div class="font-weight-medium">Kidney Cortex Expression</div>
            <div class="text-caption">GTEx v8 median TPM</div>
            <div class="text-caption mt-1">
              Value: {{ gtexData.tissues.Kidney_Cortex.median_tpm?.toFixed(2) || 'N/A' }} TPM
            </div>
            <div class="text-caption">
              {{ getTPMInterpretation(gtexData.tissues.Kidney_Cortex.median_tpm) }}
            </div>
          </div>
        </v-tooltip>

        <!-- Kidney Medulla -->
        <v-tooltip v-if="gtexData.tissues?.Kidney_Medulla" location="bottom">
          <template #activator="{ props: tooltipProps }">
            <v-chip
              :color="getTPMColor(gtexData.tissues.Kidney_Medulla.median_tpm)"
              variant="tonal"
              size="small"
              v-bind="tooltipProps"
            >
              Medulla: {{ formatTPM(gtexData.tissues.Kidney_Medulla.median_tpm) }}
            </v-chip>
          </template>
          <div class="pa-2">
            <div class="font-weight-medium">Kidney Medulla Expression</div>
            <div class="text-caption">GTEx v8 median TPM</div>
            <div class="text-caption mt-1">
              Value: {{ gtexData.tissues.Kidney_Medulla.median_tpm?.toFixed(2) || 'N/A' }} TPM
            </div>
            <div class="text-caption">
              {{ getTPMInterpretation(gtexData.tissues.Kidney_Medulla.median_tpm) }}
            </div>
          </div>
        </v-tooltip>

        <!-- No GTEx data -->
        <span
          v-if="!gtexData.tissues?.Kidney_Cortex && !gtexData.tissues?.Kidney_Medulla"
          class="text-caption text-medium-emphasis"
        >
          No data
        </span>
      </template>

      <!-- Descartes Expression -->
      <template v-if="descartesData">
        <span class="text-caption text-medium-emphasis ml-3">scRNA:</span>

        <!-- Kidney TPM -->
        <v-tooltip v-if="descartesData.kidney_tpm !== null" location="bottom">
          <template #activator="{ props: tooltipProps }">
            <v-chip
              :color="getTPMColor(descartesData.kidney_tpm)"
              variant="tonal"
              size="small"
              v-bind="tooltipProps"
            >
              TPM: {{ formatTPM(descartesData.kidney_tpm) }}
            </v-chip>
          </template>
          <div class="pa-2">
            <div class="font-weight-medium">Single-cell Kidney Expression</div>
            <div class="text-caption">Descartes Human Cell Atlas</div>
            <div class="text-caption mt-1">
              TPM: {{ descartesData.kidney_tpm?.toFixed(2) || 'N/A' }}
            </div>
            <div v-if="descartesData.kidney_percentage" class="text-caption">
              Cells expressing: {{ (descartesData.kidney_percentage * 100)?.toFixed(2) }}%
            </div>
            <div class="text-caption">{{ getTPMInterpretation(descartesData.kidney_tpm) }}</div>
          </div>
        </v-tooltip>

        <!-- Cell percentage -->
        <v-tooltip v-if="descartesData.kidney_percentage !== null" location="bottom">
          <template #activator="{ props: tooltipProps }">
            <v-chip
              :color="getPercentageColor(descartesData.kidney_percentage)"
              variant="outlined"
              size="small"
              v-bind="tooltipProps"
            >
              {{ (descartesData.kidney_percentage * 100)?.toFixed(2) }}% cells
            </v-chip>
          </template>
          <div class="pa-2">
            <div class="font-weight-medium">Cell Expression Percentage</div>
            <div class="text-caption">Descartes Human Cell Atlas</div>
            <div class="text-caption mt-1">
              {{ (descartesData.kidney_percentage * 100)?.toFixed(2) }}% of kidney cells express
              this gene
            </div>
          </div>
        </v-tooltip>

        <!-- No Descartes data -->
        <span
          v-if="descartesData.kidney_tpm === null && descartesData.kidney_percentage === null"
          class="text-caption text-medium-emphasis"
        >
          No data
        </span>
      </template>
    </div>
  </div>
</template>

<script setup>
defineProps({
  gtexData: {
    type: Object,
    default: null
  },
  descartesData: {
    type: Object,
    default: null
  }
})

// Color functions
const getTPMColor = tpm => {
  if (tpm === null || tpm === undefined) return 'grey'
  if (tpm >= 100) return 'success' // High expression
  if (tpm >= 10) return 'info' // Moderate expression
  if (tpm >= 1) return 'warning' // Low expression
  return 'grey-lighten-1' // Very low expression
}

const getPercentageColor = percentage => {
  if (!percentage) return 'grey'
  if (percentage >= 0.5) return 'success' // >50% of cells
  if (percentage >= 0.1) return 'info' // 10-50% of cells
  if (percentage >= 0.01) return 'warning' // 1-10% of cells
  return 'grey-lighten-1' // <1% of cells
}

// Formatting functions
const formatTPM = tpm => {
  if (tpm === null || tpm === undefined) return 'N/A'
  if (tpm < 0.01) return '<0.01'
  if (tpm < 1) return tpm.toFixed(2)
  if (tpm < 100) return tpm.toFixed(1)
  return Math.round(tpm).toString()
}

// Interpretation function
const getTPMInterpretation = tpm => {
  if (tpm === null || tpm === undefined) return 'No expression data'
  if (tpm >= 100) return 'Very high expression'
  if (tpm >= 10) return 'Moderate expression'
  if (tpm >= 1) return 'Low expression'
  if (tpm > 0) return 'Very low expression'
  return 'Not expressed'
}
</script>
