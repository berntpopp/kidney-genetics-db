<script setup lang="ts">
// "Spatial statistics" under the 3D viewer: clustering of pathogenic residues against the
// permutation null (histogram + table twin) and the 3D hotspot clusters (click to zoom and filter).
import { computed } from 'vue'
import { Button } from '@/components/ui/button'
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow
} from '@/components/ui/table'
import { significanceColor } from '@/components/gene/variantColors'
import type { usePositionStats } from '@/composables/usePositionStats'
import { DEFAULT_SEED } from '@/types/positionStats'
import {
  clusterSentence,
  formatP,
  hotspotSentence,
  PM1_CAVEAT,
  residueRanges
} from '@/utils/stats/sentences'
import StatsMethods from './StatsMethods.vue'

const props = defineProps<{
  state: ReturnType<typeof usePositionStats>
  /** The 3D tab's model load state */
  modelStatus: 'loading' | 'ready' | 'empty' | 'error' | 'nowebgl'
  model: { uniprotStart: number; uniprotEnd: number; label?: string } | null
  length?: number
  clinvarDate?: string
  /** Residues of the cluster currently filtering the variant list */
  selected?: number[] | null
}>()
const emit = defineEmits<{ 'select-cluster': [residues: number[]] }>()

const { status, message, spatial, spatialMessage, variantSet, minStars, retry } = props.state
const NO_MODEL = 'No full-length AlphaFold model for this protein, so no 3D statistics.'
const n = (x: number) => x.toLocaleString('en-US')
const A = (x: number) => `${x.toFixed(1)} Å`

const fullLength = computed(
  () => !!props.model && props.model.uniprotStart === 1 && props.model.uniprotEnd === props.length
)
// One message per state; null = results (or computing) below
const notice = computed(() => {
  if (props.modelStatus === 'empty' || (props.modelStatus === 'ready' && !fullLength.value)) {
    return NO_MODEL
  }
  if (props.modelStatus === 'error' || props.modelStatus === 'nowebgl') {
    return '3D statistics need the AlphaFold model, which could not be shown here.'
  }
  if (status.value === 'idle') return 'Statistics need ClinVar and UniProt data for this gene.'
  if (status.value === 'withheld' || status.value === 'too-few') return message.value
  if (status.value === 'ready' && !spatial.value) return spatialMessage.value || NO_MODEL
  return null
})
const error = computed(() => (notice.value ? '' : status.value === 'error' ? message.value : ''))
const computing = computed(() => !notice.value && !error.value && status.value === 'loading')
const cluster = computed(() => spatial.value?.cluster ?? null)
const hotspots = computed(() => spatial.value?.hotspots ?? null)
const selectedKey = computed(() => props.selected?.join(',') ?? '')

// Histogram geometry (SVG user units; the SVG scales down on narrow screens, never up)
const W = 340
const H = 156
const M = { top: 22, right: 12, bottom: 34, left: 12 }
const chart = computed(() => {
  const c = cluster.value
  if (!c) return null
  const first = c.histogram[0]!.x0
  const last = c.histogram.at(-1)!.x1
  const pad = (Math.max(last, c.observed) - Math.min(first, c.observed)) * 0.04 || 1
  const d0 = Math.min(first, c.observed) - pad
  const d1 = Math.max(last, c.observed) + pad
  const x = (v: number) => M.left + ((v - d0) / (d1 - d0)) * (W - M.left - M.right)
  const base = H - M.bottom
  const top = Math.max(1, ...c.histogram.map(b => b.n))
  const bars = c.histogram
    .filter(b => b.n > 0)
    .map(b => {
      const w = Math.max(1, Math.min(24, x(b.x1) - x(b.x0) - 2)) // 2px gaps, never wider than 24
      const h = (b.n / top) * (base - M.top)
      return { x: (x(b.x0) + x(b.x1)) / 2 - w / 2, y: base - h, w, h, label: b }
    })
  const raw = (d1 - d0) / 5
  const step = [0.5, 1, 2, 5, 10, 20].find(s => s >= raw) ?? 50
  const ticks: number[] = []
  for (let t = Math.ceil(d0 / step) * step; t <= d1; t += step) ticks.push(t)
  const ox = x(c.observed)
  return {
    bars,
    base,
    ticks: ticks.map(t => ({ t, x: x(t) })),
    span: { x: x(c.nullLo), w: x(c.nullHi) - x(c.nullLo) },
    ox,
    // Keep the observed label inside the chart
    anchor: ox < W * 0.25 ? 'start' : ox > W * 0.75 ? 'end' : 'middle'
  }
})
const chartLabel = computed(() => {
  const c = cluster.value
  if (!c) return ''
  return `Histogram of mean pairwise Cα distance in ${n(c.B)} label permutations, centred on ${A(c.nullMean)} with 95% between ${A(c.nullLo)} and ${A(c.nullHi)}; observed ${A(c.observed)}.`
})
const pathogenic = significanceColor('pathogenic')
const clusterRows = computed(() => {
  const c = cluster.value
  if (!c) return []
  return [
    ['Observed', A(c.observed)],
    ['Null mean', A(c.nullMean)],
    ['Null 95% interval', `${c.nullLo.toFixed(1)}–${A(c.nullHi)}`],
    ['p (one-sided)', formatP(c.p, c.B)],
    ['Permutations (B)', n(c.B)],
    ['Seed', String(c.seed)]
  ]
})
</script>

