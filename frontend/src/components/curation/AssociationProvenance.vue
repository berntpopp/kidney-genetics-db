<script setup lang="ts">
/** Inheritance mode, methodology, origin and points of a curated association (#437) */
import { computed } from 'vue'
import { isHttpUrl, MOI_TERMS, type Association } from '@/api/curation'

// showMoi: false where a table already shows the inheritance mode in its own column
const props = withDefaults(defineProps<{ record: Association; showMoi?: boolean }>(), {
  showMoi: true
})

const moiLabel = computed(() =>
  props.record.moi ? (props.record.moi_label ?? MOI_TERMS[props.record.moi] ?? null) : null
)
const methodology = computed(() => {
  const { methodology: name, methodology_version: version } = props.record
  return name ? (version ? `${name} (${version})` : name) : null
})
const fromGeneCurator = computed(() => props.record.source === 'gene_curator')
const points = computed(() => {
  const s = props.record.scores
  if (!s || s.total == null) return null
  const parts = [
    s.genetic != null ? `genetic ${s.genetic}` : null,
    s.experimental != null ? `experimental ${s.experimental}` : null
  ].filter(Boolean)
  return `${s.total} points${parts.length ? ` (${parts.join(', ')})` : ''}`
})
</script>

<template>
  <dl
    v-if="(showMoi && record.moi) || methodology || fromGeneCurator || points"
    class="whitespace-normal [overflow-wrap:anywhere] grid grid-cols-[auto_1fr] gap-x-3 gap-y-1 text-xs"
  >
    <template v-if="showMoi && record.moi">
      <dt class="text-muted-foreground">Inheritance</dt>
      <dd>
        {{ moiLabel ?? 'Unknown term' }}
        <span class="font-mono text-muted-foreground">{{ record.moi }}</span>
      </dd>
    </template>
    <template v-if="methodology">
      <dt class="text-muted-foreground">Methodology</dt>
      <dd>{{ methodology }}</dd>
    </template>
    <template v-if="points">
      <dt class="text-muted-foreground">Points</dt>
      <dd class="tabular-nums">{{ points }}</dd>
    </template>
    <template v-if="fromGeneCurator">
      <dt class="text-muted-foreground">Provenance</dt>
      <dd class="space-y-0.5">
        <a
          v-if="isHttpUrl(record.external_url)"
          :href="record.external_url"
          target="_blank"
          rel="noopener noreferrer"
          class="rounded-sm text-primary underline-offset-4 hover:underline focus-visible:ring-2 focus-visible:ring-ring focus-visible:outline-none"
        >
          Curated in Gene Curator ↗<span class="sr-only"> (opens in a new tab)</span>
        </a>
        <span v-else>Curated in Gene Curator</span>
        <span v-if="record.external_id" class="ml-1 font-mono text-muted-foreground">{{
          record.external_id
        }}</span>
        <p v-if="record.external_curator || record.external_reviewer" class="text-muted-foreground">
          <span v-if="record.external_curator">Curator: {{ record.external_curator }}</span>
          <span v-if="record.external_curator && record.external_reviewer"> · </span>
          <span v-if="record.external_reviewer">Reviewer: {{ record.external_reviewer }}</span>
        </p>
      </dd>
    </template>
  </dl>
</template>
