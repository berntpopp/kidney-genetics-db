<template>
  <div v-if="gnomadData">
    <h3 class="mb-2 text-xs font-medium text-muted-foreground">Constraint scores (gnomAD)</h3>

    <p v-if="gnomadData.constraint_not_available" class="text-sm text-muted-foreground">
      No gnomAD constraint scores for this gene.
    </p>

    <div v-else class="flex flex-wrap gap-1.5">
      <Chip
        kind="neutral"
        class="tabular-nums"
        :label="`pLI ${fixed(gnomadData.pli, 2)}`"
        :tooltip="`Probability of loss-of-function intolerance (pLI) ${fixed(gnomadData.pli, 4)}: ${pliText(gnomadData.pli)}. Range 0–1; ≥ 0.9 is intolerant.`"
      />
      <Chip
        kind="neutral"
        class="tabular-nums"
        :label="`Missense Z ${fixed(gnomadData.mis_z, 2)}`"
        :tooltip="`Missense Z-score ${fixed(gnomadData.mis_z, 2)}: ${zText(gnomadData.mis_z)}. Higher means fewer missense variants than expected.`"
      />
      <Chip
        v-if="gnomadData.lof_z != null"
        kind="neutral"
        class="tabular-nums"
        :label="`LoF Z ${fixed(gnomadData.lof_z, 2)}`"
        :tooltip="`Loss-of-function Z-score ${fixed(gnomadData.lof_z, 2)}: ${zText(gnomadData.lof_z)}. Higher means fewer loss-of-function variants than expected.`"
      />
    </div>
  </div>
</template>

<script setup>
import { Chip } from '@/components/shared'

defineProps({
  gnomadData: { type: Object, default: null }
})

const fixed = (value, digits) => (value == null ? 'n/a' : Number(value).toFixed(digits))

const pliText = pli => {
  if (pli == null) return 'no data'
  if (pli >= 0.9) return 'highly intolerant of loss of function'
  if (pli >= 0.5) return 'moderately intolerant of loss of function'
  return 'tolerant of loss of function'
}

const zText = z => {
  if (z == null) return 'no data'
  if (z >= 3.09) return 'extremely constrained (p < 0.001)'
  if (z >= 2) return 'constrained'
  if (z >= 0) return 'near expectation'
  return 'more variation than expected'
}
</script>
