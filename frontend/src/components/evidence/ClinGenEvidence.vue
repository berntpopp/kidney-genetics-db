<template>
  <div class="max-w-full">
    <!-- Validity assessments -->
    <div v-if="validities?.length" class="mb-4">
      <div class="text-sm font-medium mb-3">Validity Assessments ({{ validityCount }})</div>

      <div class="space-y-3">
        <div
          v-for="(validity, index) in displayValidities"
          :key="index"
          class="p-3 bg-muted/50 rounded-lg"
        >
          <!-- Classification and disease -->
          <div class="flex items-center justify-between mb-2">
            <div class="flex items-center gap-2">
              <Badge
                variant="outline"
                :style="{
                  backgroundColor: getClassificationColor(validity.classification) + '20',
                  color: getClassificationColor(validity.classification),
                  borderColor: getClassificationColor(validity.classification) + '40'
                }"
              >
                <component
                  :is="getClassificationIcon(validity.classification)"
                  class="size-3 mr-1"
                />
                {{ validity.classification }}
              </Badge>
              <span class="text-sm font-medium">
                {{ validity.disease_name }}
              </span>
            </div>
          </div>

          <!-- Details -->
          <div class="pl-4">
            <div v-if="validity.expert_panel" class="text-xs text-muted-foreground mb-1">
              <Users class="size-3 inline-block align-middle" />
              {{ validity.expert_panel }}
            </div>

            <div v-if="validity.mode_of_inheritance" class="text-xs text-muted-foreground mb-1">
              <GitBranch class="size-3 inline-block align-middle" />
              {{ validity.mode_of_inheritance }}
            </div>

            <div v-if="validity.release_date" class="text-xs text-muted-foreground">
              <Calendar class="size-3 inline-block align-middle" />
              Released: {{ formatDate(validity.release_date) }}
            </div>
          </div>
        </div>
      </div>

      <!-- Show more button -->
      <Button
        v-if="hasMoreValidities"
        variant="ghost"
        size="sm"
        class="mt-2"
        @click="showAllValidities = !showAllValidities"
      >
        {{ showAllValidities ? 'Show Less' : `Show ${remainingValidities} More Assessments` }}
        <component :is="showAllValidities ? ChevronUp : ChevronDown" class="size-4 ml-1" />
      </Button>
    </div>

    <!-- Expert panels summary -->
    <div v-if="expertPanels?.length" class="mb-4">
      <div class="text-sm font-medium mb-2">Expert Panels</div>
      <div class="flex flex-wrap gap-2">
        <Badge
          v-for="panel in expertPanels"
          :key="panel"
          variant="outline"
          :style="{
            backgroundColor: '#22c55e20',
            color: '#22c55e',
            borderColor: '#22c55e40'
          }"
        >
          <Award class="size-3 mr-1" />
          {{ panel }}
        </Badge>
      </div>
    </div>

    <!-- Diseases summary -->
    <div v-if="diseases?.length" class="mb-4">
      <div class="text-sm font-medium mb-2">Associated Diseases</div>
      <div class="space-y-1">
        <div v-for="disease in diseases" :key="disease" class="flex items-center gap-2 px-0">
          <Bug class="size-3 text-green-600 dark:text-green-400 shrink-0" />
          <span class="text-sm">{{ disease }}</span>
        </div>
      </div>
    </div>

    <!-- Classifications distribution -->
    <div v-if="classifications?.length" class="mb-4">
      <div class="text-sm font-medium mb-2">Classification Summary</div>
      <div class="flex flex-wrap gap-2">
        <Badge
          v-for="classification in uniqueClassifications"
          :key="classification"
          variant="outline"
          :style="{
            backgroundColor: getClassificationColor(classification) + '20',
            color: getClassificationColor(classification),
            borderColor: getClassificationColor(classification) + '40'
          }"
        >
          {{ classification }}
        </Badge>
      </div>
    </div>

    <!-- Evidence score -->
    <div class="mt-4 p-3 bg-muted rounded">
      <div class="grid grid-cols-2 gap-4">
        <div class="text-center">
          <div class="text-xl font-bold text-green-600 dark:text-green-400">
            {{ maxScore }}
          </div>
          <div class="text-xs text-muted-foreground">Max Score</div>
        </div>
        <div class="text-center">
          <div class="text-xl font-bold text-green-600 dark:text-green-400">
            {{ validityCount }}
          </div>
          <div class="text-xs text-muted-foreground">Assessments</div>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, computed } from 'vue'
import {
  Users,
  GitBranch,
  Calendar,
  ChevronUp,
  ChevronDown,
  Award,
  Bug,
  CircleCheck,
  Check,
  AlertTriangle,
  CircleMinus,
  CircleHelp,
  CircleX,
  Circle
} from 'lucide-vue-next'
import { Badge } from '@/components/ui/badge'
import { Button } from '@/components/ui/button'

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
    Definitive: '#22c55e',
    Strong: '#22c55e',
    Moderate: '#3b82f6',
    Limited: '#f59e0b',
    'No Specified Relationship': '#6b7280',
    Disputed: '#f97316',
    Refuted: '#ef4444'
  }
  return colors[classification] || '#6b7280'
}

const getClassificationIcon = classification => {
  const icons = {
    Definitive: CircleCheck,
    Strong: Check,
    Moderate: Check,
    Limited: AlertTriangle,
    'No Specified Relationship': CircleMinus,
    Disputed: CircleHelp,
    Refuted: CircleX
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
