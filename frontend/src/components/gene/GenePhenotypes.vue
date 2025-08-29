<template>
  <div v-if="hpoData" class="gene-phenotypes">
    <div class="text-caption text-medium-emphasis mb-2">Human Phenotypes (HPO):</div>

    <!-- All HPO data in one row for better space usage -->
    <div class="d-flex align-center flex-wrap ga-2">
      <!-- Clinical Group -->
      <v-tooltip v-if="hpoData.classification?.clinical_group?.primary" location="bottom">
        <template #activator="{ props }">
          <v-chip
            :color="getClinicalGroupColor(hpoData.classification.clinical_group.primary)"
            variant="tonal"
            size="small"
            v-bind="props"
          >
            {{ formatClinicalGroup(hpoData.classification.clinical_group.primary) }}
          </v-chip>
        </template>
        <div class="pa-2">
          <div class="font-weight-medium">Clinical Classification</div>
          <div class="text-caption mb-1">
            Primary: {{ formatClinicalGroup(hpoData.classification.clinical_group.primary) }}
          </div>
          <div class="text-caption">
            Score:
            {{
              (
                hpoData.classification.clinical_group.scores[
                  hpoData.classification.clinical_group.primary
                ] * 100
              ).toFixed(0)
            }}%
          </div>
        </div>
      </v-tooltip>

      <!-- Onset Group -->
      <v-tooltip v-if="hpoData.classification?.onset_group?.primary" location="bottom">
        <template #activator="{ props }">
          <v-chip color="secondary" variant="outlined" size="small" v-bind="props">
            {{ formatOnsetGroup(hpoData.classification.onset_group.primary) }} onset
          </v-chip>
        </template>
        <div class="pa-2">
          <div class="font-weight-medium">Age of Onset</div>
          <div class="text-caption">
            {{ formatOnsetGroup(hpoData.classification.onset_group.primary) }}
            ({{
              (
                hpoData.classification.onset_group.scores[
                  hpoData.classification.onset_group.primary
                ] * 100
              ).toFixed(0)
            }}%)
          </div>
        </div>
      </v-tooltip>

      <!-- Syndromic Badge -->
      <v-tooltip v-if="hpoData.classification?.syndromic_assessment" location="bottom">
        <template #activator="{ props }">
          <v-chip
            :color="hpoData.classification.syndromic_assessment.is_syndromic ? 'warning' : 'grey'"
            :variant="
              hpoData.classification.syndromic_assessment.is_syndromic ? 'tonal' : 'outlined'
            "
            size="small"
            v-bind="props"
          >
            {{
              hpoData.classification.syndromic_assessment.is_syndromic ? 'Syndromic' : 'Isolated'
            }}
          </v-chip>
        </template>
        <div class="pa-2">
          <div class="font-weight-medium">Presentation Type</div>
          <div class="text-caption">
            {{
              hpoData.classification.syndromic_assessment.is_syndromic
                ? 'Syndromic kidney disease'
                : 'Isolated kidney phenotype'
            }}
          </div>
          <div
            v-if="hpoData.classification.syndromic_assessment.extra_renal_categories?.length"
            class="text-caption mt-1"
          >
            Extra-renal:
            {{ hpoData.classification.syndromic_assessment.extra_renal_categories.join(', ') }}
          </div>
        </div>
      </v-tooltip>

      <!-- Phenotype Count -->
      <v-tooltip location="bottom">
        <template #activator="{ props }">
          <v-chip color="primary" variant="outlined" size="small" v-bind="props">
            {{ hpoData.kidney_phenotype_count }}/{{ hpoData.phenotype_count }} kidney
          </v-chip>
        </template>
        <div class="pa-2 max-width-300">
          <div class="font-weight-medium">HPO Phenotypes</div>
          <div class="text-caption mb-1">
            {{ hpoData.kidney_phenotype_count }} kidney-related phenotypes out of
            {{ hpoData.phenotype_count }} total
          </div>
        </div>
      </v-tooltip>

      <!-- Disease associations -->
      <v-tooltip v-if="hpoData.disease_count > 0" location="bottom">
        <template #activator="{ props }">
          <v-chip color="info" variant="outlined" size="small" v-bind="props">
            {{ hpoData.disease_count }} diseases
          </v-chip>
        </template>
        <div class="pa-2">
          <div class="font-weight-medium">Disease Associations</div>
          <div class="text-caption">{{ hpoData.disease_count }} disease associations in HPO</div>
        </div>
      </v-tooltip>
    </div>
  </div>
</template>

<script setup>
defineProps({
  hpoData: {
    type: Object,
    default: null
  }
})

// Helper functions
const getClinicalGroupColor = group => {
  const colors = {
    complement: 'purple',
    cakut: 'blue',
    glomerulopathy: 'red',
    cyst_cilio: 'teal',
    tubulopathy: 'orange',
    nephrolithiasis: 'brown'
  }
  return colors[group] || 'grey'
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