<template>
  <section class="mt-6 space-y-5 border-t pt-5" aria-labelledby="spatial-stats-title">
    <div>
      <h3 id="spatial-stats-title" class="text-base font-semibold">Spatial statistics</h3>
      <p class="text-sm text-muted-foreground">
        Whether ClinVar pathogenic missense variants cluster in the folded protein, compared with
        gnomAD population missense variants. Only residues with pLDDT ≥ 70 are used.
      </p>
    </div>

    <p v-if="notice" class="text-sm" role="status" data-testid="spatial-notice">{{ notice }}</p>
    <div v-else-if="error" role="alert" class="flex flex-wrap items-center gap-3 text-sm">
      <p>3D statistics could not be computed: {{ error }}</p>
      <Button variant="outline" size="sm" @click="retry">Try again</Button>
    </div>
    <!-- Skeleton mirrors the result layout so nothing moves when the numbers arrive -->
    <div v-else-if="computing" aria-busy="true" class="space-y-5">
      <div class="space-y-2">
        <p class="text-sm text-muted-foreground">
          Computing 3D statistics with gnomAD population variants…
        </p>
        <div class="aspect-[340/156] w-full max-w-[340px] animate-pulse rounded bg-muted/50" />
        <div class="h-[230px] animate-pulse rounded bg-muted/40 sm:max-w-sm" />
      </div>
      <div class="space-y-2">
        <div class="h-4 w-2/3 animate-pulse rounded bg-muted" />
        <div class="h-[90px] animate-pulse rounded bg-muted/40 lg:max-w-3xl" />
      </div>
    </div>
    <template v-else-if="spatial">
      <div class="space-y-2">
        <h4 class="text-sm font-semibold">Clustering</h4>
        <template v-if="cluster && chart">
          <p class="max-w-prose text-sm" data-testid="cluster-sentence">
            {{ clusterSentence(cluster) }}
          </p>
          <figure class="max-w-[340px] space-y-1.5">
            <svg
              :viewBox="`0 0 ${W} ${H}`"
              class="block h-auto w-full overflow-visible"
              role="img"
              :aria-label="chartLabel"
            >
              <rect
                :x="chart.span.x"
                :y="M.top"
                :width="chart.span.w"
                :height="chart.base - M.top"
                class="fill-muted-foreground/15"
                data-testid="null-span"
              />
              <rect
                v-for="b in chart.bars"
                :key="b.label.x0"
                :x="b.x"
                :y="b.y"
                :width="b.w"
                :height="b.h"
                class="fill-muted-foreground/55"
              />
              <line
                :x1="M.left"
                :x2="W - M.right"
                :y1="chart.base"
                :y2="chart.base"
                class="stroke-border"
                stroke-width="1"
              />
              <g v-for="t in chart.ticks" :key="t.t" class="fill-muted-foreground text-[12px]">
                <line
                  :x1="t.x"
                  :x2="t.x"
                  :y1="chart.base"
                  :y2="chart.base + 4"
                  class="stroke-border"
                />
                <text :x="t.x" :y="chart.base + 16" text-anchor="middle" class="tabular-nums">
                  {{ t.t }}
                </text>
              </g>
              <text
                :x="W / 2"
                :y="H - 2"
                text-anchor="middle"
                class="fill-muted-foreground text-[12px]"
              >
                Mean pairwise Cα distance (Å)
              </text>
              <line
                :x1="chart.ox"
                :x2="chart.ox"
                :y1="M.top - 4"
                :y2="chart.base"
                :stroke="pathogenic"
                stroke-width="2"
                :aria-label="`Observed ${A(cluster.observed)}`"
                data-testid="observed-line"
              />
              <text
                :x="chart.ox"
                :y="M.top - 8"
                :text-anchor="chart.anchor"
                class="fill-foreground text-[12px] font-medium tabular-nums"
              >
                Observed {{ A(cluster.observed) }}
              </text>
            </svg>
            <figcaption
              class="flex flex-wrap gap-x-4 gap-y-1 text-xs text-muted-foreground"
              aria-hidden="true"
            >
              <span class="inline-flex items-center gap-1.5">
                <span class="size-2.5 rounded-sm bg-muted-foreground/55" />
                {{ n(cluster.B) }} label permutations
              </span>
              <span class="inline-flex items-center gap-1.5">
                <span class="size-2.5 rounded-sm bg-muted-foreground/15 ring-1 ring-border" />
                95% of permutations
              </span>
              <span class="inline-flex items-center gap-1.5">
                <span class="h-2.5 w-0.5" :style="{ backgroundColor: pathogenic }" />
                Observed ({{ n(cluster.nCaseResidues) }} pathogenic residues)
              </span>
            </figcaption>
          </figure>
          <!-- Table twin, one statistic per row so it fits a phone without scrolling -->
          <Table class="tabular-nums sm:max-w-sm">
            <TableHeader>
              <TableRow class="hover:bg-transparent">
                <TableHead>Mean pairwise Cα distance</TableHead>
                <TableHead class="text-right">Value</TableHead>
              </TableRow>
            </TableHeader>
            <TableBody>
              <TableRow v-for="r in clusterRows" :key="r[0]">
                <TableCell>{{ r[0] }}</TableCell>
                <TableCell class="text-right whitespace-nowrap">{{ r[1] }}</TableCell>
              </TableRow>
            </TableBody>
          </Table>
        </template>
        <p v-else class="text-sm" data-testid="cluster-sentence">
          Fewer than 3 pathogenic missense residues have pLDDT ≥ 70, too few for a meaningful
          clustering test.
        </p>
      </div>

      <div v-if="hotspots" class="space-y-2">
        <h4 class="text-sm font-semibold">3D hotspots</h4>
        <p class="max-w-prose text-sm" data-testid="hotspot-sentence">
          {{ hotspotSentence(hotspots) }}
        </p>
        <template v-if="hotspots.clusters.length">
          <p class="text-xs text-muted-foreground">
            Select a hotspot to zoom the viewer to it and list its variants.
          </p>
          <Table class="tabular-nums lg:max-w-3xl">
            <TableHeader>
              <TableRow class="hover:bg-transparent">
                <TableHead>Residues</TableHead>
                <TableHead class="text-right">P/LP</TableHead>
                <TableHead class="text-right">gnomAD</TableHead>
                <TableHead class="text-right whitespace-normal">Adjusted p</TableHead>
              </TableRow>
            </TableHeader>
            <TableBody>
              <TableRow
                v-for="(c, i) in hotspots.clusters"
                :key="c.residues.join(',')"
                :class="selectedKey === c.residues.join(',') && 'bg-muted'"
              >
                <TableCell class="min-w-24 whitespace-normal">
                  <button
                    type="button"
                    class="flex items-start gap-2 rounded-sm text-left focus-visible:ring-2 focus-visible:ring-ring focus-visible:outline-none"
                    :aria-pressed="selectedKey === c.residues.join(',')"
                    :aria-label="`Hotspot ${i + 1}, residues ${residueRanges(c.residues)}: zoom the 3D view and list its variants`"
                    data-testid="hotspot-cluster"
                    @click="emit('select-cluster', c.residues)"
                  >
                    <span
                      class="mt-1.5 size-2.5 shrink-0 rounded-full"
                      :style="{ backgroundColor: pathogenic }"
                      aria-hidden="true"
                    />
                    <span>
                      <span class="block font-medium text-primary hover:underline">
                        <template v-for="(r, j) in residueRanges(c.residues).split(', ')" :key="r"
                          >{{ j ? ', ' : ''
                          }}<span class="whitespace-nowrap">{{ r }}</span></template
                        >
                      </span>
                      <span class="block text-xs text-muted-foreground">
                        {{ c.residues.length }} residue{{ c.residues.length === 1 ? '' : 's' }}
                      </span>
                    </span>
                  </button>
                </TableCell>
                <TableCell class="text-right">{{ n(c.cases) }}</TableCell>
                <TableCell class="text-right">{{ n(c.ctrls) }}</TableCell>
                <TableCell class="text-right whitespace-nowrap">
                  {{ formatP(c.adjP, hotspots.B) }}
                </TableCell>
              </TableRow>
            </TableBody>
          </Table>
          <p class="text-xs text-muted-foreground">
            P/LP and gnomAD counts are within {{ hotspots.radius }} Å of the significant residues;
            nearby hotspots can share variants. The variant list after selecting a hotspot shows
            only variants at the significant residues themselves, so its count differs from these
            sphere counts.
          </p>
        </template>
      </div>
    </template>

    <div v-if="status !== 'idle'" class="space-y-2 border-t pt-3">
      <p class="text-xs text-muted-foreground" data-testid="pm1-caveat">{{ PM1_CAVEAT }}</p>
      <StatsMethods
        v-if="variantSet && status !== 'loading'"
        v-model:min-stars="minStars"
        kind="3d"
        hide-caveat
        :permutations="cluster?.B ?? 10000"
        :hotspot-permutations="hotspots?.B ?? 2000"
        :seed="cluster?.seed ?? hotspots?.seed ?? DEFAULT_SEED"
        :versions="{ clinvar: clinvarDate, alphafold: model?.label }"
        :set="variantSet"
      />
    </div>
  </section>
</template>
