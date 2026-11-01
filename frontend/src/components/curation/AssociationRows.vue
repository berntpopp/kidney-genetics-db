<script setup lang="ts">
/**
 * Table body rows for curated associations, grouped by gene-disease pair (as ClinGen's
 * "group by gene-disease pair"). Each record shows one scannable line: inheritance,
 * classification with points, a two-line summary and the citation count; citations,
 * methodology, provenance and diagnostics open in a full-width details row. Below lg the
 * rows stack as cards.
 */
import { ref } from 'vue'
import { RouterLink } from 'vue-router'
import { ChevronDown } from 'lucide-vue-next'
import {
  clinicalGroupLabel,
  clinicalGroupText,
  differsFromClinGen,
  hasShortReadLimit,
  isAdoption,
  SHORT_READ_NOTE,
  type Association
} from '@/api/curation'
import AssociationDiagnostics from '@/components/curation/AssociationDiagnostics.vue'
import AssociationProvenance from '@/components/curation/AssociationProvenance.vue'
import MoiChip from '@/components/curation/MoiChip.vue'
import ReviewChip from '@/components/curation/ReviewChip.vue'
import SusceptibilityChip from '@/components/curation/SusceptibilityChip.vue'
import { Button } from '@/components/ui/button'
import { TableCell, TableRow } from '@/components/ui/table'
import { Chip, OntologyTerm, OntologyTermList } from '@/components/shared'

const props = defineProps<{
  records: Association[]
  /** Number of trailing cells the parent renders through the `trailing` slot */
  trailing: number
  rowTestId: (_record: Association) => string
}>()

defineSlots<{ trailing(_props: { record: Association }): unknown }>()

const STACK = 'max-lg:block max-lg:min-w-0 max-lg:max-w-none max-lg:px-0 max-lg:py-1'
const colspan = 3 + props.trailing
const open = ref(new Set<number>())

function toggle(id: number) {
  const next = new Set(open.value)
  if (!next.delete(id)) next.add(id)
  open.value = next
}

function pairs(records: Association[]) {
  const map = new Map<string, { gene: string; id: string; name: string; rows: Association[] }>()
  for (const r of records) {
    const key = `${r.gene_symbol}|${r.disease_id}`
    if (!map.has(key))
      map.set(key, { gene: r.gene_symbol, id: r.disease_id, name: r.disease_name, rows: [] })
    map.get(key)!.rows.push(r)
  }
  return [...map.entries()].map(([key, pair]) => ({ key, ...pair }))
}

const hasDiagnostics = (r: Association) =>
  !!r.diagnostics &&
  (!!r.diagnostics.recommended_transcript ||
    r.diagnostics.detectability.length > 0 ||
    !!r.diagnostics.detectability_note ||
    r.diagnostics.resources.length > 0)
const hasDetails = (r: Association) =>
  !!(
    r.evidence_summary ||
    r.citations.length ||
    r.methodology ||
    r.scores ||
    r.source === 'gene_curator'
  ) || hasDiagnostics(r)
const citationTerms = (r: Association) => r.citations.map(id => ({ id }))
</script>

