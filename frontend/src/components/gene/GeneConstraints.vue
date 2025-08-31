<template>
  <div v-if="gnomadData" class="gene-constraints">
    <div class="text-caption text-medium-emphasis mb-2">Constraint Scores (gnomAD):</div>

    <!-- Show special message if constraint data is not available -->
    <div v-if="gnomadData.constraint_not_available" class="d-flex align-center">
      <v-chip color="grey" variant="tonal" size="small">
        <v-icon size="x-small" start>mdi-information-outline</v-icon>
        No constraint scores available
      </v-chip>
    </div>

    <!-- Show constraint scores if available -->
    <div v-else class="d-flex flex-wrap ga-2">
      <!-- pLI Score -->
      <v-tooltip location="bottom">
        <template #activator="{ props }">
          <v-chip :color="getPLIColor(gnomadData.pli)" variant="tonal" size="small" v-bind="props">
            pLI: {{ formatPLI(gnomadData.pli) }}
          </v-chip>
        </template>
        <div class="pa-2">
          <div class="font-weight-medium">Loss-of-Function Intolerance</div>
          <div class="text-caption">Probability of LoF intolerance (pLI)</div>
          <div class="text-caption mt-1">Score: {{ gnomadData.pli?.toFixed(4) || 'N/A' }}</div>
          <div class="text-caption">{{ getPLIInterpretation(gnomadData.pli) }}</div>
        </div>
      </v-tooltip>

      <!-- Missense Z-score -->
      <v-tooltip location="bottom">
        <template #activator="{ props }">
          <v-chip
            :color="getZScoreColor(gnomadData.mis_z)"
            variant="tonal"
            size="small"
            v-bind="props"
          >
            Mis Z: {{ formatZScore(gnomadData.mis_z) }}
          </v-chip>
        </template>
        <div class="pa-2">
          <div class="font-weight-medium">Missense Constraint</div>
          <div class="text-caption">Z-score for missense variants</div>
          <div class="text-caption mt-1">Score: {{ gnomadData.mis_z?.toFixed(2) || 'N/A' }}</div>
          <div class="text-caption">{{ getZScoreInterpretation(gnomadData.mis_z) }}</div>
        </div>
      </v-tooltip>

      <!-- LoF Z-score (secondary) -->
      <v-tooltip v-if="gnomadData.lof_z" location="bottom">
        <template #activator="{ props }">
          <v-chip color="grey" variant="outlined" size="small" v-bind="props">
            LoF Z: {{ formatZScore(gnomadData.lof_z) }}
          </v-chip>
        </template>
        <div class="pa-2">
          <div class="font-weight-medium">LoF Constraint</div>
          <div class="text-caption">Z-score for loss-of-function variants</div>
          <div class="text-caption mt-1">Score: {{ gnomadData.lof_z?.toFixed(2) || 'N/A' }}</div>
          <div class="text-caption">{{ getZScoreInterpretation(gnomadData.lof_z) }}</div>
        </div>
      </v-tooltip>
    </div>
  </div>
</template>

<script setup>
defineProps({
  gnomadData: {
    type: Object,
    default: null
  }
})

// gnomAD constraint score colors
const getPLIColor = pli => {
  if (!pli) return 'grey'
  if (pli >= 0.9) return 'error' // High intolerance
  if (pli >= 0.5) return 'warning' // Moderate intolerance
  return 'success' // Low intolerance
}

const getZScoreColor = zScore => {
  if (!zScore) return 'grey'
  if (zScore >= 3.09) return 'error' // Very intolerant (p < 0.001)
  if (zScore >= 2) return 'warning' // Intolerant
  return 'success' // Tolerant
}

// Formatting functions
const formatPLI = pli => {
  if (!pli) return 'N/A'
  return pli.toFixed(2)
}

const formatZScore = zScore => {
  if (!zScore) return 'N/A'
  return zScore.toFixed(2)
}

// Interpretation functions
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
