<template>
  <Card class="gap-4">
    <CardHeader>
      <CardTitle tag="h2" class="text-base">Diseases (MONDO)</CardTitle>
      <CardDescription>
        Disease identifiers from the gene's evidence sources, mapped to the MONDO Disease Ontology.
      </CardDescription>
    </CardHeader>
    <CardContent class="space-y-3 text-sm">
      <DataState
        :loading="loading"
        :error="error"
        :empty="!diseases.length"
        error-title="Could not load disease mappings"
        empty-message="No MONDO mappings in the annotation data for this gene."
        min-height="4rem"
        @retry="$emit('retry')"
      >
        <ul class="divide-y" data-testid="mondo-list">
          <li
            v-for="disease in diseases"
            :key="disease.mondo_id"
            class="flex flex-col gap-1.5 py-2 first:pt-0 last:pb-0 sm:flex-row sm:items-baseline sm:justify-between sm:gap-4"
          >
            <div class="min-w-0 space-y-0.5">
              <OntologyTerm :id="disease.mondo_id" :name="disease.label" />
              <p v-if="disease.sourceIds.length" class="text-xs text-muted-foreground">
                <span>Mapped from </span>
                <template v-for="(id, i) in disease.sourceIds" :key="id">
                  <OntologyTerm :id="id" /><span v-if="i < disease.sourceIds.length - 1">, </span>
                </template>
              </p>
            </div>
            <div class="flex shrink-0 flex-wrap gap-1">
              <Chip
                v-for="source in disease.sources"
                :key="source"
                kind="neutral"
                :label="sourceDisplayName(source)"
                :tooltip="`Reported by ${sourceDisplayName(source)}`"
              />
            </div>
          </li>
        </ul>
      </DataState>
      <template v-if="mondo">
        <p v-if="mondo.unmapped_count || mondo.ambiguous_count" class="text-muted-foreground">
          Not mapped: {{ mondo.unmapped_count }} without an exact match,
          {{ mondo.ambiguous_count }} ambiguous.
        </p>
        <p class="text-xs text-muted-foreground" data-testid="mondo-attribution">
          Mappings: MONDO release {{ mondo.provenance.mondo_release }} (SSSOM, exact matches only),
          licensed
          <a
            href="https://creativecommons.org/licenses/by/4.0/"
            target="_blank"
            rel="noopener noreferrer"
            class="rounded-sm underline underline-offset-2 focus-visible:ring-2 focus-visible:ring-ring focus-visible:outline-none"
            >CC BY 4.0</a
          >.
        </p>
      </template>
    </CardContent>
  </Card>
</template>

<script setup lang="ts">
import { computed } from 'vue'
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card'
import { Chip, DataState, OntologyTerm } from '@/components/shared'
import { parseOntologyId } from '@/utils/ontology'
import { sourceDisplayName } from '@/utils/sources'
import type { MondoAnnotation } from '@/types/mondo'

const props = defineProps<{
  annotations: { annotations?: { mondo?: { data: MondoAnnotation }[] } } | null
  loading?: boolean
  error?: string | Error | boolean | null
}>()

defineEmits<{ retry: [] }>()

const mondo = computed(() => props.annotations?.annotations?.mondo?.[0]?.data ?? null)

/**
 * Sorted by name; source IDs canonicalised (ORPHA/Orphanet merge), deduplicated and without
 * the MONDO term itself.
 */
const diseases = computed(() =>
  (mondo.value?.mondo_diseases ?? [])
    .map(d => {
      const self = parseOntologyId(d.mondo_id)?.id ?? d.mondo_id
      const ids = new Set<string>()
      for (const raw of d.source_ids ?? []) {
        const id = parseOntologyId(raw)?.id ?? raw
        if (id !== self) ids.add(id)
      }
      return {
        ...d,
        sourceIds: [...ids].sort(),
        sources: [...new Set(d.sources ?? [])].sort()
      }
    })
    .sort((a, b) => (a.label ?? a.mondo_id).localeCompare(b.label ?? b.mondo_id))
)
</script>
