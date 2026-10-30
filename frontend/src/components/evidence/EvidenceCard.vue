<template>
  <Collapsible v-model:open="open" as-child>
    <article
      class="rounded-xl border bg-card text-card-foreground"
      :aria-labelledby="headingId"
      data-slot="evidence-card"
      :data-source="evidence.source_name"
    >
      <div class="flex items-start gap-3 px-4 py-3">
        <div class="min-w-0 flex-1 space-y-1.5">
          <div class="flex flex-wrap items-center gap-x-3 gap-y-1.5">
            <h3 :id="headingId" class="text-base font-semibold">
              <SourceLabel :source="evidence.source_name" />
            </h3>
            <Chip v-if="meta.classification" :classification="meta.classification" />
            <Chip
              v-if="evidence.normalized_score != null"
              kind="neutral"
              class="tabular-nums"
              data-testid="source-score"
              :label="`Score ${formatPercent(evidence.normalized_score)}`"
              :tooltip="scoreTooltip"
            />
          </div>
          <p
            v-if="meta.summary"
            class="line-clamp-2 text-sm text-muted-foreground"
            :title="meta.summary"
            data-testid="evidence-summary"
          >
            {{ meta.summary }}
          </p>
          <ul
            v-if="meta.stats.length"
            class="flex flex-wrap gap-x-4 gap-y-1 text-sm"
            data-testid="evidence-stats"
          >
            <li v-for="s in meta.stats" :key="s.unit" :title="s.tooltip">
              <span class="font-semibold tabular-nums text-foreground">{{
                s.value.toLocaleString()
              }}</span>
              <span class="text-muted-foreground">{{ ` ${s.unit}` }}</span>
            </li>
            <li v-if="captured" class="text-muted-foreground" data-testid="evidence-captured">
              captured
              <time :datetime="captured.oldest.toISOString()">{{ formatDay(captured.oldest) }}</time
              ><template v-if="captured.newest"
                >–<time :datetime="captured.newest.toISOString()">{{
                  formatDay(captured.newest)
                }}</time></template
              >
            </li>
          </ul>
        </div>
        <CollapsibleTrigger as-child>
          <Button
            variant="ghost"
            size="sm"
            class="shrink-0"
            :aria-label="`${open ? 'Hide' : 'Show'} ${displayName} details`"
          >
            <span class="hidden sm:inline">{{ open ? 'Hide details' : 'Show details' }}</span>
            <ChevronDown
              class="transition-transform motion-reduce:transition-none"
              :class="open && 'rotate-180'"
              aria-hidden="true"
            />
          </Button>
        </CollapsibleTrigger>
      </div>

      <CollapsibleContent>
        <div class="space-y-4 border-t px-4 py-4">
          <component
            :is="bodyComponent"
            v-if="bodyComponent"
            :evidence-data="evidence.evidence_data ?? {}"
            :source-name="evidence.source_name"
          />
        </div>
        <footer
          v-if="updated || meta.link"
          class="flex flex-wrap items-center justify-between gap-2 border-t px-4 py-2 text-xs text-muted-foreground"
        >
          <span v-if="updated">Last updated {{ updated }}</span>
          <a
            v-if="meta.link"
            :href="meta.link.href"
            target="_blank"
            rel="noopener noreferrer"
            class="ml-auto inline-flex items-center gap-1 rounded-sm font-medium text-primary underline-offset-4 hover:underline focus-visible:ring-2 focus-visible:ring-ring focus-visible:outline-none"
          >
            {{ meta.link.label }}
            <ExternalLink class="size-3" aria-hidden="true" />
            <span class="sr-only">(opens in a new tab)</span>
          </a>
        </footer>
      </CollapsibleContent>
    </article>
  </Collapsible>
</template>

<script setup>
import { computed, ref, useId } from 'vue'
import { ChevronDown, ExternalLink } from 'lucide-vue-next'
import { Collapsible, CollapsibleContent, CollapsibleTrigger } from '@/components/ui/collapsible'
import { Button } from '@/components/ui/button'
import { Chip, SourceLabel } from '@/components/shared'
import { sourceDisplayName } from '@/utils/sources'
import { evidenceMeta } from './evidenceMeta'
import { captureRange, formatDay, geneLabs, useProviderRegistry } from './diagnosticPanels'
import GenCCEvidence from './GenCCEvidence.vue'
import HPOEvidence from './HPOEvidence.vue'
import PubTatorEvidence from './PubTatorEvidence.vue'
import ClinGenEvidence from './ClinGenEvidence.vue'
import PanelAppEvidence from './PanelAppEvidence.vue'
import DiagnosticPanelsEvidence from './DiagnosticPanelsEvidence.vue'
import LiteratureEvidence from './LiteratureEvidence.vue'

const props = defineProps({
  evidence: { type: Object, required: true },
  /** { approved_symbol, hgnc_id } for gene-specific source links */
  gene: { type: Object, default: () => ({ approved_symbol: '' }) },
  /** { ncbiGeneId } from the gene's annotations */
  context: { type: Object, default: () => ({}) }
})

const open = ref(false)
const headingId = `evidence-${useId()}`

const BODIES = {
  GenCC: GenCCEvidence,
  HPO: HPOEvidence,
  PubTator: PubTatorEvidence,
  ClinGen: ClinGenEvidence,
  PanelApp: PanelAppEvidence,
  DiagnosticPanels: DiagnosticPanelsEvidence,
  Literature: LiteratureEvidence
}

const bodyComponent = computed(() => BODIES[props.evidence.source_name] ?? null)
const displayName = computed(() => sourceDisplayName(props.evidence.source_name))
const meta = computed(() =>
  evidenceMeta(props.evidence.source_name, props.evidence.evidence_data, props.gene, props.context)
)

// Diagnostic panels only: when the gene's labs were scraped (enhancement; absent until loaded)
const registry = useProviderRegistry(() => props.evidence.source_name === 'DiagnosticPanels')
const captured = computed(() =>
  props.evidence.source_name === 'DiagnosticPanels'
    ? captureRange(
        geneLabs(props.evidence.evidence_data ?? {}).map(p => registry.byName.value.get(p))
      )
    : null
)

const formatPercent = score => `${(score * 100).toFixed(1)}%`

// Mirrors backend evidence_normalized_scores: GenCC two-stage, ClinGen weight, else count percentile
const scoreTooltip = computed(() => {
  const source = props.evidence.source_name
  if (source === 'GenCC')
    return 'Source score (0–100%): strongest classification, adjusted for agreeing and conflicting submitters'
  if (source === 'ClinGen') return 'Source score (0–100%): weight of the strongest classification'
  return `Source score (0–100%): percentile rank of this gene's evidence count among genes with ${displayName.value} evidence`
})

const updated = computed(() => {
  const raw = props.evidence.evidence_date ?? props.evidence.evidence_data?.last_updated
  if (!raw) return null
  // Date-only strings are local dates, not UTC midnight
  const date = new Date(/^\d{4}-\d{2}-\d{2}$/.test(raw) ? `${raw}T00:00:00` : raw)
  return Number.isNaN(date.getTime())
    ? null
    : date.toLocaleDateString('en-US', { year: 'numeric', month: 'short', day: 'numeric' })
})
</script>
