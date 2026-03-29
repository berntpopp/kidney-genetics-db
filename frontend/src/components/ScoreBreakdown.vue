<template>
  <div>
    <!-- Compact inline display for tables -->
    <div v-if="variant === 'inline'" class="inline-flex items-center">
      <HoverPopover content-class="max-w-xs p-3">
        <Badge
          :class="[chipSizeClasses, 'cursor-pointer font-medium tabular-nums']"
          :style="{
            backgroundColor: scoreHexColor + '20',
            color: scoreHexColor,
            borderColor: scoreHexColor + '40'
          }"
          variant="outline"
        >
          <component :is="scoreIcon" :size="12" class="mr-1" />
          {{ formattedScore }}
        </Badge>
        <template #content>
          <p class="text-xs text-foreground">
            {{ getScoreExplanation(score, Object.keys(breakdown || {}).length) }}
          </p>
          <div v-if="sortedBreakdownEntries.length" class="mt-2 space-y-1">
            <div
              v-for="[source, sourceScore] in topSourceEntries"
              :key="source"
              class="flex justify-between text-xs"
            >
              <span class="text-foreground">{{ sourceAbbreviation(source) }}</span>
              <span class="font-mono ml-3 text-foreground"
                >{{ (sourceScore * 100).toFixed(1) }}%</span
              >
            </div>
            <p v-if="remainingSourceCount > 0" class="text-xs text-foreground/60">
              +{{ remainingSourceCount }} more
            </p>
          </div>
        </template>
      </HoverPopover>
    </div>

    <!-- Detailed card display for gene detail pages -->
    <Card v-else-if="variant === 'card'" class="h-full">
      <CardHeader class="flex flex-row items-center gap-3 pb-2">
        <div
          class="flex h-10 w-10 items-center justify-center rounded-full"
          :style="{ backgroundColor: scoreHexColor + '20' }"
        >
          <component :is="scoreIcon" :size="20" :style="{ color: scoreHexColor }" />
        </div>
        <CardTitle tag="h2" class="text-base">Evidence Score</CardTitle>
      </CardHeader>
      <CardContent>
        <!-- Donut Chart Visualization -->
        <div v-if="score" class="text-center">
          <div class="relative inline-flex items-center justify-center">
            <svg :width="80" :height="80" class="-rotate-90">
              <circle
                :cx="40"
                :cy="40"
                :r="donutRadius"
                fill="none"
                stroke="currentColor"
                class="text-muted/20"
                :stroke-width="8"
              />
              <circle
                :cx="40"
                :cy="40"
                :r="donutRadius"
                fill="none"
                :stroke="scoreHexColor"
                :stroke-width="8"
                :stroke-dasharray="circumference"
                :stroke-dashoffset="circumference - (circumference * (score ?? 0)) / 100"
                stroke-linecap="round"
              />
            </svg>
            <span class="absolute text-lg font-bold" :style="{ color: scoreHexColor }">
              {{ formattedScore }}
            </span>
          </div>
          <div class="mt-3">
            <Badge
              :style="{
                backgroundColor: scoreHexColor + '20',
                color: scoreHexColor,
                borderColor: scoreHexColor + '40'
              }"
              variant="outline"
            >
              {{ classification }}
            </Badge>
          </div>

          <!-- Compact Breakdown Below -->
          <Separator class="my-3" />
          <div>
            <div class="text-xs text-muted-foreground mb-2">Score Breakdown</div>
            <div class="flex flex-wrap justify-center gap-1">
              <HoverPopover
                v-for="[source, sourceScore] in sortedBreakdownEntries"
                :key="source"
                content-class="w-auto p-3"
              >
                <Badge
                  class="cursor-pointer text-[10px]"
                  :style="{
                    backgroundColor: getSubScoreHexColor(sourceScore) + '20',
                    color: getSubScoreHexColor(sourceScore),
                    borderColor: getSubScoreHexColor(sourceScore) + '40'
                  }"
                  variant="outline"
                >
                  {{ sourceAbbreviation(source) }}: {{ (sourceScore * 100).toFixed(0) }}
                </Badge>
                <template #content>
                  <p class="font-medium text-xs text-foreground">{{ source }}</p>
                  <p class="text-xs text-foreground/70">
                    {{ getSourceDescription(source, sourceScore) }}
                  </p>
                </template>
              </HoverPopover>
            </div>
          </div>
        </div>
        <div v-else class="text-center py-4">
          <CircleHelp class="mx-auto mb-2 text-muted-foreground" :size="24" />
          <p class="text-sm text-muted-foreground">No evidence score available</p>
        </div>
      </CardContent>
    </Card>

    <!-- Compact display for lists -->
    <div v-else-if="variant === 'compact'" class="inline-block">
      <div class="flex items-center justify-between gap-2">
        <Badge
          :class="[chipSizeClasses, 'font-medium tabular-nums']"
          :style="{
            backgroundColor: scoreHexColor + '20',
            color: scoreHexColor,
            borderColor: scoreHexColor + '40'
          }"
          variant="outline"
        >
          {{ formattedScore }}
        </Badge>
        <div class="flex gap-1">
          <HoverPopover v-for="[source, sourceScore] in topSourceEntries" :key="source">
            <Badge
              class="cursor-pointer text-[10px]"
              :style="{
                backgroundColor: getSubScoreHexColor(sourceScore) + '20',
                color: getSubScoreHexColor(sourceScore),
                borderColor: getSubScoreHexColor(sourceScore) + '40'
              }"
              variant="outline"
            >
              {{ sourceAbbreviation(source) }}
            </Badge>
            <template #content>
              <span class="text-xs text-foreground"
                >{{ source }}: {{ (sourceScore * 100).toFixed(1) }}%</span
              >
            </template>
          </HoverPopover>
          <Badge v-if="remainingSourceCount > 0" variant="outline" class="text-[10px]">
            +{{ remainingSourceCount }}
          </Badge>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { computed } from 'vue'
