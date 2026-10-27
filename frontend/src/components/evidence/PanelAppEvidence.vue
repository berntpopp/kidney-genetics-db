<template>
  <EvidenceList title="Panels" :items="panels" :item-key="p => `${p.region}:${p.id}`">
    <template #default="{ item: p }">
      <a
        v-if="panelUrl(p)"
        :href="panelUrl(p)"
        target="_blank"
        rel="noopener noreferrer"
        class="rounded-sm text-foreground underline-offset-4 hover:underline focus-visible:ring-2 focus-visible:ring-ring focus-visible:outline-none"
        >{{ p.name }}<span class="sr-only"> (opens in a new tab)</span></a
      >
      <span v-else class="text-foreground">{{ p.name }}</span>
      <span class="ml-2 text-xs text-muted-foreground">
        {{ REGION_NAMES[p.region] ?? p.region
        }}<template v-if="p.version"> · v{{ p.version }}</template>
      </span>
    </template>
  </EvidenceList>

  <EvidenceList title="Phenotypes" :items="phenotypes" :item-key="ph => ph.name">
    <template #default="{ item: ph }">
      <OntologyTerm v-if="ph.omim" :id="ph.omim" source="OMIM" :name="ph.name" />
      <span v-else class="text-foreground">{{ ph.name }}</span>
    </template>
  </EvidenceList>

  <section v-if="levels.length || modes.length" class="space-y-2">
    <h4 class="text-sm font-medium text-foreground">Rating and inheritance</h4>
    <div v-if="levels.length" class="flex flex-wrap gap-1.5">
      <Chip
        v-for="level in levels"
        :key="level"
        kind="neutral"
        :label="LEVELS[level]?.label ?? `Level ${level}`"
        :tooltip="LEVELS[level]?.tooltip ?? `PanelApp evidence level ${level}`"
      />
    </div>
    <ul v-if="modes.length" class="space-y-1 text-sm text-muted-foreground">
      <li v-for="mode in modes" :key="mode.raw" :title="mode.raw">{{ mode.label }}</li>
    </ul>
  </section>
</template>

<script setup>
import { computed } from 'vue'
import { Chip, OntologyTerm } from '@/components/shared'
import EvidenceList from './EvidenceList.vue'
import { parsePanelAppPhenotypes, uniquePanels } from './evidenceMeta'

const props = defineProps({
  evidenceData: { type: Object, required: true },
  sourceName: { type: String, default: 'PanelApp' }
})

const REGION_NAMES = { UK: 'Genomics England', Australia: 'PanelApp Australia' }

// PanelApp confidence ratings ("traffic lights"); a rating, not a ClinGen-style classification
const LEVELS = {
  3: { label: 'Green (3)', tooltip: 'Green: diagnostic-grade gene on at least one panel' },
  2: { label: 'Amber (2)', tooltip: 'Amber: moderate evidence on at least one panel' },
  1: { label: 'Red (1)', tooltip: 'Red: low evidence on the panels' },
  0: { label: 'No rating (0)', tooltip: 'Not rated by the panel reviewers' }
}

const panels = computed(() =>
  uniquePanels(props.evidenceData?.panels).sort((a, b) => a.name.localeCompare(b.name))
)
const phenotypes = computed(() => parsePanelAppPhenotypes(props.evidenceData?.phenotypes))
const levels = computed(() =>
  [...new Set((props.evidenceData?.evidence_levels ?? []).map(String))].sort().reverse()
)
// PanelApp's fixed mode-of-inheritance vocabulary in the wording the GenCC/ClinGen cards use;
// the raw value stays in the tooltip, and unknown values pass through unchanged
const MOI_LABELS = [
  [/^MONOALLELIC.*NOT imprinted/i, 'Autosomal dominant (monoallelic)'],
  [/^MONOALLELIC.*maternally imprinted/i, 'Autosomal dominant, maternally imprinted'],
  [/^MONOALLELIC.*paternally imprinted/i, 'Autosomal dominant, paternally imprinted'],
  [/^MONOALLELIC.*imprinted status unknown/i, 'Autosomal dominant, imprinting unknown'],
  [/^BIALLELIC/i, 'Autosomal recessive (biallelic)'],
  [/^BOTH.*more SEVERE/i, 'Autosomal dominant or recessive (biallelic more severe)'],
  [/^BOTH/i, 'Autosomal dominant or recessive'],
  [/^X-LINKED.*biallelic mutations in females/i, 'X-linked recessive'],
  [/^X-LINKED.*monoallelic mutations in females/i, 'X-linked, females may be affected'],
  [/^MITOCHONDRIAL/i, 'Mitochondrial'],
  [/^Other/i, 'Other'],
  [/^Unknown$/i, 'Unknown']
]
const moiLabel = raw => MOI_LABELS.find(([re]) => re.test(raw))?.[1] ?? raw

const modes = computed(() =>
  (props.evidenceData?.modes_of_inheritance ?? [])
    .filter(Boolean)
    .map(raw => ({ raw, label: moiLabel(raw) }))
)

const panelUrl = p =>
  p.region === 'UK'
    ? `https://panelapp.genomicsengland.co.uk/panels/${p.id}/`
    : p.region === 'Australia'
      ? `https://panelapp-aus.org/panels/${p.id}/`
      : null
</script>
