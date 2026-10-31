<template>
  <div>
    <!-- Detailed card display for gene detail pages -->
    <Card class="h-full gap-4">
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
          <div class="flex flex-wrap justify-center gap-1.5">
            <Chip :tier="tier" />
            <RenalNeoplasiaChip v-if="renalNeoplasia" />
          </div>

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
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { Separator } from '@/components/ui/separator'
import { Chip, RenalNeoplasiaChip } from '@/components/shared'
import { getTierConfig } from '@/utils/evidenceTiers'
import { sourceDisplayName } from '@/utils/sources'
import { CircleHelp } from 'lucide-vue-next'

const props = defineProps({
  score: { type: Number, default: null },
  // Backend evidence_tier; the only source of the label (issue 314)
  tier: { type: String, default: null },
  breakdown: { type: Object, default: () => ({}) },
  renalNeoplasia: { type: Boolean, default: false }
})

// Round down: 99.97 must not read as a perfect 100.0
const floor1 = v => (Math.floor(v * 10) / 10).toFixed(1)
const formattedScore = computed(() => (props.score == null ? 'N/A' : floor1(props.score)))

/** One format for per-source scores everywhere (evidence cards use the same) */
const formatPercent = value => `${floor1(value * 100)}%`

// Label, color and icon come only from the backend evidence_tier (issue 314)
const tierConfig = computed(() => getTierConfig(props.tier))

const sortedBreakdownEntries = computed(() =>
  // Only real numeric contributions may be shown as percentages
  Object.entries(props.breakdown ?? {})
    .filter(([, value]) => Number.isFinite(value))
    .sort(([, a], [, b]) => b - a)
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
