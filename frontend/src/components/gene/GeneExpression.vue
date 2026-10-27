<template>
  <div v-if="gtexData || descartesData">
    <h3 class="mb-2 text-xs font-medium text-muted-foreground">Kidney expression</h3>

    <p v-if="!chips.length" class="text-sm text-muted-foreground">
      No kidney expression data for this gene.
    </p>

    <div v-else class="flex flex-wrap items-center gap-1.5">
      <Chip
        v-for="chip in chips"
        :key="chip.label"
        kind="neutral"
        class="tabular-nums"
        :label="chip.label"
        :tooltip="chip.tooltip"
      />
    </div>
  </div>
</template>

<script setup>
import { computed } from 'vue'
import { Chip } from '@/components/shared'

const props = defineProps({
  gtexData: { type: Object, default: null },
  descartesData: { type: Object, default: null }
})

const formatTPM = tpm => {
  if (tpm == null) return 'n/a'
  if (tpm < 0.01) return '<0.01'
  if (tpm < 1) return tpm.toFixed(2)
  if (tpm < 100) return tpm.toFixed(1)
  return Math.round(tpm).toString()
}

const level = tpm => {
  if (tpm == null) return 'no data'
  if (tpm >= 100) return 'very high expression'
  if (tpm >= 10) return 'moderate expression'
  if (tpm >= 1) return 'low expression'
  if (tpm > 0) return 'very low expression'
  return 'not expressed'
}

const chips = computed(() => {
  const out = []
  const tissues = props.gtexData?.no_data_available ? {} : (props.gtexData?.tissues ?? {})
  for (const [key, name] of [
    ['Kidney_Cortex', 'Cortex'],
    ['Kidney_Medulla', 'Medulla']
  ]) {
    const tpm = tissues[key]?.median_tpm
    if (tpm == null) continue
    out.push({
      label: `GTEx ${name} ${formatTPM(tpm)} TPM`,
      tooltip: `GTEx v8 median expression in kidney ${name.toLowerCase()}: ${tpm.toFixed(2)} transcripts per million (${level(tpm)})`
    })
  }
  const d = props.descartesData?.no_data_available ? null : props.descartesData
  if (d?.kidney_tpm != null)
    out.push({
      label: `scRNA ${formatTPM(d.kidney_tpm)} TPM`,
      tooltip: `Descartes Human Cell Atlas, kidney single-cell expression: ${d.kidney_tpm.toFixed(2)} transcripts per million (${level(d.kidney_tpm)})`
    })
  if (d?.kidney_percentage != null)
    out.push({
      label: `${(d.kidney_percentage * 100).toFixed(2)}% of cells`,
      tooltip: `Descartes Human Cell Atlas: ${(d.kidney_percentage * 100).toFixed(2)}% of kidney cells express this gene`
    })
  return out
})
</script>
