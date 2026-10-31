<script setup lang="ts">
// "Position statistics" under the protein domain plot: domain enrichment forest table and the
// hotspot-region table (twin of the scan track), each led by a generated plain-language sentence.
import { computed, ref } from 'vue'
import { Button } from '@/components/ui/button'
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow
} from '@/components/ui/table'
import type { usePositionStats } from '@/composables/usePositionStats'
import { DEFAULT_SEED, type DomainResult } from '@/types/positionStats'
import {
  domainSentence,
  featureName,
  formatOR,
  formatP,
  rangeText,
  scanSentence,
  PM1_CAVEAT
} from '@/utils/stats/sentences'
import { significanceColor } from '@/components/gene/variantColors'
import ForestCell from './ForestCell.vue'
import StatsMethods from './StatsMethods.vue'

const props = defineProps<{
  state: ReturnType<typeof usePositionStats>
  /** ClinVar annotation date for Methods */
  clinvarDate?: string
  /** Expected feature count, so the loading skeleton reserves the final height */
  rows?: number
}>()
// Refs at setup top level unwrap in the template.
const { status, message, linear, variantSet, minStars, retry } = props.state

const n = (x: number) => x.toLocaleString('en-US')
const domains = computed(() =>
  [...(linear.value?.domains ?? [])].sort((a, b) => a.q - b.q || a.p - b.p || a.start - b.start)
)
const scan = computed(() => linear.value?.scan ?? null)

// Shared log10 OR axis: covers every finite bound and 1, clamped to 0.01–100 (beyond: arrows).
const axis = computed(() => {
  const vals = domains.value.flatMap(d => [d.lo, d.hi, d.or]).filter(v => v > 0 && isFinite(v))
  const lmin = Math.max(-2, Math.min(-1, Math.floor(Math.log10(Math.min(1, ...vals)))))
  const lmax = Math.min(2, Math.max(1, Math.ceil(Math.log10(Math.max(1, ...vals)))))
  return { min: 10 ** lmin, max: 10 ** lmax }
})

const active = ref<DomainResult | null>(null)
const counts = (d: DomainResult) =>
  `${featureName(d)} (${rangeText(d.start, d.end)}): inside ${n(d.caseIn)} P/LP and ${n(d.ctrlIn)} gnomAD; outside ${n(d.caseOut)} P/LP and ${n(d.ctrlOut)} gnomAD.`
// Focusable rows announce the feature, its 2×2 counts, OR and q.
const rowLabel = (d: DomainResult) =>
  `${counts(d)} Odds ratio ${formatOR(d.or)} (95% CI ${formatOR(d.lo)} to ${formatOR(d.hi)}), q ${formatP(d.q)}.`
const detail = computed(() => {
  const d = active.value
  if (!d) return 'Hover or focus a row to see its counts inside and outside the feature.'
  return counts(d)
})
// Long feature lists (PKD1 has 44) show the first rows by q; significant rows are never hidden.
const ROW_LIMIT = 10
const showAll = ref(false)
const visible = computed(() => {
  const keep = Math.max(ROW_LIMIT, domains.value.filter(d => d.q < 0.05).length)
  return showAll.value ? domains.value : domains.value.slice(0, keep)
})
// Sticky first column: opaque, matching the row's hover/focus tint, and carrying the row's
// focus ring on its edge (an opaque sticky cell would otherwise hide the row's inset ring).
const STICKY =
  'sticky left-0 z-[1] bg-card group-hover:bg-[color-mix(in_oklch,var(--muted)_50%,var(--card))] group-focus-visible:bg-[color-mix(in_oklch,var(--muted)_50%,var(--card))]'
const FOCUS_EDGE =
  'group-focus-visible:shadow-[inset_2px_2px_0_var(--ring),inset_0_-2px_0_var(--ring)]'
const skeletonRows = computed(() => Math.min(Math.max(props.rows ?? 4, 1), ROW_LIMIT))
</script>

