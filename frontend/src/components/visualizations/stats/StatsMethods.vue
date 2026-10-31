<script setup lang="ts">
// Methods disclosure shared by the linear (Protein Domains) and 3D statistics sections.
import { computed, ref } from 'vue'
import { ChevronDown } from 'lucide-vue-next'
import { Button } from '@/components/ui/button'
import { Collapsible, CollapsibleContent, CollapsibleTrigger } from '@/components/ui/collapsible'
import { Switch } from '@/components/ui/switch'
import type { VariantSetSummary } from '@/types/positionStats'
import { PM1_CAVEAT } from '@/utils/stats/sentences'

const props = defineProps<{
  kind: 'linear' | '3d'
  /** Permutation count B */
  permutations: number
  seed: number
  /** Hotspot permutation count (3D only) */
  hotspotPermutations?: number
  versions: { clinvar?: string; alphafold?: string }
  set?: VariantSetSummary | null
  /** The parent section already shows the PM1 caveat in every state */
  hideCaveat?: boolean
}>()
const minStars = defineModel<number>('minStars', { required: true })

const open = ref(false)
const n = (x: number) => x.toLocaleString('en-US')
const includeZeroStar = computed({
  get: () => minStars.value === 0,
  set: v => (minStars.value = v ? 0 : 1)
})
const clinvarDate = computed(() =>
  props.versions.clinvar ? props.versions.clinvar.slice(0, 10) : 'unknown date'
)
const dropped = computed(() => {
  const s = props.set
  if (!s) return []
  const lines = [
    { name: 'ClinVar', d: s.dropped.clinvar, c: s.checked.clinvar, u: s.unplaced?.clinvar ?? 0 },
    { name: 'gnomAD', d: s.dropped.gnomad, c: s.checked.gnomad, u: s.unplaced?.gnomad ?? 0 }
  ].map(
    r =>
      `${n(r.d)} of ${n(r.c)} ${r.name} missense variants did not match the UniProt sequence and were excluded` +
      (r.u
        ? `; ${n(r.u)} lie in a segment absent from the canonical protein and were not placed.`
        : '.')
  )
  // Positions numbered on another isoform or RefSeq protein are mapped onto canonical UniProt.
  const iso = s.isoforms
  const mapped = [
    ...Object.entries(iso?.clinvar ?? {})
      .filter(([, frame]) => frame)
      .map(([tx, frame]) => (frame === tx ? `ClinVar ${tx}` : `ClinVar ${tx} (via ${frame})`)),
    ...(iso?.gnomad ? [`gnomAD MANE transcript (via ${iso.gnomad})`] : [])
  ]
  if (mapped.length)
    lines.push(`Positions mapped onto the canonical UniProt sequence from: ${mapped.join(', ')}.`)
  return lines
})
const switchId = computed(() => `stats-zero-star-${props.kind}`)
</script>

<template>
  <div class="space-y-2">
    <p v-if="!hideCaveat" class="text-xs text-muted-foreground">{{ PM1_CAVEAT }}</p>
    <Collapsible v-model:open="open">
      <CollapsibleTrigger as-child>
        <Button variant="ghost" size="sm" class="-ml-2 h-8 gap-1 px-2 text-sm">
          Methods
          <ChevronDown
            class="size-4 transition-transform duration-200"
            :class="open ? 'rotate-180' : ''"
            aria-hidden="true"
          />
        </Button>
      </CollapsibleTrigger>
      <CollapsibleContent>
        <dl
          class="grid max-w-3xl gap-x-6 gap-y-2 pt-2 text-sm sm:grid-cols-[10rem_1fr] [&_dd]:text-muted-foreground [&_dt]:font-medium"
        >
          <dt>Cases</dt>
          <dd>
            ClinVar pathogenic and likely pathogenic missense variants with
            {{ minStars === 0 ? 'any review status' : 'at least 1 review star' }}; one ClinVar
            record (VCV) counts once.
          </dd>
          <dt>Controls</dt>
          <dd>
            gnomAD v4.1 missense variants passing filters with allele count above 0; one gnomAD
            variant counts once. Variants also listed as pathogenic in ClinVar are kept, which makes
            the tests conservative.
          </dd>
          <dt>Sequence check</dt>
          <dd>
            <template v-if="dropped.length">
              <span v-for="line in dropped" :key="line" class="block">{{ line }}</span>
            </template>
            <template v-else>Reference amino acids are checked against UniProt.</template>
            Statistics are withheld when more than 10% of either source fails the check.
          </dd>
          <template v-if="kind === 'linear'">
            <dt>Domains</dt>
            <dd>
              One two-sided Fisher's exact test per UniProt feature (variants inside vs outside),
              with the conditional maximum-likelihood odds ratio and exact 95% CI. q values are
              Benjamini–Hochberg adjusted across all features of the protein.
            </dd>
            <dt>Hotspot scan</dt>
            <dd>
              15-residue windows, step 1. Each window gets a one-sided hypergeometric p for
              pathogenic variants among all variants in it. The family-wise adjusted p is the share
              of label permutations (positions fixed, B = {{ n(permutations) }}, seed {{ seed }})
              whose smallest window p is at least as small. Windows with adjusted p &lt; 0.05 are
              merged into regions; the ClinVar benign and likely benign missense count is shown for
              each.
            </dd>
          </template>
          <template v-else>
            <dt>Clustering</dt>
            <dd>
              Mean pairwise Cα distance among distinct pathogenic residues with pLDDT ≥ 70, compared
              with label permutations over the same residues (one-sided, B = {{ n(permutations) }},
              seed {{ seed }}).
            </dd>
            <dt>Hotspots</dt>
            <dd>
              For each residue with pLDDT ≥ 70, a one-sided hypergeometric p for pathogenic variants
              within 10 Å (Cα), family-wise adjusted by min-p permutation (B =
              {{ n(hotspotPermutations ?? permutations) }}). Significant residues within 10 Å of
              each other form a cluster. Counts are over the tested 10 Å spheres, so overlapping
              clusters can share variants.
            </dd>
          </template>
          <dt>Data</dt>
          <dd>
            ClinVar annotation {{ clinvarDate }} · gnomAD v4.1<template v-if="versions.alphafold">
              · AlphaFold {{ versions.alphafold }}</template
            >
          </dd>
        </dl>
        <div class="flex items-center gap-2 pt-3">
          <Switch :id="switchId" v-model="includeZeroStar" />
          <label :for="switchId" class="text-sm"
            >Include ClinVar records without review stars</label
          >
        </div>
      </CollapsibleContent>
    </Collapsible>
  </div>
</template>
