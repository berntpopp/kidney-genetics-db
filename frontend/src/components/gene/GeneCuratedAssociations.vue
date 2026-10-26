<template>
  <Card v-if="records.length">
    <CardHeader class="pb-2">
      <CardTitle tag="h2" class="text-base">Expert-reviewed associations</CardTitle>
    </CardHeader>
    <CardContent class="space-y-3 text-sm">
      <ul class="space-y-3">
        <li v-for="r in records" :key="r.id" class="space-y-1">
          <div class="flex flex-wrap items-center gap-2">
            <Badge variant="secondary">{{ r.evidence_strength }}</Badge>
            <span>{{ r.disease_name }}</span>
            <a
              :href="diseaseUrl(r.disease_id)"
              target="_blank"
              rel="noopener noreferrer"
              class="text-primary underline underline-offset-2"
              >{{ r.disease_id }}</a
            >
          </div>
          <p v-if="r.evidence_summary" class="text-muted-foreground">{{ r.evidence_summary }}</p>
          <p class="text-xs text-muted-foreground">
            <a
              v-for="c in r.citations"
              :key="c"
              :href="pubmedUrl(c)"
              target="_blank"
              rel="noopener noreferrer"
              class="mr-2 underline underline-offset-2"
              >{{ c }}</a
            >
            <span v-if="r.published_at">
              · published {{ new Date(r.published_at).toLocaleDateString() }}</span
            >
          </p>
        </li>
      </ul>
      <RouterLink to="/curation/associations" class="text-xs underline underline-offset-2">
        All expert-reviewed associations
      </RouterLink>
    </CardContent>
  </Card>
</template>

<script setup lang="ts">
import { ref, watch } from 'vue'
import { RouterLink } from 'vue-router'
import { curationApi, diseaseUrl, pubmedUrl, type Association } from '@/api/curation'
import { Badge } from '@/components/ui/badge'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'

const props = defineProps<{ geneSymbol: string }>()

// Published records only (the public endpoint); none or a failed request shows nothing (#379)
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
