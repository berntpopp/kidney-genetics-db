<template>
  <div v-if="clinvarData">
    <h3 class="mb-2 text-xs font-medium text-muted-foreground">Clinical variants (ClinVar)</h3>

    <p
      v-if="!clinvarData.total_variants || clinvarData.no_data_available"
      class="text-sm text-muted-foreground"
    >
      No ClinVar variants for {{ geneSymbol }}.
    </p>

    <div v-else class="flex flex-wrap items-center gap-1.5">
      <Chip
        kind="neutral"
        class="tabular-nums"
        :label="`${fmt(clinvarData.total_variants)} total`"
        :tooltip="totalTooltip"
      />
      <Chip
        v-for="chip in significanceChips"
        :key="chip.label"
        kind="neutral"
        class="tabular-nums"
        :class="STATUS_TONE_CLASSES[chip.tone]"
        :label="`${fmt(chip.count)} ${chip.label}`"
        :tooltip="chip.tooltip"
      />
      <Chip
        v-if="consequencesTooltip"
        kind="neutral"
        :icon="Dna"
        label="Consequences"
        :tooltip="consequencesTooltip"
      />
    </div>
  </div>
</template>

<script setup>
import { computed } from 'vue'
import { Dna } from 'lucide-vue-next'
import { Chip } from '@/components/shared'
import { STATUS_TONE_CLASSES } from '@/utils/status'
import { SIGNIFICANCE } from './variantColors'

const props = defineProps({
  clinvarData: { type: Object, default: null },
  geneSymbol: { type: String, required: true }
})

const fmt = n => Number(n ?? 0).toLocaleString()

const totalTooltip = computed(() => {
  const d = props.clinvarData
  const high =
    d.high_confidence_count ?? Math.round((d.total_variants * d.high_confidence_percentage) / 100)
  return `${fmt(d.total_variants)} variants submitted to ClinVar for ${props.geneSymbol}; ${fmt(high)} (${d.high_confidence_percentage}%) have a high-quality review (expert panel, or multiple submitters without conflicts)`
})

// Clinical significance is a risk axis, not evidence strength: status tones plus a label
const significanceChips = computed(() => {
  const d = props.clinvarData
  return [
    {
      label: 'P/LP',
      tone: SIGNIFICANCE.pathogenic.tone,
      count: (d.pathogenic_count ?? 0) + (d.likely_pathogenic_count ?? 0),
      tooltip: `Pathogenic ${fmt(d.pathogenic_count)}, likely pathogenic ${fmt(d.likely_pathogenic_count)}${d.pathogenic_percentage != null ? ` (${d.pathogenic_percentage}% of all variants)` : ''}`
    },
    {
      label: 'VUS',
      tone: SIGNIFICANCE.vus.tone,
      count: d.vus_count ?? 0,
      tooltip: SIGNIFICANCE.vus.description
    },
    {
      label: 'Conflicting',
      tone: SIGNIFICANCE.conflicting.tone,
      count: d.conflicting_count ?? 0,
      tooltip: SIGNIFICANCE.conflicting.description
    },
    {
      label: 'B/LB',
      tone: SIGNIFICANCE.benign.tone,
      count: (d.benign_count ?? 0) + (d.likely_benign_count ?? 0),
      tooltip: `Benign ${fmt(d.benign_count)}, likely benign ${fmt(d.likely_benign_count)}`
    }
  ].filter(c => c.count > 0)
})

const consequencesTooltip = computed(() => {
  const c = props.clinvarData?.consequence_categories
  if (!c) return ''
  const d = props.clinvarData
  return [
    c.truncating &&
      `Truncating ${fmt(c.truncating)} (${d.truncating_percentage}%; nonsense, frameshift, essential splice site)`,
    c.missense && `missense ${fmt(c.missense)} (${d.missense_percentage}%)`,
    c.synonymous && `synonymous ${fmt(c.synonymous)} (${d.synonymous_percentage}%)`,
    c.inframe && `in-frame ${fmt(c.inframe)}`,
    c.splice_region && `splice region ${fmt(c.splice_region)}`
  ]
    .filter(Boolean)
    .join('; ')
})
</script>
