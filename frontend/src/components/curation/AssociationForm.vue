<script setup lang="ts">
import { watch } from 'vue'
import { z } from 'zod/v3'
import { toTypedSchema } from '@vee-validate/zod'
import { useForm } from 'vee-validate'
import { Input } from '@/components/ui/input'
import { Label } from '@/components/ui/label'
import { Button } from '@/components/ui/button'
import { EVIDENCE_STRENGTHS, type Association, type AssociationInput } from '@/api/curation'

const props = defineProps<{ record?: Association | null; busy?: boolean }>()
const emit = defineEmits<{ save: [input: AssociationInput]; cancel: [] }>()

const FIELDS = [
  'gene_symbol',
  'disease_id',
  'disease_name',
  'evidence_strength',
  'citations',
  'evidence_summary'
] as const

const splitCitations = (v: string) => v.split(/[\s,;]+/).filter(Boolean)

// Mirrors backend validation; the API stays authoritative
const schema = toTypedSchema(
  z.object({
    gene_symbol: z.string().trim().min(1, 'Gene symbol is required'),
    disease_id: z
      .string()
      .trim()
      .toUpperCase()
      .refine(v => !v.startsWith('HP:'), 'HPO terms describe phenotypes; use a MONDO or OMIM ID')
      .refine(v => /^(MONDO:\d{7}|OMIM:\d{6})$/.test(v), 'Use MONDO:NNNNNNN or OMIM:NNNNNN'),
    disease_name: z.string().trim().min(1, 'Disease name is required').max(255),
    evidence_strength: z.enum(EVIDENCE_STRENGTHS, {
      errorMap: () => ({ message: 'Select an evidence strength' })
    }),
    citations: z
      .string()
      .refine(v => splitCitations(v).length > 0, 'At least one PMID is required')
      .refine(
        v => splitCitations(v).every(c => /^(PMID:)?\d{1,9}$/i.test(c)),
        'Use PMIDs such as 12345678 or PMID:12345678'
      ),
    evidence_summary: z.string().max(2000).optional()
  })
)

const { handleSubmit, defineField, errors, resetForm } = useForm({ validationSchema: schema })
const opts = { validateOnBlur: true }
const [geneSymbol] = defineField('gene_symbol', opts)
const [diseaseId] = defineField('disease_id', opts)
const [diseaseName] = defineField('disease_name', opts)
const [strength] = defineField('evidence_strength', opts)
const [citations] = defineField('citations', opts)
const [summary] = defineField('evidence_summary', opts)

watch(
  () => props.record,
  r =>
    resetForm({
      values: r
        ? {
            gene_symbol: r.gene_symbol,
            disease_id: r.disease_id,
            disease_name: r.disease_name,
            evidence_strength: r.evidence_strength,
            citations: r.citations.join(', '),
            evidence_summary: r.evidence_summary ?? ''
          }
        : undefined
    }),
  { immediate: true }
)

const onSubmit = handleSubmit(
  values =>
    emit('save', {
      ...values,
      citations: splitCitations(values.citations),
      evidence_summary: values.evidence_summary?.trim() || null
    }),
  ({ errors: invalid }) => {
    // Move focus to the first invalid field so screen readers announce its error
    const first = FIELDS.find(f => invalid[f])
    if (first) document.getElementById(`gda-${first}`)?.focus()
  }
)

const describedBy = (f: (typeof FIELDS)[number], hint?: string) =>
  [errors.value[f] ? `gda-${f}-error` : '', hint ?? ''].filter(Boolean).join(' ') || undefined
const fieldClass =
  'flex w-full rounded-md border border-input bg-background px-3 py-2 text-sm focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring disabled:opacity-50'
</script>

<template>
  <form class="space-y-4" novalidate @submit.prevent="onSubmit">
    <div class="grid gap-4 sm:grid-cols-2">
      <div class="space-y-2">
        <Label for="gda-gene_symbol">Gene symbol</Label>
        <Input
          id="gda-gene_symbol"
          v-model="geneSymbol"
          :disabled="busy || !!record"
          :aria-invalid="!!errors.gene_symbol"
          :aria-describedby="describedBy('gene_symbol')"
        />
        <p v-if="errors.gene_symbol" id="gda-gene_symbol-error" class="text-sm text-destructive">
          {{ errors.gene_symbol }}
        </p>
      </div>
      <div class="space-y-2">
        <Label for="gda-disease_id">Disease ID (MONDO or OMIM)</Label>
        <Input
          id="gda-disease_id"
          v-model="diseaseId"
          placeholder="MONDO:0005300"
          :disabled="busy"
          :aria-invalid="!!errors.disease_id"
          :aria-describedby="describedBy('disease_id', 'gda-disease_id-hint')"
        />
        <p id="gda-disease_id-hint" class="text-xs text-muted-foreground">
          HPO terms describe phenotypes and are not accepted as disease IDs.
        </p>
        <p v-if="errors.disease_id" id="gda-disease_id-error" class="text-sm text-destructive">
          {{ errors.disease_id }}
        </p>
      </div>
      <div class="space-y-2">
        <Label for="gda-disease_name">Disease name</Label>
        <Input
          id="gda-disease_name"
          v-model="diseaseName"
          :disabled="busy"
          :aria-invalid="!!errors.disease_name"
          :aria-describedby="describedBy('disease_name')"
        />
        <p v-if="errors.disease_name" id="gda-disease_name-error" class="text-sm text-destructive">
          {{ errors.disease_name }}
        </p>
      </div>
      <div class="space-y-2">
        <Label for="gda-evidence_strength">Evidence strength</Label>
        <select
          id="gda-evidence_strength"
          v-model="strength"
          :class="fieldClass"
          :disabled="busy"
          :aria-invalid="!!errors.evidence_strength"
          :aria-describedby="describedBy('evidence_strength')"
        >
          <option value="" disabled>Select…</option>
          <option v-for="s in EVIDENCE_STRENGTHS" :key="s" :value="s">{{ s }}</option>
        </select>
        <p
          v-if="errors.evidence_strength"
          id="gda-evidence_strength-error"
          class="text-sm text-destructive"
        >
          {{ errors.evidence_strength }}
        </p>
      </div>
    </div>
    <div class="space-y-2">
      <Label for="gda-citations">PubMed citations</Label>
      <Input
        id="gda-citations"
        v-model="citations"
        placeholder="12345678, PMID:23456789"
        :disabled="busy"
        :aria-invalid="!!errors.citations"
        :aria-describedby="describedBy('citations')"
      />
      <p v-if="errors.citations" id="gda-citations-error" class="text-sm text-destructive">
        {{ errors.citations }}
      </p>
    </div>
    <div class="space-y-2">
      <Label for="gda-evidence_summary">Evidence summary (optional)</Label>
      <textarea
        id="gda-evidence_summary"
        v-model="summary"
        rows="3"
        maxlength="2000"
        :class="fieldClass"
        :disabled="busy"
        :aria-invalid="!!errors.evidence_summary"
        :aria-describedby="describedBy('evidence_summary')"
      />
      <p
        v-if="errors.evidence_summary"
        id="gda-evidence_summary-error"
        class="text-sm text-destructive"
      >
        {{ errors.evidence_summary }}
      </p>
    </div>
    <div class="flex gap-2">
      <Button type="submit" :disabled="busy">Save draft</Button>
      <Button
        v-if="record"
        type="button"
        variant="outline"
        :disabled="busy"
        @click="emit('cancel')"
      >
        Cancel
      </Button>
    </div>
  </form>
</template>
