<template>
  <div class="score-breakdown">
    <!-- Compact inline display for tables -->
    <div v-if="variant === 'inline'" class="d-inline-flex align-center">
      <v-tooltip location="bottom" max-width="400">
        <template #activator="{ props: tooltipProps }">
          <v-chip
            :color="scoreColor"
            :size="size"
            variant="flat"
            class="font-weight-medium score-chip"
            v-bind="tooltipProps"
          >
            <v-icon :icon="scoreIcon" size="small" start />
            {{ formattedScore }}
          </v-chip>
        </template>
        <div class="pa-2">
          <div class="text-caption">
            {{ getScoreExplanation(score, Object.keys(breakdown || {}).length) }}
          </div>
        </div>
      </v-tooltip>
    </div>

    <!-- Detailed card display for gene detail pages -->
    <v-card v-else-if="variant === 'card'" class="score-breakdown-card" height="100%">
      <v-card-item>
        <template #prepend>
          <v-avatar :color="scoreColor" size="40">
            <v-icon :icon="scoreIcon" color="white" />
          </v-avatar>
        </template>
        <v-card-title>Evidence Score</v-card-title>
      </v-card-item>
      <v-card-text>
        <!-- Donut Chart Visualization -->
        <div v-if="score" class="text-center">
          <div class="position-relative d-inline-block">
            <v-progress-circular
              :model-value="score"
              :color="scoreColor"
              size="120"
              width="8"
              class="score-circle"
            >
              <div class="text-center">
                <div class="text-h4 font-weight-bold">
                  {{ formattedScore }}
                </div>
                <div class="text-caption text-medium-emphasis">/ 100</div>
              </div>
            </v-progress-circular>
          </div>
          <div class="mt-3">
            <v-chip :color="scoreColor" variant="tonal" size="small">
              {{ classification }}
            </v-chip>
          </div>

          <!-- Compact Breakdown Below -->
          <v-divider class="my-3" />
          <div class="score-breakdown-mini">
            <div class="text-caption text-medium-emphasis mb-2">Score Breakdown</div>
            <div class="d-flex flex-wrap justify-center ga-1">
              <v-tooltip
                v-for="(sourceScore, source) in sortedBreakdown"
                :key="source"
                location="bottom"
              >
                <template #activator="{ props: tooltipProps }">
                  <v-chip
                    :color="getSubScoreColor(sourceScore)"
                    size="x-small"
                    variant="tonal"
                    v-bind="tooltipProps"
                  >
                    {{ sourceAbbreviation(source) }}: {{ (sourceScore * 100).toFixed(0) }}
                  </v-chip>
                </template>
                <div>
                  <strong>{{ source }}</strong
                  ><br />
                  {{ getSourceDescription(source, sourceScore) }}
                </div>
              </v-tooltip>
            </div>
          </div>
        </div>
        <div v-else class="text-center py-4">
          <v-icon icon="mdi-help-circle" size="large" class="text-medium-emphasis mb-2" />
          <p class="text-body-2 text-medium-emphasis">No evidence score available</p>
        </div>
      </v-card-text>
    </v-card>

    <!-- Compact display for lists -->
    <div v-else-if="variant === 'compact'" class="score-compact">
      <div class="d-flex align-center justify-space-between">
        <v-chip :color="scoreColor" :size="size" variant="flat" class="font-weight-medium">
          {{ formattedScore }}
        </v-chip>
        <div class="d-flex ga-1">
          <v-tooltip v-for="(sourceScore, source) in topSources" :key="source" location="bottom">
            <template #activator="{ props: tooltipProps }">
              <v-chip
                :color="getSubScoreColor(sourceScore)"
                size="x-small"
                variant="tonal"
                v-bind="tooltipProps"
              >
                {{ sourceAbbreviation(source) }}
              </v-chip>
            </template>
            <span>{{ source }}: {{ (sourceScore * 100).toFixed(1) }}%</span>
          </v-tooltip>
          <v-chip v-if="remainingSourceCount > 0" size="x-small" variant="outlined">
            +{{ remainingSourceCount }}
          </v-chip>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { computed } from 'vue'
import { getScoreExplanation } from '@/utils/evidenceTiers'

// Props
const props = defineProps({
  score: {
    type: Number,
    default: null
  },
  breakdown: {
    type: Object,
    default: () => ({})
  },
  variant: {
    type: String,
    default: 'inline',
    validator: value => ['inline', 'card', 'compact'].includes(value)
  },
  size: {
    type: String,
    default: 'small',
    validator: value => ['x-small', 'small', 'default'].includes(value)
  },
  maxSources: {
    type: Number,
    default: 3
  }
})

