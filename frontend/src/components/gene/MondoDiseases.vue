<template>
  <Card v-if="mondo?.mondo_diseases?.length">
    <CardHeader class="pb-2">
      <CardTitle tag="h2" class="text-base"> MONDO Diseases </CardTitle>
    </CardHeader>
    <CardContent class="space-y-3 text-sm">
      <ul class="space-y-1">
        <li v-for="disease in mondo.mondo_diseases" :key="disease.mondo_id">
          <a
            :href="`https://monarchinitiative.org/${disease.mondo_id}`"
            target="_blank"
            rel="noopener noreferrer"
            class="text-primary underline underline-offset-2"
            >{{ disease.mondo_id }}</a
          >
          <span v-if="disease.label"> {{ disease.label }}</span>
          <span class="text-muted-foreground">
            (from {{ disease.source_ids.join(', ') }}; {{ disease.sources.join(', ') }})</span
          >
        </li>
      </ul>
      <p v-if="mondo.unmapped_count || mondo.ambiguous_count" class="text-muted-foreground">
        Not mapped: {{ mondo.unmapped_count }} without an exact match,
        {{ mondo.ambiguous_count }} ambiguous.
      </p>
      <p class="text-xs text-muted-foreground" data-testid="mondo-attribution">
        Mappings: MONDO release {{ mondo.provenance.mondo_release }} (SSSOM, skos:exactMatch only),
        licensed
        <a
          href="https://creativecommons.org/licenses/by/4.0/"
          target="_blank"
          rel="noopener noreferrer"
          class="underline underline-offset-2"
          >CC BY 4.0</a
        >.
      </p>
    </CardContent>
  </Card>
</template>

<script setup lang="ts">
import { computed } from 'vue'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import type { MondoAnnotation } from '@/types/mondo'

const props = defineProps<{
  annotations: { annotations?: { mondo?: { data: MondoAnnotation }[] } } | null
}>()

const mondo = computed(() => props.annotations?.annotations?.mondo?.[0]?.data ?? null)
</script>
