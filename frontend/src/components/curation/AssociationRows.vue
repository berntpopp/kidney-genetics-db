<script setup lang="ts">
/**
 * Table body rows for curated associations, grouped by gene-disease pair (as ClinGen's
 * "group by gene-disease pair"). Each record shows one scannable line: inheritance,
 * classification, citations and a one-line summary; methodology, provenance, points and
 * diagnostics open in a full-width details row. Below lg the rows stack as cards.
 */
import { ref } from 'vue'
import { RouterLink } from 'vue-router'
import { ChevronDown } from 'lucide-vue-next'
import { hasShortReadLimit, type Association } from '@/api/curation'
import AssociationDiagnostics from '@/components/curation/AssociationDiagnostics.vue'
import AssociationProvenance from '@/components/curation/AssociationProvenance.vue'
import MoiChip from '@/components/curation/MoiChip.vue'
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
  !!(r.evidence_summary || r.methodology || r.scores || r.source === 'gene_curator') ||
  hasDiagnostics(r)
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
            :to="`/genes/${pair.gene}`"
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
          <div class="flex flex-wrap gap-1.5">
            <Chip
              v-if="r.relationship_type === 'susceptibility'"
              kind="neutral"
              :label="r.evidence_strength"
              tooltip="Susceptibility (risk) association, not a Mendelian validity class"
            />
            <Chip v-else :classification="r.evidence_strength" />
            <Chip
              v-if="hasShortReadLimit(r.diagnostics)"
              status="warning"
              label="Short-read limit"
              tooltip="Standard short-read testing can miss variants in this gene: a negative short-read result does not exclude the diagnosis."
            />
          </div>
        </TableCell>
        <TableCell
          :class="[STACK, 'min-w-56 align-top whitespace-normal [overflow-wrap:anywhere]']"
        >
          <div class="flex flex-wrap items-center gap-x-3 gap-y-1">
            <OntologyTermList :terms="citationTerms(r)" source="PubMed" />
            <Button
              v-if="hasDetails(r)"
              variant="ghost"
              size="sm"
              class="-my-1 h-7 px-2 text-xs text-muted-foreground"
              :aria-expanded="open.has(r.id)"
              :aria-controls="`gda-details-${r.id}`"
              @click="toggle(r.id)"
            >
              Details
              <ChevronDown
                aria-hidden="true"
                class="size-3.5 transition-transform motion-reduce:transition-none"
                :class="open.has(r.id) && 'rotate-180'"
              />
            </Button>
          </div>
          <p
            v-if="r.evidence_summary && !open.has(r.id)"
            class="mt-1 line-clamp-1 text-xs text-muted-foreground"
            :title="r.evidence_summary"
          >
            {{ r.evidence_summary }}
          </p>
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
              <p v-if="r.evidence_summary" class="text-sm">{{ r.evidence_summary }}</p>
              <AssociationProvenance :record="r" :show-moi="false" />
            </div>
            <AssociationDiagnostics :diagnostics="r.diagnostics" />
          </div>
        </TableCell>
      </TableRow>
    </template>
  </template>
</template>
