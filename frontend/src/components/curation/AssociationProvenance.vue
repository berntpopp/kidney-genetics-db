<script setup lang="ts">
/** Inheritance mode, methodology, origin and points of a curated association (#437) */
import { computed } from 'vue'
import { ExternalLink } from 'lucide-vue-next'
import {
  clinicalGroupText,
  differsFromClinGen,
  isAdoption,
  isHttpUrl,
  isPublicUrl,
  MOI_TERMS,
  type Association
} from '@/api/curation'

// showMoi: false where a table already shows the inheritance mode in its own column
const props = withDefaults(defineProps<{ record: Association; showMoi?: boolean }>(), {
  showMoi: true
})

const moiLabel = computed(() =>
  props.record.moi ? (props.record.moi_label ?? MOI_TERMS[props.record.moi] ?? null) : null
)
const methodology = computed(() => {
  const { methodology: name, methodology_version: version } = props.record
  if (!name || !version) return name || null
  // Gene Curator pins a number ("version 1"); KGDB records may name a draft ("draft iteration 3")
  return /^\d+$/.test(version) ? `${name}, version ${version}` : `${name} (${version})`
})
const adopted = computed(() => props.record.adopted_clingen ?? null)
// An adoption takes ClinGen's class; our own curation only cites it
const adoption = computed(() => isAdoption(props.record))
const differs = computed(() => differsFromClinGen(props.record))
const fromGeneCurator = computed(() => props.record.source === 'gene_curator')
// Software agents Gene Curator credits; the curator is one when it is an agent account
const curatorIsAgent = computed(
  () =>
    !!props.record.external_curator &&
    !!props.record.ai_agents?.includes(props.record.external_curator)
)
const ai = computed(
  () => props.record.ai_agents?.filter(a => a !== props.record.external_curator).join(', ') || null
)
// An AI-approved import was reviewed in Gene Curator by an agent account
const reviewerIsAgent = computed(() => props.record.approval_kind === 'ai')
const points = computed(() => {
  const s = props.record.scores
  if (!s || s.total == null) return null
  // Gene Curator's susceptibility "functional" section is stored as experimental
  const susceptibility = props.record.relationship_type === 'susceptibility'
  const parts = [
    s.genetic != null ? `genetic ${s.genetic}` : null,
    s.association != null ? `association ${s.association}` : null,
    s.experimental != null
      ? `${susceptibility ? 'functional' : 'experimental'} ${s.experimental}`
      : null
  ].filter(Boolean)
  return `${s.total} points${parts.length ? ` (${parts.join(', ')})` : ''}`
})
</script>

<template>
  <dl
    v-if="
      (showMoi && record.moi) ||
      methodology ||
      fromGeneCurator ||
      record.external_curator ||
      ai ||
      record.clinical_group ||
      record.external_reviewer ||
      adopted ||
      record.classification_rationale ||
      points ||
      $slots.default
    "
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
    <template v-if="adopted">
      <dt class="text-muted-foreground">{{ adoption ? 'Adopted from' : 'ClinGen' }}</dt>
      <dd>
        <a
          v-if="isHttpUrl(adopted.url)"
          :href="adopted.url"
          target="_blank"
          rel="noopener noreferrer"
          class="inline-flex items-center gap-1 rounded-sm text-primary underline-offset-4 hover:underline focus-visible:ring-2 focus-visible:ring-ring focus-visible:outline-none"
        >
          {{ adoption ? 'ClinGen' : adopted.classification }}
          <ExternalLink class="size-3" aria-hidden="true" />
          <span class="sr-only">(opens in a new tab)</span>
        </a>
        <span v-else>{{ adoption ? 'ClinGen' : adopted.classification }}</span>
        {{
          [
            adopted.expert_panel,
            adoption && adopted.classification,
            adopted.classified_date && `classified ${adopted.classified_date}`
          ]
            .filter(Boolean)
            .map(part => ` · ${part}`)
            .join('')
        }}
        <span v-if="differs" class="font-medium text-foreground">
          · differs from this curation</span
        >
      </dd>
    </template>
    <template v-if="record.classification_rationale">
      <dt class="text-muted-foreground">Why this class</dt>
      <dd class="max-w-prose">{{ record.classification_rationale }}</dd>
    </template>
    <template v-if="fromGeneCurator">
      <dt class="text-muted-foreground">Provenance</dt>
      <dd class="space-y-0.5">
        <a
          v-if="isPublicUrl(record.external_url)"
          :href="record.external_url"
          target="_blank"
          rel="noopener noreferrer"
          class="inline-flex items-center gap-1 rounded-sm text-primary underline-offset-4 hover:underline focus-visible:ring-2 focus-visible:ring-ring focus-visible:outline-none"
        >
          Curated in Gene Curator
          <ExternalLink class="size-3" aria-hidden="true" />
          <span class="sr-only">(opens in a new tab)</span>
        </a>
        <span v-else>Curated in Gene Curator</span>
        <span v-if="record.external_id" class="ml-1 font-mono text-muted-foreground">{{
          record.external_id
        }}</span>
      </dd>
    </template>
    <template v-if="record.clinical_group">
      <dt class="text-muted-foreground">Clinical group</dt>
      <dd>
        {{ clinicalGroupText(record.clinical_group) }}
        <span v-if="record.clinical_group.rationale" class="block text-muted-foreground">{{
          record.clinical_group.rationale
        }}</span>
      </dd>
    </template>
    <template v-if="record.external_curator || ai">
      <dt class="text-muted-foreground">Curated by</dt>
      <dd>
        {{ record.external_curator }}
        <span v-if="curatorIsAgent" class="ml-1 text-muted-foreground">· AI agent</span>
        <span v-if="ai" :class="['text-muted-foreground', { 'ml-1': record.external_curator }]"
          >{{ record.external_curator ? '· ' : '' }}AI-assisted ({{ ai }})</span
        >
      </dd>
    </template>
    <template v-if="record.external_reviewer">
      <dt class="text-muted-foreground">Reviewed by</dt>
      <dd>
        {{ record.external_reviewer }}
        <span v-if="reviewerIsAgent" class="ml-1 text-muted-foreground">· AI agent</span>
      </dd>
    </template>
    <!-- Extra dt/dd rows from the caller, aligned with the rows above -->
    <slot />
  </dl>
</template>
