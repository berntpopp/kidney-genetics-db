<template>
  <div v-if="mouseData">
    <h3 class="mb-2 text-xs font-medium text-muted-foreground">Mouse phenotypes (MGI)</h3>

    <p
      v-if="mouseData.phenotype_count === 0 || mouseData.no_data_available"
      class="text-sm text-muted-foreground"
    >
      No kidney phenotypes in mouse models.
    </p>

    <div v-else class="flex flex-wrap items-center gap-1.5">
      <Chip
        kind="neutral"
        class="tabular-nums"
        :label="`${mouseData.phenotype_count} ${mouseData.phenotype_count === 1 ? 'phenotype' : 'phenotypes'}`"
        :tooltip="phenotypeTooltip"
      />
      <Chip
        v-for="z in zygosity"
        :key="z.key"
        kind="neutral"
        class="tabular-nums"
        :label="`${z.count} ${z.label}`"
        :tooltip="`${z.count} kidney phenotypes in ${z.label} knockout mice`"
      />
      <Chip
        v-if="mouseData.system_analysis?.renal_urinary"
        kind="neutral"
        class="tabular-nums"
        :label="`${mouseData.system_analysis.renal_urinary.phenotype_count} renal/urinary`"
        tooltip="Phenotypes in the renal/urinary system branch of the Mammalian Phenotype Ontology"
      />
    </div>
  </div>
</template>

<script setup>
import { computed } from 'vue'
import { Chip } from '@/components/shared'

const props = defineProps({
  mouseData: { type: Object, default: null }
})

const zygosity = computed(() =>
  [
    ['homozygous', 'homozygous'],
    ['heterozygous', 'heterozygous'],
    ['conditional', 'conditional']
  ]
    .map(([key, label]) => ({
      key,
      label,
      count: props.mouseData?.zygosity_analysis?.[key]?.phenotype_count ?? 0
    }))
    .filter(z => z.count > 0)
)

const phenotypeTooltip = computed(() => {
  const names = (props.mouseData?.phenotypes ?? []).slice(0, 5).map(p => p.name)
  const more = props.mouseData.phenotype_count - names.length
  return `Kidney-related phenotypes in mouse models${names.length ? `, e.g. ${names.join(', ')}` : ''}${more > 0 ? ` and ${more} more` : ''}`
})
</script>
