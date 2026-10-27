<template>
  <div>
    <!-- Compact inline display for tables -->
    <div v-if="variant === 'inline'" class="inline-flex items-center">
      <HoverPopover content-class="max-w-xs p-3">
        <Badge
          as="span"
          :class="[chipSizeClasses, 'cursor-pointer font-medium tabular-nums']"
          :style="tintedChipStyle(tierConfig.color)"
          variant="outline"
        >
          <component :is="tierConfig.icon" :size="12" class="mr-1" aria-hidden="true" />
          {{ formattedScore }}
        </Badge>
        <template #content>
          <p class="text-xs text-foreground">
            {{ getScoreExplanation(score, Object.keys(breakdown || {}).length, tier) }}
          </p>
          <div v-if="sortedBreakdownEntries.length" class="mt-2 space-y-1">
            <div
              v-for="[source, sourceScore] in topSourceEntries"
              :key="source"
              class="flex justify-between text-xs"
            >
              <span class="text-foreground">{{ sourceDisplayName(source) }}</span>
              <span class="ml-3 font-mono text-foreground">{{ formatPercent(sourceScore) }}</span>
            </div>
            <p v-if="remainingSourceCount > 0" class="text-xs text-muted-foreground">
              +{{ remainingSourceCount }} more
            </p>
          </div>
        </template>
      </HoverPopover>
    </div>

    <!-- Detailed card display for gene detail pages -->
    <Card v-else-if="variant === 'card'" class="h-full gap-4">
      <CardHeader>
        <CardTitle tag="h2" class="text-base">Evidence score</CardTitle>
      </CardHeader>
      <CardContent>
        <div v-if="score != null" class="flex flex-col items-center gap-3 text-center">
          <div class="relative inline-flex items-center justify-center">
            <svg width="96" height="96" class="-rotate-90" aria-hidden="true">
              <circle
                cx="48"
                cy="48"
                :r="donutRadius"
                fill="none"
                stroke="var(--muted)"
                stroke-width="8"
              />
              <circle
                cx="48"
                cy="48"
                :r="donutRadius"
                fill="none"
                :stroke="tierConfig.color"
                stroke-width="8"
                :stroke-dasharray="circumference"
                :stroke-dashoffset="circumference - (circumference * Math.min(score, 100)) / 100"
                stroke-linecap="round"
              />
            </svg>
            <span class="absolute text-xl font-semibold tabular-nums text-foreground">
              {{ formattedScore }}<span class="text-sm text-muted-foreground">%</span>
            </span>
          </div>
          <Chip :tier="tier" />

          <Separator class="my-1" />
          <div class="w-full">
            <h3 class="mb-2 text-xs font-medium text-muted-foreground">Score by source</h3>
            <div v-if="sortedBreakdownEntries.length" class="flex flex-wrap justify-center gap-1.5">
              <Chip
                v-for="[source, sourceScore] in sortedBreakdownEntries"
                :key="source"
                kind="neutral"
                class="tabular-nums"
                :label="`${sourceDisplayName(source)} ${formatPercent(sourceScore)}`"
                :tooltip="getSourceDescription(source, sourceScore)"
              />
            </div>
            <p v-else class="text-sm text-muted-foreground">No per-source scores.</p>
          </div>
        </div>
        <div v-else class="py-4 text-center">
          <CircleHelp class="mx-auto mb-2 text-muted-foreground" :size="24" aria-hidden="true" />
          <p class="text-sm text-muted-foreground">No evidence score available</p>
        </div>
      </CardContent>
    </Card>
  </div>
</template>

<script setup>
import { computed } from 'vue'
import HoverPopover from '@/components/ui/HoverPopover.vue'
import { Badge } from '@/components/ui/badge'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { Separator } from '@/components/ui/separator'
import { Chip } from '@/components/shared'
import { getScoreExplanation, getTierConfig, tintedChipStyle } from '@/utils/evidenceTiers'
import { sourceDisplayName } from '@/utils/sources'
import { CircleHelp } from 'lucide-vue-next'

const props = defineProps({
  score: { type: Number, default: null },
  // Backend evidence_tier; the only source of the label (issue 314)
  tier: { type: String, default: null },
  breakdown: { type: Object, default: () => ({}) },
  variant: {
    type: String,
    default: 'inline',
    validator: value => ['inline', 'card'].includes(value)
  },
  size: {
    type: String,
    default: 'small',
    validator: value => ['x-small', 'small', 'default'].includes(value)
  },
  maxSources: { type: Number, default: 3 }
})

const formattedScore = computed(() => (props.score == null ? 'N/A' : props.score.toFixed(1)))

/** One format for per-source scores everywhere (evidence cards use the same) */
const formatPercent = value => `${(value * 100).toFixed(1)}%`

// Label, color and icon come only from the backend evidence_tier (issue 314)
const tierConfig = computed(() => getTierConfig(props.tier))

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

const sortedBreakdownEntries = computed(() =>
  // Only real numeric contributions may be shown as percentages
  Object.entries(props.breakdown ?? {})
    .filter(([, value]) => Number.isFinite(value))
    .sort(([, a], [, b]) => b - a)
)

const topSourceEntries = computed(() => sortedBreakdownEntries.value.slice(0, props.maxSources))
const remainingSourceCount = computed(() =>
  Math.max(0, sortedBreakdownEntries.value.length - props.maxSources)
)

const donutRadius = 40 // (96 - 8) / 2 - 4
const circumference = 2 * Math.PI * donutRadius

const getSourceDescription = (source, score) => {
  const percentage = formatPercent(score)
  const descriptions = {
    PanelApp: `Panel confidence score: ${percentage}`,
    HPO: `Phenotype association strength: ${percentage}`,
    PubTator: `Literature evidence score: ${percentage}`,
    Literature: `Publication support: ${percentage}`
  }
  return `${sourceDisplayName(source)}. ${descriptions[source] || `Evidence score: ${percentage}`}. Normalized source score (0–100%).`
}
</script>