import HoverPopover from '@/components/ui/HoverPopover.vue'
import { Badge } from '@/components/ui/badge'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { Separator } from '@/components/ui/separator'
import { getScoreExplanation } from '@/utils/evidenceTiers'
import { CircleHelp, CircleCheck, CircleAlert, CircleX } from 'lucide-vue-next'

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

/** Map Vuetify-style color names to hex */
const colorMap = {
  success: '#22c55e',
  info: '#3b82f6',
  warning: '#f59e0b',
  orange: '#f97316',
  error: '#ef4444',
  grey: '#6b7280'
}

const scoreHexColor = computed(() => {
  if (!props.score) return colorMap.grey
  if (props.score >= 80) return colorMap.success
  if (props.score >= 70) return colorMap.info
  if (props.score >= 50) return colorMap.warning
  if (props.score >= 30) return colorMap.orange
  return colorMap.error
})

const scoreIcon = computed(() => {
  if (!props.score) return CircleHelp
  if (props.score >= 80) return CircleCheck
  if (props.score >= 50) return CircleAlert
  return CircleX
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

const chipSizeClasses = computed(() => {
  switch (props.size) {
    case 'x-small':
      return 'text-[10px] px-1.5 py-0'
    case 'small':
      return 'text-xs px-2 py-0.5'
    default:
      return 'text-sm px-2.5 py-1'
  }
})

const sortedBreakdownEntries = computed(() => {
  if (!props.breakdown) return []
  return Object.entries(props.breakdown).sort(([, a], [, b]) => b - a)
})

const topSourceEntries = computed(() => {
  return sortedBreakdownEntries.value.slice(0, props.maxSources)
})

const remainingSourceCount = computed(() => {
  return Math.max(0, sortedBreakdownEntries.value.length - props.maxSources)
})

// SVG donut
const donutRadius = 36 // (80 - 8) / 2
const circumference = 2 * Math.PI * donutRadius

// Methods
const getSubScoreHexColor = score => {
  const pct = score * 100
  if (pct >= 90) return colorMap.success
  if (pct >= 70) return colorMap.info
  if (pct >= 50) return colorMap.warning
  if (pct >= 30) return colorMap.orange
  return colorMap.error
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
