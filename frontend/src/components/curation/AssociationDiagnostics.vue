<script setup lang="ts">
/**
 * Non-scoring "Diagnostics & resources" block (issues 437, 439): recommended transcript,
 * detectability limits and verified resources. Renders nothing without content.
 */
import { computed } from 'vue'
import { AlertTriangle } from 'lucide-vue-next'
import { Alert, AlertDescription } from '@/components/ui/alert'
import { isHttpUrl, MANE_LABELS, RESOURCE_LABELS, type Diagnostics } from '@/api/curation'

const props = defineProps<{ diagnostics: Diagnostics | null | undefined }>()

const transcript = computed(() => props.diagnostics?.recommended_transcript ?? null)
const detectability = computed(() => props.diagnostics?.detectability ?? [])
const resources = computed(() => props.diagnostics?.resources ?? [])
const hasContent = computed(
  () => !!transcript.value || detectability.value.length > 0 || resources.value.length > 0
)
const warn = computed(() => detectability.value.some(d => d.negative_report_does_not_exclude))
const linkClass =
  'rounded-sm text-primary underline-offset-4 hover:underline focus-visible:ring-2 focus-visible:ring-ring focus-visible:outline-none'
</script>

<template>
  <section
    v-if="hasContent"
    class="whitespace-normal [overflow-wrap:anywhere] space-y-2 text-xs"
    aria-label="Diagnostics and resources"
  >
    <h3 class="text-sm font-medium">Diagnostics &amp; resources</h3>

    <Alert v-if="warn" class="py-2">
      <AlertTriangle aria-hidden="true" />
      <AlertDescription>
        Standard short-read testing can miss variants in this gene: a negative short-read result
        does not exclude the diagnosis.
      </AlertDescription>
    </Alert>

    <p v-if="transcript">
      <span class="text-muted-foreground">Transcript: </span>
      <span class="font-mono">{{
        [transcript.refseq, transcript.ensembl].filter(Boolean).join(' / ') || '—'
      }}</span>
      · {{ MANE_LABELS[transcript.mane_status] ?? transcript.mane_status }}
      <template v-if="transcript.legacy_transcript">
        · literature <span class="font-mono">{{ transcript.legacy_transcript }}</span>
      </template>
      <span v-if="transcript.numbering_conversion" class="block text-muted-foreground">
        {{ transcript.numbering_conversion }}
      </span>
    </p>

    <ul v-if="detectability.length" class="list-disc space-y-1 pl-4">
      <li v-for="(d, i) in detectability" :key="i">
        {{ d.challenge }}
        <span v-if="d.share_of_variants" class="text-muted-foreground">
          ({{ d.share_of_variants }})</span
        >
        <span v-if="d.methods.length" class="block text-muted-foreground">
          Methods: {{ d.methods.map(m => m.replaceAll('_', ' ')).join(', ') }}
        </span>
        <span v-if="d.tools.length" class="block">
          Tools:
          <template v-for="(t, j) in d.tools" :key="j">
            <a
              v-if="isHttpUrl(t.url)"
              :href="t.url"
              target="_blank"
              rel="noopener noreferrer"
              :class="linkClass"
              >{{ t.name }}</a
            ><span v-else>{{ t.name }}</span
            ><span v-if="j < d.tools.length - 1">, </span>
          </template>
        </span>
      </li>
    </ul>

    <ul v-if="resources.length" class="space-y-1">
      <li v-for="(r, i) in resources" :key="i">
        <span class="text-muted-foreground">{{ RESOURCE_LABELS[r.type] ?? r.type }}: </span>
        <a
          v-if="isHttpUrl(r.url)"
          :href="r.url"
          target="_blank"
          rel="noopener noreferrer"
          :class="linkClass"
          >{{ r.name }}<span class="sr-only"> (opens in a new tab)</span></a
        >
        <span v-else>{{ r.name }}</span>
        <span v-if="r.language" class="text-muted-foreground"> · {{ r.language }}</span>
        <span class="text-muted-foreground"> · verified {{ r.verified.date }}</span>
      </li>
    </ul>
  </section>
</template>
