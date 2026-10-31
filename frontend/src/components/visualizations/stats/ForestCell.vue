<script setup lang="ts">
// One forest-plot cell on a log10 odds-ratio axis shared by every row (min/max are OR values).
// With `axis`, it draws the shared tick labels and the labelled OR = 1 hairline instead of a point.
import { computed } from 'vue'
import { significanceColor } from '@/components/gene/variantColors'
import { formatOR } from '@/utils/stats/sentences'

const props = defineProps<{
  min: number
  max: number
  or?: number
  lo?: number
  hi?: number
  significant?: boolean
  axis?: boolean
}>()

const W = 168
const PAD = 8
const H = computed(() => (props.axis ? 28 : 20))
const lmin = computed(() => Math.log10(props.min))
const lmax = computed(() => Math.log10(props.max))
// Off-scale (0, ∞ or beyond the shared domain) values pin to the edge and draw an arrow.
const x = (v: number) => {
  const l = v <= 0 ? -Infinity : Math.log10(v)
  const t = (Math.min(Math.max(l, lmin.value), lmax.value) - lmin.value) / (lmax.value - lmin.value)
  return PAD + t * (W - 2 * PAD)
}
const offLeft = (v: number) => v <= 0 || Math.log10(v) < lmin.value
const offRight = (v: number) => !Number.isFinite(v) || Math.log10(v) > lmax.value

const ticks = computed(() => {
  const out: number[] = []
  for (let e = Math.ceil(lmin.value); e <= Math.floor(lmax.value); e++)
    out.push(Number((10 ** e).toPrecision(1)))
  return out
})
const color = computed(() =>
  props.significant ? significanceColor('pathogenic') : 'var(--muted-foreground)'
)
const mid = computed(() => H.value / 2)
const label = computed(() =>
  props.or === undefined
    ? ''
    : `Odds ratio ${formatOR(props.or)}, 95% CI ${formatOR(props.lo ?? 0)} to ${formatOR(props.hi ?? Infinity)}`
)
</script>

<template>
  <svg
    v-if="axis"
    :width="W"
    :height="H"
    :viewBox="`0 0 ${W} ${H}`"
    class="block overflow-visible"
    aria-hidden="true"
  >
    <text
      v-for="t in ticks"
      :key="t"
      :x="x(t)"
      :y="H - 2"
      text-anchor="middle"
      class="fill-muted-foreground text-[10px] tabular-nums"
    >
      {{ t }}
    </text>
    <text :x="x(1)" y="9" text-anchor="middle" class="fill-muted-foreground text-[10px]">
      no enrichment
    </text>
    <line
      :x1="x(1)"
      :x2="x(1)"
      y1="11"
      :y2="H - 11"
      stroke="var(--muted-foreground)"
      stroke-width="1"
    />
  </svg>
  <svg
    v-else
    :width="W"
    :height="H"
    :viewBox="`0 0 ${W} ${H}`"
    class="block overflow-visible"
    role="img"
    :aria-label="label"
  >
    <!-- Dashed muted-foreground: ≥ 3:1 on the card in both themes (WCAG 1.4.11) -->
    <line
      :x1="x(1)"
      :x2="x(1)"
      y1="0"
      :y2="H"
      stroke="var(--muted-foreground)"
      stroke-width="1"
      stroke-dasharray="2 2"
    />
    <template v-if="or !== undefined">
      <line
        :x1="x(lo ?? 0)"
        :x2="x(hi ?? Infinity)"
        :y1="mid"
        :y2="mid"
        :stroke="color"
        stroke-width="2"
      />
      <path
        v-if="offLeft(lo ?? 0)"
        :d="`M${PAD - 6},${mid} l6,-4 v8 z`"
        :fill="color"
        data-arrow="left"
      />
      <path
        v-if="offRight(hi ?? Infinity)"
        :d="`M${W - PAD + 6},${mid} l-6,-4 v8 z`"
        :fill="color"
        data-arrow="right"
      />
      <!-- An odds ratio of 0 or ∞ has no point on the axis; the arrow carries it.
           Filled = significant, hollow = not: shape, not only red vs grey (dark-mode protan ΔE 6.7) -->
      <circle
        v-if="!offLeft(or) && !offRight(or)"
        :cx="x(or)"
        :cy="mid"
        r="4"
        :fill="significant ? color : 'var(--card)'"
        :stroke="significant ? 'var(--card)' : color"
        :stroke-width="significant ? 1 : 1.5"
        :data-filled="significant ? 'true' : 'false'"
      />
    </template>
  </svg>
</template>
