<template>
  <div class="gencc-evidence">
    <!-- Classifications overview -->
    <div v-if="classifications?.length" class="mb-4">
      <div class="text-subtitle-2 font-weight-medium mb-3">Classifications</div>

      <div class="d-flex flex-wrap ga-2 mb-3">
        <v-chip
          v-for="classification in uniqueClassifications"
          :key="classification"
          :color="getClassificationColor(classification)"
          variant="tonal"
          size="small"
        >
          <component :is="getClassificationIcon(classification)" class="size-3 mr-1" />
          {{ classification }}
        </v-chip>
      </div>
    </div>

    <!-- Submissions details -->
    <div v-if="submissions?.length" class="mb-4">
      <div class="text-subtitle-2 font-weight-medium mb-3">
        Submissions ({{ submissions.length }})
      </div>

      <v-expansion-panels variant="accordion" density="compact">
        <v-expansion-panel
          v-for="(submission, index) in displaySubmissions"
          :key="index"
          elevation="0"
        >
          <v-expansion-panel-title class="py-2">
            <div class="d-flex align-center justify-space-between w-100">
              <div class="d-flex align-center ga-2">
                <v-chip
                  size="x-small"
                  :color="getClassificationColor(submission.classification)"
                  variant="tonal"
                >
                  {{ submission.classification }}
                </v-chip>
                <span class="text-body-2">{{ submission.disease_name }}</span>
              </div>
              <div class="text-caption text-medium-emphasis">
                {{ submission.submitter }}
              </div>
            </div>
          </v-expansion-panel-title>

          <v-expansion-panel-text>
            <div class="pa-2">
              <v-list density="compact" class="transparent">
                <v-list-item class="px-0">
                  <v-list-item-title class="text-caption">Disease</v-list-item-title>
                  <v-list-item-subtitle>{{ submission.disease_name }}</v-list-item-subtitle>
                </v-list-item>

                <v-list-item class="px-0">
                  <v-list-item-title class="text-caption">Mode of Inheritance</v-list-item-title>
                  <v-list-item-subtitle>{{
                    submission.mode_of_inheritance || 'Not specified'
                  }}</v-list-item-subtitle>
                </v-list-item>

                <v-list-item class="px-0">
                  <v-list-item-title class="text-caption">Submission Date</v-list-item-title>
                  <v-list-item-subtitle>{{
                    formatDate(submission.submission_date)
                  }}</v-list-item-subtitle>
                </v-list-item>

                <v-list-item class="px-0">
                  <v-list-item-title class="text-caption">Submitter</v-list-item-title>
                  <v-list-item-subtitle>{{ submission.submitter }}</v-list-item-subtitle>
                </v-list-item>
              </v-list>
            </div>
          </v-expansion-panel-text>
        </v-expansion-panel>
      </v-expansion-panels>

      <!-- Show more button -->
      <v-btn
        v-if="hasMoreSubmissions"
        variant="text"
        size="small"
        class="mt-2"
        @click="showAllSubmissions = !showAllSubmissions"
      >
        {{ showAllSubmissions ? 'Show Less' : `Show ${remainingSubmissions} More Submissions` }}
        <component :is="showAllSubmissions ? ChevronUp : ChevronDown" class="size-4 ml-1" />
      </v-btn>
    </div>

    <!-- Submitters summary -->
    <div v-if="submitters?.length" class="mb-4">
      <div class="text-subtitle-2 font-weight-medium mb-2">Submitters</div>
      <div class="d-flex flex-wrap ga-1">
        <v-chip v-for="submitter in submitters" :key="submitter" size="x-small" variant="outlined">
          {{ submitter }}
        </v-chip>
      </div>
    </div>

    <!-- Diseases summary -->
    <div v-if="diseases?.length" class="mb-4">
      <div class="text-subtitle-2 font-weight-medium mb-2">Associated Diseases</div>
      <v-list density="compact" class="transparent">
        <v-list-item v-for="disease in diseases" :key="disease" class="px-0">
          <template #prepend>
            <Bug class="size-3 text-purple-600 dark:text-purple-400" />
          </template>
          <v-list-item-title class="text-body-2">{{ disease }}</v-list-item-title>
        </v-list-item>
      </v-list>
    </div>

    <!-- Evidence score -->
    <div class="mt-4 pa-3 bg-surface-light rounded">
      <div class="text-center">
        <div class="text-h4 font-weight-bold text-purple">
          {{ evidenceScore }}
        </div>
        <div class="text-caption text-medium-emphasis">Weighted Evidence Score</div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, computed } from 'vue'
import {
  ChevronUp,
  ChevronDown,
  Bug,
  CircleCheck,
  Check,
  Info,
  AlertTriangle,
  CircleX,
  CircleMinus,
  Ban,
  Circle
} from 'lucide-vue-next'

const props = defineProps({
  evidenceData: {
    type: Object,
    required: true
  },
  sourceName: {
    type: String,
    default: 'GenCC'
  }
})

const showAllSubmissions = ref(false)

// Data accessors
const submissions = computed(() => {
  return props.evidenceData?.submissions || []
})

const classifications = computed(() => {
  return props.evidenceData?.classifications || []
})

const uniqueClassifications = computed(() => {
  // Sort by importance (Definitive > Strong > Moderate > Supportive > Limited)
  const order = ['Definitive', 'Strong', 'Moderate', 'Supportive', 'Limited', 'Disputed Evidence']
  return [...new Set(classifications.value)].sort((a, b) => {
    return order.indexOf(a) - order.indexOf(b)
  })
})

const submitters = computed(() => {
  return props.evidenceData?.submitters || []
})

const diseases = computed(() => {
  return props.evidenceData?.diseases || []
})

const evidenceScore = computed(() => {
  const score = props.evidenceData?.evidence_score
  return score !== undefined ? score.toFixed(2) : 'N/A'
})

// Display logic
const displaySubmissions = computed(() => {
  if (showAllSubmissions.value) {
    return submissions.value
  }
  return submissions.value.slice(0, 3)
})

const hasMoreSubmissions = computed(() => {
  return submissions.value.length > 3
})

const remainingSubmissions = computed(() => {
  return submissions.value.length - 3
})

// Helper functions
const getClassificationColor = classification => {
  const colors = {
    Definitive: 'success',
    Strong: 'success',
    Moderate: 'info',
    Supportive: 'warning',
    Limited: 'orange',
    'Disputed Evidence': 'error',
    'No Known Disease Relationship': 'grey',
    'Refuted Evidence': 'error'
  }
  return colors[classification] || 'grey'
}

const getClassificationIcon = classification => {
  const icons = {
    Definitive: CircleCheck,
    Strong: Check,
    Moderate: Check,
    Supportive: Info,
    Limited: AlertTriangle,
    'Disputed Evidence': CircleX,
    'No Known Disease Relationship': CircleMinus,
    'Refuted Evidence': Ban
  }
  return icons[classification] || Circle
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
.gencc-evidence {
  max-width: 100%;
}

.bg-surface-light {
  background: rgba(var(--v-theme-surface-variant), 0.3);
}
</style>