<template>
  <template v-for="pair in pairs(records)" :key="pair.key">
    <TableRow data-testid="gda-pair" class="hover:bg-transparent max-lg:block">
      <th
        scope="rowgroup"
        :colspan="colspan"
        class="border-t-2 border-border px-2 pt-4 pb-1 text-left align-baseline font-normal max-lg:block max-lg:px-0"
      >
        <div class="flex flex-wrap items-baseline gap-x-2 gap-y-0.5">
          <RouterLink
            :to="`/curation/associations/${pair.gene}`"
            class="rounded-sm font-semibold underline-offset-4 hover:underline focus-visible:ring-2 focus-visible:ring-ring focus-visible:outline-none"
          >
            {{ pair.gene }}
          </RouterLink>
          <span class="min-w-0 whitespace-normal [overflow-wrap:anywhere]">
            <OntologyTerm :id="pair.id" :name="pair.name" />
          </span>
          <span
            v-if="pair.rows.length > 1"
            class="ml-auto text-xs text-muted-foreground tabular-nums"
          >
            {{ pair.rows.length }} records
          </span>
        </div>
      </th>
    </TableRow>

    <template v-for="r in pair.rows" :key="r.id">
      <TableRow :data-testid="rowTestId(r)" class="max-lg:block max-lg:py-2">
        <TableCell :class="[STACK, 'w-16 align-top max-lg:inline-block max-lg:pr-1.5']">
          <span class="sr-only lg:hidden">Inheritance: </span>
          <MoiChip :moi="r.moi" />
        </TableCell>
        <TableCell :class="[STACK, 'align-top max-lg:inline-block']">
          <div class="flex flex-wrap gap-1.5 max-lg:inline-flex max-lg:align-middle">
            <SusceptibilityChip
              v-if="r.relationship_type === 'susceptibility'"
              :strength="r.evidence_strength"
              :odds-ratio="r.odds_ratio"
            />
            <Chip v-else :classification="r.evidence_strength" />
            <ReviewChip :record="r" />
            <span
              v-if="r.risk_allele"
              class="font-mono text-xs text-muted-foreground"
              :title="`Risk allele ${r.risk_allele}`"
              >{{ r.risk_allele }}</span
            >
            <Chip
              v-if="r.clinical_group"
              kind="neutral"
              :label="clinicalGroupLabel(r.clinical_group.primary)"
              :tooltip="`Curated clinical group: ${clinicalGroupText(r.clinical_group)}`"
            />
            <Chip
              v-if="hasShortReadLimit(r.diagnostics)"
              status="warning"
              label="Short-read limit"
              :tooltip="SHORT_READ_NOTE"
            />
          </div>
          <p
            v-if="r.scores?.total != null"
            class="mt-1 text-xs text-muted-foreground tabular-nums max-lg:ml-2 max-lg:inline-block max-lg:align-middle max-lg:mt-0"
          >
            {{ r.scores.total }} points
          </p>
        </TableCell>
        <TableCell
          :class="[STACK, 'min-w-56 align-top whitespace-normal [overflow-wrap:anywhere]']"
        >
          <p
            v-if="r.evidence_summary && !open.has(r.id)"
            class="mb-1 line-clamp-2 max-w-prose text-sm"
            :title="r.evidence_summary"
          >
            {{ r.evidence_summary }}
          </p>
          <!-- PMIDs are listed in the details row; the line shows how many and who curated -->
          <div
            class="flex flex-wrap items-center gap-x-3 gap-y-1 text-xs text-muted-foreground tabular-nums"
          >
            <span v-if="r.citations.length">
              {{ r.citations.length }} PubMed
              {{ r.citations.length === 1 ? 'citation' : 'citations' }}
            </span>
            <!-- An adopted classification may cite no PMIDs: say where the evidence lives -->
            <span v-else-if="isAdoption(r)">Classification adopted from ClinGen</span>
            <span v-if="r.adopted_clingen && !isAdoption(r)">
              ClinGen: {{ r.adopted_clingen.classification
              }}<span v-if="differsFromClinGen(r)" class="font-medium text-foreground">
                (differs)</span
              >
            </span>
            <span v-if="r.ai_agents?.length">AI-assisted curation</span>
            <Button
              v-if="hasDetails(r)"
              variant="ghost"
              size="sm"
              class="-mx-2 -my-1 h-7 px-2 text-xs text-muted-foreground"
              :aria-expanded="open.has(r.id)"
              :aria-controls="`gda-details-${r.id}`"
              @click="toggle(r.id)"
            >
              {{ open.has(r.id) ? 'Hide details' : 'Details' }}
              <ChevronDown
                aria-hidden="true"
                class="size-3.5 transition-transform motion-reduce:transition-none"
                :class="open.has(r.id) && 'rotate-180'"
              />
            </Button>
          </div>
        </TableCell>
        <slot name="trailing" :record="r" />
      </TableRow>
      <TableRow
        v-if="open.has(r.id)"
        :id="`gda-details-${r.id}`"
        :data-testid="`${rowTestId(r)}-details`"
        class="bg-muted/30 hover:bg-muted/30 max-lg:block"
      >
        <TableCell
          :colspan="colspan"
          class="px-4 py-3 whitespace-normal [overflow-wrap:anywhere] max-lg:block max-lg:px-3"
        >
          <div class="grid gap-4 md:grid-cols-2">
            <div class="space-y-2">
              <p v-if="r.evidence_summary" class="text-sm whitespace-pre-line">
                {{ r.evidence_summary }}
              </p>
              <AssociationProvenance :record="r" :show-moi="false">
                <template v-if="r.citations.length">
                  <dt class="text-muted-foreground">Citations</dt>
                  <dd><OntologyTermList :terms="citationTerms(r)" source="PubMed" /></dd>
                </template>
              </AssociationProvenance>
            </div>
            <AssociationDiagnostics :diagnostics="r.diagnostics" />
          </div>
        </TableCell>
      </TableRow>
    </template>
  </template>
</template>