<template>
  <section class="mt-6 space-y-5 border-t pt-5" aria-labelledby="position-stats-title">
    <div>
      <h2 id="position-stats-title" class="text-lg font-semibold">Position statistics</h2>
      <p class="text-sm text-muted-foreground">
        Where ClinVar pathogenic missense variants fall along the protein, compared with gnomAD
        population missense variants.
      </p>
    </div>

    <div v-if="status === 'loading' || status === 'idle'" aria-busy="true" class="space-y-3">
      <p class="text-sm text-muted-foreground">
        {{
          status === 'loading'
            ? 'Computing statistics with gnomAD population variants…'
            : 'Statistics need ClinVar and UniProt data for this gene.'
        }}
      </p>
      <template v-if="status === 'loading'">
        <div class="h-4 w-3/4 animate-pulse rounded bg-muted" />
        <div class="space-y-2">
          <div class="h-9 animate-pulse rounded bg-muted/70" />
          <div v-for="i in skeletonRows" :key="i" class="h-10 animate-pulse rounded bg-muted/40" />
        </div>
      </template>
    </div>

    <div
      v-else-if="status === 'error'"
      role="alert"
      class="flex flex-wrap items-center gap-3 text-sm"
    >
      <p>Statistics could not be computed: {{ message }}</p>
      <Button variant="outline" size="sm" @click="retry">Try again</Button>
    </div>

    <p v-else-if="status === 'withheld' || status === 'too-few'" class="text-sm" role="status">
      {{ message }}
    </p>

    <template v-else-if="status === 'ready' && linear">
      <div class="space-y-2">
        <h3 class="text-xs font-semibold tracking-wide text-muted-foreground uppercase">
          Domain enrichment
        </h3>
        <p class="max-w-prose text-sm" data-testid="domain-sentence">
          {{ domainSentence(domains) }}
        </p>
        <Table v-if="domains.length" class="tabular-nums lg:max-w-4xl">
          <TableHeader>
            <TableRow class="hover:bg-transparent">
              <TableHead
                class="sticky left-0 z-[1] bg-[color-mix(in_oklch,var(--muted)_40%,var(--card))]"
                >Feature</TableHead
              >
              <TableHead class="text-right">P/LP</TableHead>
              <TableHead class="text-right">gnomAD</TableHead>
              <TableHead class="w-[180px] align-bottom">
                <span class="sr-only">Odds ratio plot, log scale</span>
                <ForestCell axis :min="axis.min" :max="axis.max" />
              </TableHead>
              <TableHead class="text-right whitespace-nowrap">OR (95% CI, unadjusted)</TableHead>
              <TableHead class="text-right">q</TableHead>
            </TableRow>
          </TableHeader>
          <TableBody>
            <TableRow
              v-for="d in visible"
              :key="d.key"
              :data-significant="d.q < 0.05 ? 'true' : 'false'"
              tabindex="0"
              :aria-label="rowLabel(d)"
              class="group focus-visible:bg-muted/50 focus-visible:ring-2 focus-visible:ring-ring focus-visible:outline-none focus-visible:ring-inset"
              @mouseenter="active = d"
              @mouseleave="active = null"
              @focus="active = d"
              @blur="active = null"
            >
              <TableCell :class="[STICKY, FOCUS_EDGE, 'min-w-40']">
                <span class="block" :class="d.q < 0.05 ? 'font-medium' : ''">{{ d.label }}</span>
                <span class="block text-xs text-muted-foreground">
                  {{ d.type }} · {{ rangeText(d.start, d.end) }}
                </span>
              </TableCell>
              <TableCell class="text-right">{{ n(d.caseIn) }}</TableCell>
              <TableCell class="text-right">{{ n(d.ctrlIn) }}</TableCell>
              <TableCell>
                <ForestCell
                  :min="axis.min"
                  :max="axis.max"
                  :or="d.or"
                  :lo="d.lo"
                  :hi="d.hi"
                  :significant="d.q < 0.05"
                />
              </TableCell>
              <TableCell class="text-right whitespace-nowrap">
                {{ formatOR(d.or) }}
                <span class="text-muted-foreground"
                  >({{ formatOR(d.lo) }}–{{ formatOR(d.hi) }})</span
                >
              </TableCell>
              <TableCell class="text-right" :class="d.q < 0.05 ? 'font-medium' : ''">
                {{ formatP(d.q) }}
              </TableCell>
            </TableRow>
          </TableBody>
        </Table>
        <Button
          v-if="visible.length < domains.length || showAll"
          variant="ghost"
          size="sm"
          class="-ml-2 h-8 px-2"
          :aria-expanded="showAll"
          @click="showAll = !showAll"
        >
          {{ showAll ? 'Show fewer features' : `Show all ${domains.length} features` }}
        </Button>
        <p
          v-if="domains.length"
          class="flex flex-wrap items-center gap-x-4 gap-y-1 text-xs text-muted-foreground"
          data-testid="forest-key"
        >
          <span class="inline-flex items-center gap-1.5">
            <svg width="10" height="10" viewBox="0 0 10 10" aria-hidden="true">
              <circle cx="5" cy="5" r="4" :fill="significanceColor('pathogenic')" />
            </svg>
            q &lt; 0.05 (Benjamini–Hochberg)
          </span>
          <span class="inline-flex items-center gap-1.5">
            <svg width="10" height="10" viewBox="0 0 10 10" aria-hidden="true">
              <circle
                cx="5"
                cy="5"
                r="3.5"
                fill="none"
                stroke="var(--muted-foreground)"
                stroke-width="1.5"
              />
            </svg>
            Not significant
          </span>
        </p>
        <p v-if="domains.length" class="text-xs text-muted-foreground sm:hidden">
          Scroll the table sideways for the odds-ratio plot.
        </p>
        <p
          v-if="domains.length"
          class="min-h-8 text-xs text-muted-foreground"
          data-testid="domain-detail"
        >
          {{ detail }}
        </p>
      </div>

      <div v-if="scan" class="space-y-2">
        <h3 class="text-xs font-semibold tracking-wide text-muted-foreground uppercase">
          Hotspot regions
        </h3>
        <p class="max-w-prose text-sm" data-testid="scan-sentence">{{ scanSentence(scan) }}</p>
        <Table v-if="scan.regions.length" class="tabular-nums lg:max-w-2xl">
          <TableHeader>
            <TableRow class="hover:bg-transparent">
              <TableHead
                class="sticky left-0 z-[1] bg-[color-mix(in_oklch,var(--muted)_40%,var(--card))]"
                >Residues</TableHead
              >
              <TableHead class="text-right">P/LP</TableHead>
              <TableHead class="text-right">gnomAD</TableHead>
              <TableHead class="text-right">ClinVar B/LB</TableHead>
              <TableHead class="text-right">Adjusted p</TableHead>
            </TableRow>
          </TableHeader>
          <TableBody>
            <TableRow v-for="r in scan.regions" :key="r.start" class="group">
              <TableCell :class="[STICKY, 'font-medium']">
                {{ rangeText(r.start, r.end) }}
              </TableCell>
              <TableCell class="text-right">{{ n(r.cases) }}</TableCell>
              <TableCell class="text-right">{{ n(r.ctrls) }}</TableCell>
              <TableCell class="text-right">{{ n(r.benign) }}</TableCell>
              <TableCell class="text-right">{{ formatP(r.adjP, scan.B) }}</TableCell>
            </TableRow>
          </TableBody>
        </Table>
        <p v-if="scan.regions.length" class="text-xs text-muted-foreground sm:hidden">
          Scroll the table sideways for all columns.
        </p>
      </div>
    </template>

    <div v-if="status !== 'idle'" class="space-y-2 border-t pt-3">
      <p class="text-xs text-muted-foreground" data-testid="pm1-caveat">{{ PM1_CAVEAT }}</p>
      <StatsMethods
        v-if="variantSet && status !== 'loading'"
        v-model:min-stars="minStars"
        kind="linear"
        hide-caveat
        :permutations="scan?.B ?? 10000"
        :seed="scan?.seed ?? DEFAULT_SEED"
        :versions="{ clinvar: clinvarDate }"
        :set="variantSet"
      />
    </div>
  </section>
</template>
