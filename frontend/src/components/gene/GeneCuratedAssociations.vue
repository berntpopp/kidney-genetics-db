<template>
  <Card v-if="records.length" class="gap-4">
    <CardHeader v-if="!standalone" class="pb-2">
      <CardTitle tag="h2" class="text-base">Expert-reviewed associations</CardTitle>
    </CardHeader>
    <CardContent class="space-y-4 text-sm">
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
          <li v-for="r in group.records" :key="r.id" class="space-y-2 py-3 first:pt-0 last:pb-0">
            <!-- Same order as the table: inheritance, classification, disease -->
            <div class="flex flex-wrap items-center gap-2">
              <MoiChip :moi="r.moi" />
              <Chip v-if="group.type === 'mendelian'" :classification="r.evidence_strength" />
              <SusceptibilityChip
                v-else
                :strength="r.evidence_strength"
                :odds-ratio="r.odds_ratio"
              />
              <ReviewChip :record="r" />
              <Chip
                v-if="hasShortReadLimit(r.diagnostics)"
                status="warning"
                label="Short-read limit"
                :tooltip="SHORT_READ_NOTE"
              />
              <OntologyTerm
                :id="r.disease_id"
                :name="r.disease_name"
                :href="diseaseUrl(r.disease_id)"
              />
              <span v-if="r.risk_allele" class="text-muted-foreground">
                risk allele <span class="font-mono text-foreground">{{ r.risk_allele }}</span>
              </span>
            </div>
            <!-- Summary and provenance beside diagnostics on wide screens, like the table details -->
            <div class="grid gap-4 lg:grid-cols-2">
              <div class="space-y-2">
                <div v-if="r.evidence_summary" class="space-y-1">
                  <h4 class="text-xs font-medium text-muted-foreground">Synopsis</h4>
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
              <AssociationDiagnostics :diagnostics="r.diagnostics" />
            </div>
          </li>
        </ul>
      </section>
      <RouterLink
        v-if="!standalone"
        to="/curation/associations"
        class="rounded-sm text-xs text-primary underline-offset-4 hover:underline focus-visible:ring-2 focus-visible:ring-ring focus-visible:outline-none"
      >
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
  hasShortReadLimit,
  SHORT_READ_NOTE,
  RELATIONSHIP_LABELS,
  RELATIONSHIP_TYPES,
  type Association
} from '@/api/curation'
import AssociationDiagnostics from '@/components/curation/AssociationDiagnostics.vue'
import AssociationProvenance from '@/components/curation/AssociationProvenance.vue'
import MoiChip from '@/components/curation/MoiChip.vue'
import ReviewChip from '@/components/curation/ReviewChip.vue'
import SusceptibilityChip from '@/components/curation/SusceptibilityChip.vue'
import { Chip, OntologyTerm, OntologyTermList } from '@/components/shared'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'

// The gene's published records; GeneDetail fetches them before first paint so the card never pops in
// standalone: the page header and breadcrumb already name the list and link back
const props = defineProps<{ records: Association[]; standalone?: boolean }>()

const groups = computed(() =>
  RELATIONSHIP_TYPES.map(type => ({
    type,
    records: props.records.filter(r => (r.relationship_type ?? 'mendelian') === type)
  })).filter(g => g.records.length)
)
</script>
