<template>
  <div v-if="clinvarData" class="clinvar-variants">
    <div class="text-caption text-medium-emphasis mb-2">Clinical Variants (ClinVar):</div>

    <!-- Show special message if no variants available -->
    <div
      v-if="clinvarData.total_variants === 0 || clinvarData.no_data_available"
      class="d-flex align-center"
    >
      <v-chip color="grey" variant="tonal" size="small">
        <v-icon size="x-small" start>mdi-information-outline</v-icon>
        No variants available
      </v-chip>
    </div>

    <div v-else class="d-flex align-center flex-wrap ga-2">
      <!-- Total variants chip -->
      <v-tooltip location="bottom" max-width="350">
        <template #activator="{ props }">
          <v-chip color="primary" variant="tonal" size="small" v-bind="props">
            {{ clinvarData.total_variants }} total
          </v-chip>
        </template>
        <div class="pa-2">
          <div class="font-weight-medium">Total ClinVar Variants</div>
          <div class="text-caption">All variants submitted to ClinVar for {{ geneSymbol }}</div>

          <v-divider class="my-2"></v-divider>

          <div class="text-caption">
            <div class="font-weight-medium mb-1">Review Confidence:</div>
            <div class="d-flex align-center">
              <v-icon size="x-small" class="mr-1" color="success">mdi-shield-check</v-icon>
              <span class="font-weight-medium">{{ clinvarData.high_confidence_percentage }}%</span>
              <span class="ml-1">with high-quality review</span>
            </div>
            <div class="text-caption mt-1 text-medium-emphasis" style="font-size: 0.7rem;">
              ({{ clinvarData.high_confidence_count || Math.round(clinvarData.total_variants * clinvarData.high_confidence_percentage / 100) }} of {{ clinvarData.total_variants }} variants)
            </div>
            <div class="text-caption mt-2 text-medium-emphasis" style="font-size: 0.7rem;">
              High-quality = Expert panel reviewed or<br>
              multiple submitters with no conflicts
            </div>
          </div>
        </div>
      </v-tooltip>

      <!-- Pathogenic/Likely pathogenic chip -->
      <v-tooltip
        v-if="clinvarData.pathogenic_count + clinvarData.likely_pathogenic_count > 0"
        location="bottom"
      >
        <template #activator="{ props }">
          <v-chip color="error" variant="tonal" size="small" v-bind="props">
            {{ clinvarData.pathogenic_count + clinvarData.likely_pathogenic_count }} P/LP
          </v-chip>
        </template>
        <div class="pa-2">
          <div class="font-weight-medium">Pathogenic Variants</div>
          <div class="text-caption">
            <div>Pathogenic: {{ clinvarData.pathogenic_count }}</div>
            <div>Likely pathogenic: {{ clinvarData.likely_pathogenic_count }}</div>
            <div class="mt-1 text-medium-emphasis">
              {{ clinvarData.pathogenic_percentage }}% of all variants
            </div>
          </div>
        </div>
      </v-tooltip>

      <!-- VUS chip -->
      <v-tooltip v-if="clinvarData.vus_count > 0" location="bottom">
        <template #activator="{ props }">
          <v-chip color="warning" variant="tonal" size="small" v-bind="props">
            {{ clinvarData.vus_count }} VUS
          </v-chip>
        </template>
        <div class="pa-2">
          <div class="font-weight-medium">Uncertain Significance</div>
          <div class="text-caption">
            Variants of uncertain significance requiring further evidence
          </div>
        </div>
      </v-tooltip>

      <!-- Benign/Likely benign chip -->
      <v-tooltip
        v-if="clinvarData.benign_count + clinvarData.likely_benign_count > 0"
        location="bottom"
      >
        <template #activator="{ props }">
          <v-chip color="success" variant="outlined" size="small" v-bind="props">
            {{ clinvarData.benign_count + clinvarData.likely_benign_count }} B/LB
          </v-chip>
        </template>
        <div class="pa-2">
          <div class="font-weight-medium">Benign Variants</div>
          <div class="text-caption">
            <div>Benign: {{ clinvarData.benign_count }}</div>
            <div>Likely benign: {{ clinvarData.likely_benign_count }}</div>
          </div>
        </div>
      </v-tooltip>
    </div>
  </div>
</template>

<script setup>
defineProps({
  clinvarData: {
    type: Object,
    default: null
  },
  geneSymbol: {
    type: String,
    required: true
  }
})
</script>
