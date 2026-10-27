<template>
  <div v-if="hpoData">
    <h3 class="mb-2 text-xs font-medium text-muted-foreground">Human phenotypes (HPO)</h3>

    <p
      v-if="hpoData.phenotype_count === 0 || hpoData.no_data_available"
      class="text-sm text-muted-foreground"
    >
      No HPO phenotypes for this gene.
    </p>

    <div v-else class="flex flex-wrap items-center gap-1.5">
      <Chip
        v-if="clinical?.primary"
        kind="neutral"
        data-testid="clinical-group"
        :label="groupLabel(clinical.primary)"
        :tooltip="clinicalTooltip"
      />
      <span
        v-if="clinical?.secondary?.length"
        data-testid="clinical-group-secondary"
        class="contents"
      >
        <span class="sr-only">Secondary clinical groups:</span>
        <Chip
          v-for="group in clinical.secondary"
          :key="group"
          kind="neutral"
          class="text-muted-foreground"
          :label="groupLabel(group)"
          :tooltip="`Secondary clinical group: ${groupLabel(group)} (at least half the evidence of the primary group)`"
        />
      </span>
      <Chip
        v-if="onset?.primary"
        kind="neutral"
        :label="`${ONSET[onset.primary] ?? onset.primary} onset`"
        :tooltip="`Most likely age of onset from the HPO annotations: ${ONSET[onset.primary] ?? onset.primary} (${pct(onset.scores?.[onset.primary])})`"
      />
      <Chip
        v-if="syndromic"
        kind="neutral"
        :label="syndromic.is_syndromic ? 'Syndromic' : 'Isolated'"
        :tooltip="syndromicTooltip"
      />
      <Chip
        kind="neutral"
        class="tabular-nums"
        :label="`${hpoData.kidney_phenotype_count} of ${hpoData.phenotype_count} kidney`"
        :tooltip="`${hpoData.kidney_phenotype_count} kidney-related phenotypes out of ${hpoData.phenotype_count} HPO phenotypes annotated to this gene`"
      />
      <Chip
        v-if="hpoData.disease_count > 0"
        kind="neutral"
        class="tabular-nums"
        :label="`${hpoData.disease_count} ${hpoData.disease_count === 1 ? 'disease' : 'diseases'}`"
        :tooltip="`${hpoData.disease_count} disease associations in HPO`"
      />
    </div>
  </div>
</template>

<script setup>
import { computed } from 'vue'
import { Chip } from '@/components/shared'

const props = defineProps({
  hpoData: { type: Object, default: null }
})

const GROUPS = {
  complement: 'Complement',
  cakut: 'CAKUT',
  glomerulopathy: 'Glomerulopathy',
  cyst_cilio: 'Cystic/Ciliopathy',
  tubulopathy: 'Tubulopathy',
  nephrolithiasis: 'Nephrolithiasis',
  neoplasia: 'Neoplasia'
}
const ONSET = { adult: 'Adult', pediatric: 'Pediatric', congenital: 'Congenital' }

const groupLabel = group => GROUPS[group] ?? group
const pct = value => (value == null ? 'n/a' : `${(value * 100).toFixed(0)}%`)

const clinical = computed(() => props.hpoData?.classification?.clinical_group)
const onset = computed(() => props.hpoData?.classification?.onset_group)
const syndromic = computed(() => props.hpoData?.classification?.syndromic_assessment)

const clinicalTooltip = computed(() => {
  const c = clinical.value
  // v1 annotations (no method) keep their old score until the next HPO run
  const scoreLabel = c.method ? 'Share of kidney-group evidence' : 'Score (pre-v2 classification)'
  const secondary = c.secondary?.length
    ? ` Secondary: ${c.secondary.map(groupLabel).join(', ')}.`
    : ''
  return `Clinical group: ${groupLabel(c.primary)}. ${scoreLabel}: ${pct(c.scores?.[c.primary])}.${secondary}`
})

const syndromicTooltip = computed(() => {
  const s = syndromic.value
  const extra = s.extra_renal_categories?.length
    ? ` Extra-renal: ${s.extra_renal_categories.join(', ')}.`
    : ''
  return `${s.is_syndromic ? 'Syndromic kidney disease' : 'Isolated kidney phenotype'}.${extra}`
})
</script>
