<template>
  <div class="max-w-full">
    <!-- Classifications overview -->
    <div v-if="classifications?.length" class="mb-4">
      <div class="text-sm font-medium mb-3">Classifications</div>

      <div class="flex flex-wrap gap-2 mb-3">
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
          <component :is="getClassificationIcon(classification)" class="size-3 mr-1" />
          {{ classification }}
        </Badge>
      </div>
    </div>

    <!-- Submissions details -->
    <div v-if="submissions?.length" class="mb-4">
      <div class="text-sm font-medium mb-3">Submissions ({{ submissions.length }})</div>

      <Accordion type="single" collapsible>
        <AccordionItem
          v-for="(submission, index) in displaySubmissions"
          :key="index"
          :value="`submission-${index}`"
        >
          <AccordionTrigger class="py-2">
            <div class="flex items-center justify-between w-full pr-2">
              <div class="flex items-center gap-2">
                <Badge
                  variant="outline"
                  class="text-xs"
                  :style="{
                    backgroundColor: getClassificationColor(submission.classification) + '20',
                    color: getClassificationColor(submission.classification),
                    borderColor: getClassificationColor(submission.classification) + '40'
                  }"
                >
                  {{ submission.classification }}
                </Badge>
                <span class="text-sm">{{ submission.disease_name }}</span>
              </div>
              <div class="text-xs text-muted-foreground">
                {{ submission.submitter }}
              </div>
            </div>
          </AccordionTrigger>

          <AccordionContent>
            <div class="p-2 space-y-2">
              <div class="px-0">
                <div class="text-xs font-medium">Disease</div>
                <div class="text-sm text-muted-foreground">{{ submission.disease_name }}</div>
              </div>

              <div class="px-0">
                <div class="text-xs font-medium">Mode of Inheritance</div>
                <div class="text-sm text-muted-foreground">
                  {{ submission.mode_of_inheritance || 'Not specified' }}
                </div>
              </div>

              <div class="px-0">
                <div class="text-xs font-medium">Submission Date</div>
                <div class="text-sm text-muted-foreground">
                  {{ formatDate(submission.submission_date) }}
                </div>
              </div>

              <div class="px-0">
                <div class="text-xs font-medium">Submitter</div>
                <div class="text-sm text-muted-foreground">{{ submission.submitter }}</div>
              </div>
            </div>
          </AccordionContent>
        </AccordionItem>
      </Accordion>

      <!-- Show more button -->
      <Button
        v-if="hasMoreSubmissions"
        variant="ghost"
        size="sm"
        class="mt-2"
        @click="showAllSubmissions = !showAllSubmissions"
      >
        {{ showAllSubmissions ? 'Show Less' : `Show ${remainingSubmissions} More Submissions` }}
        <component :is="showAllSubmissions ? ChevronUp : ChevronDown" class="size-4 ml-1" />
      </Button>
    </div>

    <!-- Submitters summary -->
    <div v-if="submitters?.length" class="mb-4">
      <div class="text-sm font-medium mb-2">Submitters</div>
      <div class="flex flex-wrap gap-1">
        <Badge v-for="submitter in submitters" :key="submitter" variant="outline">
          {{ submitter }}
        </Badge>
      </div>
    </div>

    <!-- Diseases summary -->
    <div v-if="diseases?.length" class="mb-4">
      <div class="text-sm font-medium mb-2">Associated Diseases</div>
      <div class="space-y-1">
        <div v-for="disease in diseases" :key="disease" class="flex items-center gap-2 px-0">
          <Bug class="size-3 text-purple-600 dark:text-purple-400 shrink-0" />
          <span class="text-sm">{{ disease }}</span>
        </div>
      </div>
    </div>

    <!-- Evidence score -->
    <div class="mt-4 p-3 bg-muted rounded">
      <div class="text-center">
        <div class="text-2xl font-bold text-purple-600 dark:text-purple-400">
          {{ evidenceScore }}
        </div>
        <div class="text-xs text-muted-foreground">Weighted Evidence Score</div>
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
import { Badge } from '@/components/ui/badge'
import { Button } from '@/components/ui/button'
import {
  Accordion,
  AccordionContent,
  AccordionItem,
  AccordionTrigger
} from '@/components/ui/accordion'

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
    Definitive: '#22c55e',
    Strong: '#22c55e',
    Moderate: '#3b82f6',
    Supportive: '#f59e0b',
    Limited: '#f97316',
    'Disputed Evidence': '#ef4444',
    'No Known Disease Relationship': '#6b7280',
    'Refuted Evidence': '#ef4444'
  }
  return colors[classification] || '#6b7280'
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
