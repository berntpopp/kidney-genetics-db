<template>
  <Card v-if="records.length" class="gap-4">
    <CardHeader class="pb-2">
      <CardTitle tag="h2" class="text-base">Expert-reviewed associations</CardTitle>
    </CardHeader>
    <CardContent class="space-y-3 text-sm">
      <ul class="space-y-3">
        <li v-for="r in records" :key="r.id" class="space-y-1">
          <div class="flex flex-wrap items-center gap-2">
            <Chip :classification="r.evidence_strength" />
            <OntologyTerm
              :id="r.disease_id"
              :name="r.disease_name"
              :href="diseaseUrl(r.disease_id)"
            />
          </div>
          <p v-if="r.evidence_summary" class="text-muted-foreground">{{ r.evidence_summary }}</p>
          <p class="flex flex-wrap gap-x-3 text-xs text-muted-foreground">
            <OntologyTerm v-for="c in r.citations" :id="c" :key="c" source="PubMed" />
            <span v-if="r.published_at">
              Published {{ new Date(r.published_at).toLocaleDateString() }}</span
            >
          </p>
        </li>
      </ul>
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
import { ref, watch } from 'vue'
import { RouterLink } from 'vue-router'
import { curationApi, diseaseUrl, type Association } from '@/api/curation'
import { Chip, OntologyTerm } from '@/components/shared'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'

const props = defineProps<{ geneSymbol: string }>()

// Published records only (the public endpoint); none or a failed request shows nothing (issue 379)
const records = ref<Association[]>([])

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
