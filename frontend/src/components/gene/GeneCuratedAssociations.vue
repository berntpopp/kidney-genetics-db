<template>
  <Card v-if="records.length" class="gap-4">
    <CardHeader class="pb-2">
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
        <ul class="space-y-3">
          <li v-for="r in group.records" :key="r.id" class="space-y-1">
            <div class="flex flex-wrap items-center gap-2">
              <Chip v-if="group.type === 'mendelian'" :classification="r.evidence_strength" />
              <SusceptibilityChip v-else :strength="r.evidence_strength" />
              <MoiChip :moi="r.moi" />
              <OntologyTerm
                :id="r.disease_id"
                :name="r.disease_name"
                :href="diseaseUrl(r.disease_id)"
              />
            </div>
            <p v-if="r.evidence_summary" class="text-muted-foreground [overflow-wrap:anywhere]">
              {{ r.evidence_summary }}
            </p>
            <AssociationProvenance :record="r" :show-moi="false" />
            <p class="flex flex-wrap gap-x-3 text-xs text-muted-foreground">
              <OntologyTerm v-for="c in r.citations" :id="c" :key="c" source="PubMed" />
              <span v-if="r.published_at"> Published {{ r.published_at.slice(0, 10) }}</span>
            </p>
            <AssociationDiagnostics :diagnostics="r.diagnostics" />
          </li>
        </ul>
      </section>
      <RouterLink
        to="/curation/associations"
        class="rounded-sm text-xs text-primary underline-offset-4 hover:underline focus-visible:ring-2 focus-visible:ring-ring focus-visible:outline-none"
      >
        All expert-reviewed associations
      </RouterLink>
    </CardContent>
  </Card>
</template>

<script setup lang="ts">
import { computed, ref, watch } from 'vue'
import { RouterLink } from 'vue-router'
import {
  curationApi,
  diseaseUrl,
  RELATIONSHIP_LABELS,
  RELATIONSHIP_TYPES,
  type Association
} from '@/api/curation'
import AssociationDiagnostics from '@/components/curation/AssociationDiagnostics.vue'
import AssociationProvenance from '@/components/curation/AssociationProvenance.vue'
import MoiChip from '@/components/curation/MoiChip.vue'
import SusceptibilityChip from '@/components/curation/SusceptibilityChip.vue'
import { Chip, OntologyTerm } from '@/components/shared'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'

const props = defineProps<{ geneSymbol: string }>()

// Published records only (the public endpoint); none or a failed request shows nothing (issue 379)
const records = ref<Association[]>([])

const groups = computed(() =>
  RELATIONSHIP_TYPES.map(type => ({
    type,
    records: records.value.filter(r => (r.relationship_type ?? 'mendelian') === type)
  })).filter(g => g.records.length)
)

watch(
  () => props.geneSymbol,
  async symbol => {
    records.value = []
    if (!symbol) return
    try {
      records.value = (await curationApi.listPublished({ gene_symbol: symbol })).data
    } catch (err) {
      window.logService?.warn('Curated associations unavailable', err)
    }
  },
  { immediate: true }
)
</script>
