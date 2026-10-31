<script setup lang="ts">
/**
 * Non-scoring "Diagnostics & resources" block (issues 437, 439): recommended transcript,
 * detectability limits and verified resources. Renders nothing without content.
 */
import { computed } from 'vue'
import { AlertTriangle } from 'lucide-vue-next'
import { Alert, AlertDescription } from '@/components/ui/alert'
import {
  detectabilityLabel,
  isHttpUrl,
  MANE_LABELS,
  RESOURCE_LABELS,
  SHORT_READ_NOTE,
  type Diagnostics
} from '@/api/curation'

const props = defineProps<{ diagnostics: Diagnostics | null | undefined }>()

const transcript = computed(() => props.diagnostics?.recommended_transcript ?? null)
const detectability = computed(() => props.diagnostics?.detectability ?? [])
const detectabilityNote = computed(() => props.diagnostics?.detectability_note ?? null)
const resources = computed(() => props.diagnostics?.resources ?? [])
const hasContent = computed(
  () =>
    !!transcript.value ||
    detectability.value.length > 0 ||
    !!detectabilityNote.value ||
    resources.value.length > 0
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
    <h4 class="text-sm font-medium">Diagnostics &amp; resources</h4>

    <Alert v-if="warn" class="py-2">
      <AlertTriangle aria-hidden="true" />
      <AlertDescription>
        {{ SHORT_READ_NOTE }}
      </AlertDescription>
    </Alert>

    <dl class="grid grid-cols-[auto_1fr] gap-x-3 gap-y-1.5">
      <template v-if="transcript">
        <dt class="text-muted-foreground">Transcript</dt>
        <dd>
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
          <span v-if="transcript.verified_via" class="block text-muted-foreground">
            Verified via {{ transcript.verified_via }}
          </span>
        </dd>
      </template>

      <template v-if="detectabilityNote || detectability.length">
        <dt class="text-muted-foreground">Detectability</dt>
        <dd class="space-y-1">
          <p v-if="detectabilityNote" class="max-w-prose">{{ detectabilityNote }}</p>
          <ul v-if="detectability.length" class="list-disc space-y-1 pl-4">
            <li v-for="(d, i) in detectability" :key="i">
              {{ detectabilityLabel(d.challenge) }}
              <span v-if="d.share_of_variants" class="text-muted-foreground">
                ({{ d.share_of_variants }})</span
              >
              <span v-if="d.methods.length" class="block text-muted-foreground">
                Methods: {{ d.methods.map(detectabilityLabel).join(', ') }}
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
        </dd>
      </template>

      <template v-if="resources.length">
        <dt class="text-muted-foreground">Resources</dt>
        <dd>
          <ul class="space-y-1">
            <li v-for="(r, i) in resources" :key="i">
              <a
                v-if="isHttpUrl(r.url)"
                :href="r.url"
                target="_blank"
                rel="noopener noreferrer"
                :class="linkClass"
                >{{ r.name }}<span class="sr-only"> (opens in a new tab)</span></a
              >
              <span v-else>{{ r.name }}</span>
              <!-- "Other resource" says nothing; name the type only when it is specific -->
              <span v-if="r.type !== 'other'" class="text-muted-foreground">
                · {{ RESOURCE_LABELS[r.type] ?? r.type }}</span
              >
              <span v-if="r.language" class="text-muted-foreground"> · {{ r.language }}</span>
              <span v-if="r.country_or_scope" class="text-muted-foreground">
                · {{ r.country_or_scope }}</span
              >
              <span class="text-muted-foreground tabular-nums">
                · verified {{ r.verified.date }}</span
              >
            </li>
          </ul>
        </dd>
      </template>
    </dl>
  </section>
</template>
