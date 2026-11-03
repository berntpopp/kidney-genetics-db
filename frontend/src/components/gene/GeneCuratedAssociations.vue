<template>
  <Card v-if="records.length" class="gap-4">
    <CardHeader v-if="!standalone" class="pb-2">
      <CardTitle tag="h2" class="text-base">
        Expert-reviewed associations
        <span
          v-if="records.length > 1"
          data-testid="gda-count"
          class="ml-1 font-normal text-muted-foreground tabular-nums"
          >· {{ records.length }}</span
        >
      </CardTitle>
    </CardHeader>
    <!-- The page header names the gene; this keeps the outline h1 > h2 > h3 -->
    <h2 v-else class="sr-only">Curated associations</h2>
    <CardContent class="space-y-4 text-sm">
      <!-- Several entities: one line each, so the count and what separates them read first (#539) -->
      <!-- Below sm the rows stack (disease, then MOI and class) so no column scrolls out of view -->
      <Table v-if="records.length > 1" data-testid="gda-overview" class="max-sm:block">
        <TableCaption class="mt-0 mb-2 caption-top text-left text-xs max-sm:block">
          {{ records.length }} associations, each a separate gene–disease entity with its own
          classification: different classes are not a conflict.
        </TableCaption>
        <TableHeader class="max-sm:sr-only">
          <TableRow>
            <TableHead>Disease</TableHead>
            <TableHead class="w-14">MOI</TableHead>
            <TableHead>Classification</TableHead>
          </TableRow>
        </TableHeader>
        <TableBody class="max-sm:block">
          <TableRow
            v-for="r in sorted"
            :key="r.id"
            data-testid="gda-overview-row"
            class="max-sm:block max-sm:py-2"
          >
            <TableCell class="align-top whitespace-normal max-sm:block max-sm:px-0 max-sm:py-0.5">
              <a
                :href="`#gda-${r.id}`"
                class="rounded-sm underline-offset-4 hover:underline focus-visible:ring-2 focus-visible:ring-ring focus-visible:outline-none"
                >{{ r.disease_name }}</a
              >
              <span class="ml-1 font-mono text-xs whitespace-nowrap text-muted-foreground">{{
                r.disease_id
              }}</span>
            </TableCell>
            <TableCell class="align-top max-sm:inline-block max-sm:px-0 max-sm:pr-2"
              ><MoiChip :moi="r.moi"
            /></TableCell>
            <TableCell class="align-top whitespace-normal max-sm:inline-block max-sm:px-0">
              <div class="flex flex-wrap items-center gap-x-2 gap-y-1">
                <SusceptibilityChip
                  v-if="isRisk(r)"
                  :strength="r.evidence_strength"
                  :odds-ratio="r.odds_ratio"
                />
                <Chip v-else :classification="r.evidence_strength" />
                <span class="text-xs text-muted-foreground">
                  {{ isRisk(r) ? 'Susceptibility' : 'Mendelian' }}
                  <template v-if="r.shared_risk_allele_genes?.length">
                    · allele shared with {{ r.shared_risk_allele_genes.join(', ') }}
                  </template>
                </span>
              </div>
            </TableCell>
          </TableRow>
        </TableBody>
      </Table>

      <!-- Susceptibility is listed apart and never with Mendelian strength colours (#437) -->
      <section
        v-for="group in groups"
        :key="group.type"
        :data-testid="`gda-${group.type}`"
        class="space-y-2"
      >
        <h3 class="text-xs font-medium text-muted-foreground">
          {{ RELATIONSHIP_LABELS[group.type] }}
        </h3>
        <ul class="divide-y divide-border">
          <li
            v-for="r in group.records"
            :id="`gda-${r.id}`"
            :key="r.id"
            class="scroll-mt-24 space-y-2 py-3 first:pt-0 last:pb-0"
          >
            <!-- The disease names the entity; its class and inheritance follow -->
            <h4 class="font-semibold [overflow-wrap:anywhere]">
              <OntologyTerm
                :id="r.disease_id"
                :name="r.disease_name"
                :href="diseaseUrl(r.disease_id)"
              />
            </h4>
            <div class="flex flex-wrap items-center gap-2">
              <MoiChip :moi="r.moi" />
              <SusceptibilityChip
                v-if="isRisk(r)"
                :strength="r.evidence_strength"
                :odds-ratio="r.odds_ratio"
              />
              <Chip v-else :classification="r.evidence_strength" />
              <ReviewChip :record="r" />
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
            <p v-if="r.risk_allele" class="text-muted-foreground [overflow-wrap:anywhere]">
              Risk allele <span class="font-mono text-xs text-foreground">{{ r.risk_allele }}</span>
              <template v-if="r.shared_risk_allele_genes?.length">
                · also curated for
                <template v-for="(g, i) in r.shared_risk_allele_genes" :key="g"
                  >{{ i ? ', ' : ''
                  }}<RouterLink :to="`/curation/associations/${g}`" :class="LINK">{{
                    g
                  }}</RouterLink></template
                >: shared evidence, count it once
              </template>
            </p>
            <!-- Summary and provenance beside diagnostics on wide screens, like the table details -->
            <div class="grid gap-4 lg:grid-cols-2">
              <div class="space-y-2">
                <div v-if="r.evidence_summary" class="space-y-1">
                  <p class="text-xs font-medium text-muted-foreground">Synopsis</p>
                  <p class="max-w-prose whitespace-pre-line [overflow-wrap:anywhere]">
                    {{ r.evidence_summary }}
                  </p>
                </div>
                <AssociationProvenance :record="r" :show-moi="false">
                  <template v-if="r.citations.length">
                    <dt class="text-muted-foreground">Citations</dt>
                    <dd>
                      <OntologyTermList
                        :terms="r.citations.map(id => ({ id }))"
                        source="PubMed"
                        :max="6"
                      />
                    </dd>
                  </template>
                  <template v-if="r.published_at">
                    <dt class="text-muted-foreground">Published</dt>
                    <dd class="tabular-nums">{{ r.published_at.slice(0, 10) }}</dd>
                  </template>
                </AssociationProvenance>
              </div>
              <AssociationDiagnostics :diagnostics="r.diagnostics" heading="h5" />
            </div>
          </li>
        </ul>
      </section>
      <RouterLink v-if="!standalone" to="/curation/associations" :class="['text-xs', LINK]">
        All expert-reviewed associations
      </RouterLink>
    </CardContent>
  </Card>
</template>

<script setup lang="ts">
import { computed } from 'vue'
import { RouterLink } from 'vue-router'
import {
  diseaseUrl,
  clinicalGroupLabel,
  clinicalGroupText,
  hasShortReadLimit,
  SHORT_READ_NOTE,
  RELATIONSHIP_LABELS,
  RELATIONSHIP_TYPES,
  strengthsFor,
  type Association
} from '@/api/curation'
import AssociationDiagnostics from '@/components/curation/AssociationDiagnostics.vue'
import AssociationProvenance from '@/components/curation/AssociationProvenance.vue'
import MoiChip from '@/components/curation/MoiChip.vue'
import ReviewChip from '@/components/curation/ReviewChip.vue'
import SusceptibilityChip from '@/components/curation/SusceptibilityChip.vue'
import { Chip, OntologyTerm, OntologyTermList } from '@/components/shared'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import {
  Table,
  TableBody,
  TableCaption,
  TableCell,
  TableHead,
  TableHeader,
  TableRow
} from '@/components/ui/table'

// The gene's published records; GeneDetail fetches them before first paint so the card never pops in
// standalone: the page header and breadcrumb already name the list and link back
const props = defineProps<{ records: Association[]; standalone?: boolean }>()

const LINK =
  'rounded-sm text-primary underline-offset-4 hover:underline focus-visible:ring-2 focus-visible:ring-ring focus-visible:outline-none'
const typeOf = (r: Association) => r.relationship_type ?? 'mendelian'
const isRisk = (r: Association) => typeOf(r) === 'susceptibility'

// Mendelian first, then strongest class, then disease name: never the order of MONDO IDs
const sorted = computed(() =>
  [...props.records].sort(
    (a, b) =>
      RELATIONSHIP_TYPES.indexOf(typeOf(a)) - RELATIONSHIP_TYPES.indexOf(typeOf(b)) ||
      strengthsFor(typeOf(a)).indexOf(a.evidence_strength) -
        strengthsFor(typeOf(b)).indexOf(b.evidence_strength) ||
      a.disease_name.localeCompare(b.disease_name)
  )
)

const groups = computed(() =>
  RELATIONSHIP_TYPES.map(type => ({
    type,
    records: sorted.value.filter(r => typeOf(r) === type)
  })).filter(g => g.records.length)
)
</script>
