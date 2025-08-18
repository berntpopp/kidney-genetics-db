<template>
  <div class="clingen-evidence">
    <!-- Validity assessments -->
    <div v-if="validities?.length" class="mb-4">
      <div class="text-subtitle-2 font-weight-medium mb-3">
        Validity Assessments ({{ validityCount }})
      </div>

      <v-list density="compact" class="transparent">
        <v-list-item
          v-for="(validity, index) in displayValidities"
          :key="index"
          class="px-0 mb-3 validity-item"
        >
          <div class="w-100">
            <!-- Classification and disease -->
            <div class="d-flex align-center justify-space-between mb-2">
              <div class="d-flex align-center ga-2">
                <v-chip
                  size="small"
                  :color="getClassificationColor(validity.classification)"
                  variant="tonal"
                >
                  <v-icon
                    :icon="getClassificationIcon(validity.classification)"
                    start
                    size="x-small"
                  />
                  {{ validity.classification }}
                </v-chip>
                <span class="text-body-2 font-weight-medium">
                  {{ validity.disease_name }}
                </span>
              </div>
            </div>

            <!-- Details -->
            <div class="pl-4">
              <div v-if="validity.expert_panel" class="text-caption text-medium-emphasis mb-1">
                <v-icon icon="mdi-account-group" size="x-small" />
                {{ validity.expert_panel }}
              </div>

              <div
                v-if="validity.mode_of_inheritance"
                class="text-caption text-medium-emphasis mb-1"
              >
                <v-icon icon="mdi-family-tree" size="x-small" />
                {{ validity.mode_of_inheritance }}
              </div>

              <div v-if="validity.release_date" class="text-caption text-medium-emphasis">
                <v-icon icon="mdi-calendar" size="x-small" />
                Released: {{ formatDate(validity.release_date) }}
              </div>
            </div>
          </div>
        </v-list-item>
      </v-list>

      <!-- Show more button -->
      <v-btn
        v-if="hasMoreValidities"
        variant="text"
        size="small"
        class="mt-2"
        @click="showAllValidities = !showAllValidities"
      >
        {{ showAllValidities ? 'Show Less' : `Show ${remainingValidities} More Assessments` }}
        <v-icon :icon="showAllValidities ? 'mdi-chevron-up' : 'mdi-chevron-down'" end />
      </v-btn>
    </div>

    <!-- Expert panels summary -->
    <div v-if="expertPanels?.length" class="mb-4">
      <div class="text-subtitle-2 font-weight-medium mb-2">Expert Panels</div>
      <div class="d-flex flex-wrap ga-2">
        <v-chip
          v-for="panel in expertPanels"
          :key="panel"
          size="small"
          variant="outlined"
          color="green"
        >
          <v-icon icon="mdi-certificate" start size="x-small" />
          {{ panel }}
        </v-chip>
      </div>
    </div>

    <!-- Diseases summary -->
    <div v-if="diseases?.length" class="mb-4">
      <div class="text-subtitle-2 font-weight-medium mb-2">Associated Diseases</div>
      <v-list density="compact" class="transparent">
        <v-list-item v-for="disease in diseases" :key="disease" class="px-0">
          <template #prepend>
            <v-icon icon="mdi-virus-outline" size="x-small" color="green" />
          </template>
          <v-list-item-title class="text-body-2">{{ disease }}</v-list-item-title>
        </v-list-item>
      </v-list>
    </div>

    <!-- Classifications distribution -->
    <div v-if="classifications?.length" class="mb-4">
      <div class="text-subtitle-2 font-weight-medium mb-2">Classification Summary</div>
      <div class="d-flex flex-wrap ga-2">
        <v-chip
          v-for="classification in uniqueClassifications"
          :key="classification"
          :color="getClassificationColor(classification)"
          variant="tonal"
          size="small"
        >
          {{ classification }}
        </v-chip>
      </div>
    </div>

    <!-- Evidence score -->
    <div class="mt-4 pa-3 bg-surface-light rounded">
      <v-row dense>
        <v-col cols="6">
          <div class="text-center">
            <div class="text-h5 font-weight-bold text-green">
              {{ maxScore }}
            </div>
            <div class="text-caption text-medium-emphasis">Max Score</div>
          </div>
        </v-col>
        <v-col cols="6">
          <div class="text-center">
            <div class="text-h5 font-weight-bold text-green">
              {{ validityCount }}
            </div>
            <div class="text-caption text-medium-emphasis">Assessments</div>
          </div>
        </v-col>
      </v-row>
    </div>
  </div>
</template>

<script setup>
import { ref, computed } from 'vue'

const props = defineProps({
  evidenceData: {
    type: Object,
    required: true
  },
  sourceName: {
    type: String,
    default: 'ClinGen'
  }
})

const showAllValidities = ref(false)

// Data accessors
const validities = computed(() => {
  return props.evidenceData?.validities || []
})

const validityCount = computed(() => {
  return props.evidenceData?.validity_count || validities.value.length
})

const expertPanels = computed(() => {
  return props.evidenceData?.expert_panels || []
})

const diseases = computed(() => {
  return props.evidenceData?.diseases || []
})

const classifications = computed(() => {
  return props.evidenceData?.classifications || []
})

const uniqueClassifications = computed(() => {
  const order = [
    'Definitive',
    'Strong',
    'Moderate',
    'Limited',
    'No Specified Relationship',
    'Disputed',
    'Refuted'
  ]
  return [...new Set(classifications.value)].sort((a, b) => {
    return order.indexOf(a) - order.indexOf(b)
  })
})

const maxScore = computed(() => {
  const score = props.evidenceData?.max_classification_score
  return score !== undefined ? (score * 100).toFixed(0) : 'N/A'
})

// Display logic
const displayValidities = computed(() => {
  if (showAllValidities.value) {
    return validities.value
  }
  return validities.value.slice(0, 3)
})

const hasMoreValidities = computed(() => {
  return validities.value.length > 3
})

const remainingValidities = computed(() => {
  return validities.value.length - 3
})

// Helper functions
const getClassificationColor = classification => {
  const colors = {
    Definitive: 'success',
    Strong: 'success',
    Moderate: 'info',
    Limited: 'warning',
    'No Specified Relationship': 'grey',
    Disputed: 'orange',
    Refuted: 'error'
  }
  return colors[classification] || 'grey'
}

const getClassificationIcon = classification => {
  const icons = {
    Definitive: 'mdi-check-circle',
    Strong: 'mdi-check-bold',
    Moderate: 'mdi-check',
    Limited: 'mdi-alert',
    'No Specified Relationship': 'mdi-minus-circle',
    Disputed: 'mdi-help-circle',
    Refuted: 'mdi-close-circle'
  }
  return icons[classification] || 'mdi-circle'
}

const formatDate = dateString => {
  if (!dateString) return 'Unknown'
  const date = new Date(dateString)
  return date.toLocaleDateString('en-US', {
    year: 'numeric',
    month: 'short',
    day: 'numeric'
  })
}
</script>

<style scoped>
.clingen-evidence {
  max-width: 100%;
}

.validity-item {
  padding: 12px;
  background: rgba(var(--v-theme-surface-variant), 0.1);
  border-radius: 8px;
  margin-bottom: 8px;
}

.bg-surface-light {
  background: rgba(var(--v-theme-surface-variant), 0.3);
}
</style>
