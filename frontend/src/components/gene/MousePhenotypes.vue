<template>
  <div v-if="mouseData" class="mouse-phenotypes">
    <div class="text-caption text-medium-emphasis mb-2">Mouse Phenotypes (MGI/MPO):</div>

    <div class="d-flex align-center flex-wrap ga-2 mb-2">
      <!-- Phenotype count with color coding -->
      <v-tooltip location="bottom">
        <template #activator="{ props }">
          <v-chip
            :color="getPhenotypeCountColor(mouseData.phenotype_count)"
            variant="outlined"
            size="small"
            v-bind="props"
          >
            {{ mouseData.phenotype_count }} phenotypes
          </v-chip>
        </template>
        <div class="pa-2 max-width-300">
          <div class="font-weight-medium">Kidney-Related Phenotypes</div>
          <div class="text-caption mb-2">
            {{ mouseData.phenotype_count }} phenotypes found in mouse models
          </div>
          <div v-if="mouseData.phenotypes?.length" class="text-caption">
            <div class="font-weight-medium mb-1">Sample phenotypes:</div>
            <div
              v-for="phenotype in mouseData.phenotypes.slice(0, 5)"
              :key="phenotype.term"
              class="mb-1"
            >
              <span class="font-mono">{{ phenotype.term }}</span
              >: {{ phenotype.name }}
            </div>
            <div v-if="mouseData.phenotype_count > 5" class="text-medium-emphasis">
              +{{ mouseData.phenotype_count - 5 }} more phenotypes
            </div>
          </div>
        </div>
      </v-tooltip>

      <!-- Zygosity breakdown -->
      <v-tooltip
        v-if="mouseData.zygosity_analysis?.homozygous?.phenotype_count > 0"
        location="bottom"
      >
        <template #activator="{ props }">
          <v-chip color="error" variant="outlined" size="small" v-bind="props">
            {{ mouseData.zygosity_analysis.homozygous.phenotype_count }} hm
          </v-chip>
        </template>
        <div class="pa-2">
          <div class="font-weight-medium">Homozygous Knockout</div>
          <div class="text-caption">
            {{ mouseData.zygosity_analysis.homozygous.phenotype_count }} kidney phenotypes
          </div>
        </div>
      </v-tooltip>

      <v-tooltip
        v-if="mouseData.zygosity_analysis?.heterozygous?.phenotype_count > 0"
        location="bottom"
      >
        <template #activator="{ props }">
          <v-chip color="warning" variant="outlined" size="small" v-bind="props">
            {{ mouseData.zygosity_analysis.heterozygous.phenotype_count }} ht
          </v-chip>
        </template>
        <div class="pa-2">
          <div class="font-weight-medium">Heterozygous Knockout</div>
          <div class="text-caption">
            {{ mouseData.zygosity_analysis.heterozygous.phenotype_count }} kidney phenotypes
          </div>
        </div>
      </v-tooltip>

      <v-tooltip
        v-if="mouseData.zygosity_analysis?.conditional?.phenotype_count > 0"
        location="bottom"
      >
        <template #activator="{ props }">
          <v-chip color="info" variant="outlined" size="small" v-bind="props">
            {{ mouseData.zygosity_analysis.conditional.phenotype_count }} cn
          </v-chip>
        </template>
        <div class="pa-2">
          <div class="font-weight-medium">Conditional Knockout</div>
          <div class="text-caption">
            {{ mouseData.zygosity_analysis.conditional.phenotype_count }} kidney phenotypes
          </div>
        </div>
      </v-tooltip>
    </div>

    <!-- System analysis if available -->
    <div v-if="mouseData.system_analysis?.renal_urinary" class="d-flex align-center flex-wrap ga-2">
      <v-chip color="purple" variant="outlined" size="small">
        Renal: {{ mouseData.system_analysis.renal_urinary.phenotype_count }} phenotypes
      </v-chip>
    </div>
  </div>
</template>

<script setup>
defineProps({
  mouseData: {
    type: Object,
    default: null
  }
})

// Color coding for phenotype count
const getPhenotypeCountColor = count => {
  if (!count || count === 0) return 'grey'
  if (count >= 20) return 'error' // Many phenotypes (severe)
  if (count >= 10) return 'warning' // Moderate phenotypes
  if (count >= 5) return 'info' // Some phenotypes
  return 'success' // Few phenotypes
}
</script>