// Computed properties
const formattedScore = computed(() => {
  if (props.score === null || props.score === undefined) return 'N/A'
  return props.score.toFixed(1)
})

const scoreColor = computed(() => {
  if (!props.score) return 'grey'
  if (props.score >= 95) return 'success'
  if (props.score >= 80) return 'success'
  if (props.score >= 70) return 'info'
  if (props.score >= 50) return 'warning'
  if (props.score >= 30) return 'orange'
  return 'error'
})

const scoreIcon = computed(() => {
  if (!props.score) return 'mdi-help-circle'
  if (props.score >= 80) return 'mdi-check-circle'
  if (props.score >= 50) return 'mdi-alert-circle'
  return 'mdi-close-circle'
})

const classification = computed(() => {
  if (!props.score) return 'Unknown'
  if (props.score >= 95) return 'Definitive'
  if (props.score >= 80) return 'Strong'
  if (props.score >= 70) return 'Moderate'
  if (props.score >= 50) return 'Limited'
  if (props.score >= 30) return 'Minimal'
  return 'Disputed'
})

const sortedBreakdown = computed(() => {
  if (!props.breakdown) return {}

  // Sort by score value descending
  return Object.entries(props.breakdown)
    .sort(([, a], [, b]) => b - a)
    .reduce((acc, [key, value]) => {
      acc[key] = value
      return acc
    }, {})
})

const topSources = computed(() => {
  const entries = Object.entries(sortedBreakdown.value)
  return entries.slice(0, props.maxSources).reduce((acc, [key, value]) => {
    acc[key] = value
    return acc
  }, {})
})

const remainingSourceCount = computed(() => {
  const total = Object.keys(sortedBreakdown.value).length
  return Math.max(0, total - props.maxSources)
})

// Methods
const getSubScoreColor = score => {
  const percentage = score * 100
  if (percentage >= 90) return 'success'
  if (percentage >= 70) return 'info'
  if (percentage >= 50) return 'warning'
  if (percentage >= 30) return 'orange'
  return 'error'
}

const sourceAbbreviation = source => {
  const abbreviations = {
    PanelApp: 'PA',
    HPO: 'HPO',
    PubTator: 'PT',
    Literature: 'LIT',
    ClinGen: 'CG',
    GenCC: 'GC'
  }
  return abbreviations[source] || source.substring(0, 2).toUpperCase()
}

const getSourceDescription = (source, score) => {
  const percentage = (score * 100).toFixed(1)
  const descriptions = {
    PanelApp: `Panel confidence score: ${percentage}%`,
    HPO: `Phenotype association strength: ${percentage}%`,
    PubTator: `Literature evidence score: ${percentage}%`,
    Literature: `Publication support: ${percentage}%`,
    ClinGen: score >= 0.8 ? 'Definitive clinical validity' : 'Moderate clinical validity',
    GenCC: score >= 0.8 ? 'Strong gene-disease association' : 'Moderate association'
  }
  return descriptions[source] || `Evidence score: ${percentage}%`
}
</script>

<style scoped>
/* Following Style Guide - Compact density for data interfaces */
.score-chip {
  cursor: help;
  font-variant-numeric: tabular-nums;
}

.score-details {
  min-width: 250px;
}

.score-item {
  margin-bottom: 8px;
}

.score-item:last-child {
  margin-bottom: 0;
}

.score-breakdown-card {
  border: 1px solid rgb(var(--v-theme-surface-variant));
  transition: all 0.3s cubic-bezier(0.4, 0, 0.2, 1);
}

.score-breakdown-card:hover {
  box-shadow: 0 2px 8px rgba(var(--v-theme-shadow), 0.12);
}

.score-details-expanded {
  padding-top: 8px;
}

.score-item-expanded {
  padding: 8px;
  border-radius: 4px;
  background: rgba(var(--v-theme-surface-variant), 0.4);
  transition: background-color 0.2s ease;
}

.score-item-expanded:hover {
  background: rgba(var(--v-theme-surface-variant), 0.6);
}

.score-compact {
  display: inline-block;
}

/* Dark theme adjustments */
.v-theme--dark .score-item-expanded {
  background: rgba(var(--v-theme-surface-bright), 0.08);
}

.v-theme--dark .score-item-expanded:hover {
  background: rgba(var(--v-theme-surface-bright), 0.12);
}

/* Smooth transitions */
.v-chip,
.v-progress-linear {
  transition: all 0.2s ease;
}

/* Focus states - Following Style Guide */
.score-chip:focus-visible {
  outline: 2px solid rgb(var(--v-theme-primary));
  outline-offset: 2px;
}
</style>
