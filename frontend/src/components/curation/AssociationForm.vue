<script setup lang="ts">
import { computed, ref, watch } from 'vue'
import { z } from 'zod/v3'
import { toTypedSchema } from '@vee-validate/zod'
import { useForm } from 'vee-validate'
import { Input } from '@/components/ui/input'
import { Label } from '@/components/ui/label'
import { Button } from '@/components/ui/button'
import {
  EVIDENCE_STRENGTHS,
  MANE_LABELS,
  MANE_STATUSES,
  MOI_TERMS,
  RELATIONSHIP_LABELS,
  RELATIONSHIP_TYPES,
  RESOURCE_LABELS,
  RESOURCE_TYPES,
  VERIFIED_METHODS,
  isHttpUrl,
  strengthsFor,
  type Association,
  type AssociationInput,
  type Detectability,
  type RecommendedTranscript,
  type Diagnostics,
  type Resource
} from '@/api/curation'

const props = defineProps<{ record?: Association | null; busy?: boolean }>()
const emit = defineEmits<{ save: [input: AssociationInput]; cancel: [] }>()

const FIELDS = [
  'gene_symbol',
  'disease_id',
  'disease_name',
  'relationship_type',
  'risk_allele',
  'odds_ratio',
  'odds_ratio_ci_low',
  'odds_ratio_ci_high',
  'evidence_strength',
  'moi',
  'citations',
  'evidence_summary',
  'methodology',
  'methodology_version',
  'source',
  'external_id',
  'external_url',
  'external_curator',
  'external_reviewer',
  'score_genetic',
  'score_experimental',
  'score_total'
] as const

const num = (v: string | undefined) => (v?.trim() ? Number(v) : null)
const splitCitations = (v: string) => v.split(/[\s,;]+/).filter(Boolean)
const blank = (v: string | undefined | null) => v?.trim() || null
// Number inputs may hand back numbers; normalise to the string the other fields use
const score = z.preprocess(
  v => (v == null || v === '' ? undefined : String(v)),
  z
    .string()
    .optional()
    .refine(
      v => !v?.trim() || (Number(v) >= 0 && Number(v) <= 100),
      'Points must be between 0 and 100'
    )
)
const ratio = z.preprocess(
  v => (v == null || v === '' ? undefined : String(v)),
  z
    .string()
    .optional()
    .refine(v => !v?.trim() || Number(v) > 0, 'Must be greater than 0')
)

// Mirrors backend validation; the API stays authoritative
const schema = toTypedSchema(
  z
    .object({
      gene_symbol: z.string().trim().min(1, 'Gene symbol is required'),
      disease_id: z
        .string()
        .trim()
        .toUpperCase()
        .refine(v => !v.startsWith('HP:'), 'HPO terms describe phenotypes; use a MONDO or OMIM ID')
        .refine(v => /^(MONDO:\d{7}|OMIM:\d{6})$/.test(v), 'Use MONDO:NNNNNNN or OMIM:NNNNNN'),
      disease_name: z.string().trim().min(1, 'Disease name is required').max(255),
      relationship_type: z.enum(RELATIONSHIP_TYPES),
      risk_allele: z.string().max(100).optional(),
      odds_ratio: ratio,
      odds_ratio_ci_low: ratio,
      odds_ratio_ci_high: ratio,
      evidence_strength: z.enum(EVIDENCE_STRENGTHS, {
        errorMap: () => ({ message: 'Select an evidence strength' })
      }),
      moi: z.string().optional(),
      citations: z
        .string()
        // An adopted ClinGen classification may cite none; the backend allows [] only then
        .refine(
          v => !!props.record?.adopted_clingen || splitCitations(v).length > 0,
          'At least one PMID is required'
        )
        .refine(
          v => splitCitations(v).every(c => /^(PMID:)?\d{1,9}$/i.test(c)),
          'Use PMIDs such as 12345678 or PMID:12345678'
        ),
      evidence_summary: z.string().max(4000).optional(),
      methodology: z.string().max(100).optional(),
      methodology_version: z.string().max(50).optional(),
      source: z.enum(['kgdb', 'gene_curator']),
      external_id: z.string().max(100).optional(),
      external_url: z
        .string()
        .max(2000)
        .optional()
        .refine(
          v => !v?.trim() || isHttpUrl(v.trim()),
          'Links must start with http:// or https://'
        ),
      external_curator: z.string().max(255).optional(),
      external_reviewer: z.string().max(255).optional(),
      score_genetic: score,
      score_experimental: score,
      score_total: score
    })
    .superRefine((v, ctx) => {
      if (!(strengthsFor(v.relationship_type) as readonly string[]).includes(v.evidence_strength))
        ctx.addIssue({
          code: 'custom',
          path: ['evidence_strength'],
          message: `Select a ${v.relationship_type} classification`
        })
      if (v.relationship_type === 'susceptibility') {
        const [or, lo, hi] = [v.odds_ratio, v.odds_ratio_ci_low, v.odds_ratio_ci_high].map(num)
        const message =
          (lo !== null || hi !== null) && (or === null || lo === null || hi === null)
            ? 'Give the odds ratio and both CI bounds, or the odds ratio alone'
            : or !== null && lo !== null && hi !== null && !(lo <= or && or <= hi)
              ? 'The odds ratio must lie within its 95% CI'
              : null
        if (message) ctx.addIssue({ code: 'custom', path: ['odds_ratio'], message })
      }
      if (v.source === 'gene_curator') {
        if (!v.external_id?.trim())
          ctx.addIssue({
            code: 'custom',
            path: ['external_id'],
            message: 'External ID is required'
          })
        if (!v.external_url?.trim())
          ctx.addIssue({
            code: 'custom',
            path: ['external_url'],
            message: 'Link is required (http:// or https://)'
          })
      }
    })
)

const { handleSubmit, defineField, errors, resetForm, values } = useForm({
  validationSchema: schema,
  initialValues: { relationship_type: 'mendelian', source: 'kgdb' }
})
const opts = { validateOnBlur: true }
const [geneSymbol] = defineField('gene_symbol', opts)
const [diseaseId] = defineField('disease_id', opts)
const [diseaseName] = defineField('disease_name', opts)
const [relationshipType] = defineField('relationship_type', opts)
const [riskAllele] = defineField('risk_allele', opts)
const [oddsRatio] = defineField('odds_ratio', opts)
const [oddsRatioLow] = defineField('odds_ratio_ci_low', opts)
const [oddsRatioHigh] = defineField('odds_ratio_ci_high', opts)
const [strength] = defineField('evidence_strength', opts)
const [moi] = defineField('moi', opts)
const [citations] = defineField('citations', opts)
const [summary] = defineField('evidence_summary', opts)
const [methodology] = defineField('methodology', opts)
const [methodologyVersion] = defineField('methodology_version', opts)
const [source] = defineField('source', opts)
const [externalId] = defineField('external_id', opts)
const [externalUrl] = defineField('external_url', opts)
const [externalCurator] = defineField('external_curator', opts)
const [externalReviewer] = defineField('external_reviewer', opts)
const [scoreGenetic] = defineField('score_genetic', opts)
const [scoreExperimental] = defineField('score_experimental', opts)
const [scoreTotal] = defineField('score_total', opts)

const strengthOptions = computed(() => strengthsFor(values.relationship_type ?? 'mendelian'))
// A strength that does not fit the new relationship type is cleared, never silently kept
watch(
  () => values.relationship_type,
  type => {
    if (
      strength.value &&
      !(strengthsFor(type ?? 'mendelian') as readonly string[]).includes(strength.value)
    )
      strength.value = undefined
  }
)

/* Diagnostics (non-scoring, issue 439): plain rows, checked on submit */
interface TranscriptRow {
  refseq: string
  ensembl: string
  mane_status: string
  legacy_transcript: string
  numbering_conversion: string
  verified_via: string
}
interface DetectabilityRow {
  challenge: string
  share_of_variants: string
  methods: string
  negative_report_does_not_exclude: boolean
  raw: Detectability | null
}
interface ResourceRow {
  type: Resource['type']
  name: string
  url: string
  language: string
  country_or_scope: string
  method: Resource['verified']['method']
  date: string
  raw: Resource | null
}
const emptyTranscript = (): TranscriptRow => ({
  refseq: '',
  ensembl: '',
  mane_status: '',
  legacy_transcript: '',
  numbering_conversion: '',
  verified_via: ''
})
const transcript = ref<TranscriptRow>(emptyTranscript())
const detectability = ref<DetectabilityRow[]>([])
const detectabilityNote = ref('')
const resources = ref<ResourceRow[]>([])
const rowErrors = ref<Record<string, string>>({})

const addDetectability = () =>
  detectability.value.push({
    challenge: '',
    share_of_variants: '',
    methods: '',
    negative_report_does_not_exclude: false,
    raw: null
  })
const addResource = () =>
  resources.value.push({
    type: 'patient_organisation',
    name: '',
    url: '',
    language: '',
    country_or_scope: '',
    method: 'fetched',
    date: '',
    raw: null
  })

function loadDiagnostics(d: Diagnostics | null | undefined) {
  const t = d?.recommended_transcript
  transcript.value = t
    ? {
        refseq: t.refseq ?? '',
        ensembl: t.ensembl ?? '',
        mane_status: t.mane_status,
        legacy_transcript: t.legacy_transcript ?? '',
        numbering_conversion: t.numbering_conversion ?? '',
        verified_via: t.verified_via ?? ''
      }
    : emptyTranscript()
  detectabilityNote.value = d?.detectability_note ?? ''
  detectability.value = (d?.detectability ?? []).map(x => ({
    challenge: x.challenge,
    share_of_variants: x.share_of_variants ?? '',
    methods: x.methods.join(', '),
    negative_report_does_not_exclude: x.negative_report_does_not_exclude,
    raw: x
  }))
  resources.value = (d?.resources ?? []).map(x => ({
    type: x.type,
    name: x.name,
    url: x.url,
    language: x.language ?? '',
    country_or_scope: x.country_or_scope ?? '',
    method: x.verified.method,
    date: x.verified.date,
    raw: x
  }))
  rowErrors.value = {}
}

/** Rows -> API payload (null = no diagnostics); false and rowErrors when a row is incomplete */
function buildDiagnostics(): Diagnostics | null | false {
  const errs: Record<string, string> = {}
  const t = transcript.value
  const hasTranscript = [
    t.refseq,
    t.ensembl,
    t.legacy_transcript,
    t.numbering_conversion,
    t.verified_via
  ].some(v => v.trim())
  if (hasTranscript && !t.mane_status) errs.tx = 'Select the MANE status of the transcript'
  detectability.value.forEach((d, i) => {
    if (!d.challenge.trim()) errs[`det-${i}`] = 'Describe the detection challenge'
  })
  resources.value.forEach((r, i) => {
    if (!r.name.trim() || !isHttpUrl(r.url.trim()) || !r.date)
      errs[`res-${i}`] = 'Name, an http(s) link and the verification date are required'
    // A changed link was not checked on the old date: never carry that claim over
    else if (r.raw && r.url.trim() !== r.raw.url && r.date === r.raw.verified.date)
      errs[`res-${i}`] = 'The link changed: enter a new verification date'
  })
  rowErrors.value = errs
  if (Object.keys(errs).length) return false

  const diagnostics: Diagnostics = {
    recommended_transcript:
      hasTranscript || t.mane_status
        ? {
            refseq: blank(t.refseq),
            ensembl: blank(t.ensembl),
            mane_status: t.mane_status as RecommendedTranscript['mane_status'],
            legacy_transcript: blank(t.legacy_transcript),
            numbering_conversion: blank(t.numbering_conversion),
            verified_via: blank(t.verified_via)
          }
        : null,
    // Fields the editor does not show (tools, sources, ...) are kept from the loaded record
    detectability: detectability.value.map(d => ({
      affected_variants: null,
      tools: [],
      sources: [],
      ...d.raw,
      challenge: d.challenge.trim(),
      share_of_variants: blank(d.share_of_variants),
      methods: d.methods
        .split(/[,;]+/)
        .map(m => m.trim())
        .filter(Boolean),
      negative_report_does_not_exclude: d.negative_report_does_not_exclude
    })),
    detectability_note: blank(detectabilityNote.value),
    resources: resources.value.map(r => ({
      audiences: [],
      maintainer: null,
      conflict_of_interest: null,
      ...r.raw,
      type: r.type,
      name: r.name.trim(),
      url: r.url.trim(),
      language: blank(r.language),
      country_or_scope: blank(r.country_or_scope),
      verified: { method: r.method, date: r.date }
    }))
  }
  const empty =
    !diagnostics.recommended_transcript &&
    !diagnostics.detectability.length &&
    !diagnostics.detectability_note &&
    !diagnostics.resources.length
  return empty ? null : diagnostics
}

const ROW_FIELD: Record<string, string> = { det: 'challenge', res: 'name' }
function focusFirstRowError() {
  const key = Object.keys(rowErrors.value)[0]
  if (!key) return
  const [kind, i] = key.split('-')
  document
    .getElementById(kind === 'tx' ? 'gda-tx-refseq' : `gda-${kind}-${i}-${ROW_FIELD[kind!]}`)
    ?.focus()
}

const str = (v: number | null | undefined) => (v == null ? '' : String(v))

watch(
  () => props.record,
  r => {
    resetForm({
      values: r
        ? {
            gene_symbol: r.gene_symbol,
            disease_id: r.disease_id,
            disease_name: r.disease_name,
            relationship_type: r.relationship_type ?? 'mendelian',
            risk_allele: r.risk_allele ?? '',
            odds_ratio: str(r.odds_ratio),
            odds_ratio_ci_low: str(r.odds_ratio_ci_low),
            odds_ratio_ci_high: str(r.odds_ratio_ci_high),
            evidence_strength: r.evidence_strength,
            moi: r.moi ?? '',
            citations: r.citations.join(', '),
            evidence_summary: r.evidence_summary ?? '',
            methodology: r.methodology ?? '',
            methodology_version: r.methodology_version ?? '',
            source: r.source ?? 'kgdb',
            external_id: r.external_id ?? '',
            external_url: r.external_url ?? '',
            external_curator: r.external_curator ?? '',
            external_reviewer: r.external_reviewer ?? '',
            score_genetic: str(r.scores?.genetic),
            score_experimental: str(r.scores?.experimental),
            score_total: str(r.scores?.total)
          }
        : { relationship_type: 'mendelian', source: 'kgdb' }
    })
    loadDiagnostics(r?.diagnostics)
  },
  { immediate: true }
)

const onSubmit = handleSubmit(
  v => {
    const diagnostics = buildDiagnostics()
    if (diagnostics === false) {
      focusFirstRowError()
      return
    }
    const scores = {
      genetic: num(v.score_genetic),
      experimental: num(v.score_experimental),
      total: num(v.score_total),
      // No field for association points yet: keep an imported value instead of dropping it
      ...(props.record?.scores?.association != null && {
        association: props.record.scores.association
      })
    }
    const gc = v.source === 'gene_curator'
    emit('save', {
      gene_symbol: v.gene_symbol,
      disease_id: v.disease_id,
      disease_name: v.disease_name,
      evidence_strength: v.evidence_strength,
      citations: splitCitations(v.citations),
      evidence_summary: blank(v.evidence_summary),
      relationship_type: v.relationship_type,
      // Only a susceptibility entity names an allele (the backend refuses it otherwise)
      risk_allele: v.relationship_type === 'susceptibility' ? blank(v.risk_allele) : null,
      odds_ratio: v.relationship_type === 'susceptibility' ? num(v.odds_ratio) : null,
      odds_ratio_ci_low: v.relationship_type === 'susceptibility' ? num(v.odds_ratio_ci_low) : null,
      odds_ratio_ci_high:
        v.relationship_type === 'susceptibility' ? num(v.odds_ratio_ci_high) : null,
      moi: blank(v.moi),
      methodology: blank(v.methodology),
      methodology_version: blank(v.methodology_version),
      source: v.source,
      external_id: gc ? blank(v.external_id) : null,
      external_url: gc ? blank(v.external_url) : null,
      external_curator: gc ? blank(v.external_curator) : null,
      external_reviewer: gc ? blank(v.external_reviewer) : null,
      scores: Object.values(scores).some(x => x !== null) ? scores : null,
      diagnostics
    })
  },
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
  <form class="space-y-6" novalidate @submit.prevent="onSubmit">
    <fieldset class="space-y-4">
      <legend class="mb-2 text-sm font-medium">Classification</legend>
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
          <p
            v-if="errors.disease_name"
            id="gda-disease_name-error"
            class="text-sm text-destructive"
          >
            {{ errors.disease_name }}
          </p>
        </div>
        <div class="space-y-2">
          <Label for="gda-relationship_type">Relationship</Label>
          <select
            id="gda-relationship_type"
            v-model="relationshipType"
            :class="fieldClass"
            :disabled="busy"
          >
            <option v-for="t in RELATIONSHIP_TYPES" :key="t" :value="t">
              {{ RELATIONSHIP_LABELS[t] }}
            </option>
          </select>
        </div>
        <div class="space-y-2">
          <Label for="gda-evidence_strength">{{
            relationshipType === 'susceptibility' ? 'Risk association' : 'Evidence strength'
          }}</Label>
          <select
            id="gda-evidence_strength"
            v-model="strength"
            :class="fieldClass"
            :disabled="busy"
            :aria-invalid="!!errors.evidence_strength"
            :aria-describedby="describedBy('evidence_strength')"
          >
            <option value="" disabled>Select…</option>
            <option v-for="s in strengthOptions" :key="s" :value="s">{{ s }}</option>
          </select>
          <p
            v-if="errors.evidence_strength"
            id="gda-evidence_strength-error"
            class="text-sm text-destructive"
          >
            {{ errors.evidence_strength }}
          </p>
        </div>
        <div v-if="relationshipType === 'susceptibility'" class="space-y-2">
          <Label for="gda-risk_allele">Risk allele (optional)</Label>
          <Input
            id="gda-risk_allele"
            v-model="riskAllele"
            maxlength="100"
            placeholder="rs4664308 A"
            :disabled="busy"
          />
        </div>
        <div v-if="relationshipType === 'susceptibility'" class="space-y-2">
          <Label for="gda-odds_ratio">Odds ratio, 95% CI (optional)</Label>
          <div class="grid grid-cols-3 gap-2">
            <Input
              id="gda-odds_ratio"
              v-model="oddsRatio"
              type="number"
              min="0"
              step="any"
              aria-label="Odds ratio"
              :disabled="busy"
              :aria-invalid="!!errors.odds_ratio"
              :aria-describedby="describedBy('odds_ratio')"
            />
            <Input
              id="gda-odds_ratio_ci_low"
              v-model="oddsRatioLow"
              type="number"
              min="0"
              step="any"
              aria-label="95% CI lower"
              :disabled="busy"
              :aria-invalid="!!errors.odds_ratio_ci_low"
              :aria-describedby="describedBy('odds_ratio_ci_low')"
            />
            <Input
              id="gda-odds_ratio_ci_high"
              v-model="oddsRatioHigh"
              type="number"
              min="0"
              step="any"
              aria-label="95% CI upper"
              :disabled="busy"
              :aria-invalid="!!errors.odds_ratio_ci_high"
              :aria-describedby="describedBy('odds_ratio_ci_high')"
            />
          </div>
          <p
            v-for="f in ['odds_ratio', 'odds_ratio_ci_low', 'odds_ratio_ci_high'] as const"
            v-show="errors[f]"
            :id="`gda-${f}-error`"
            :key="f"
            class="text-sm text-destructive"
          >
            {{ errors[f] }}
          </p>
        </div>
        <div class="space-y-2">
          <Label for="gda-moi">Mode of inheritance (optional)</Label>
          <select id="gda-moi" v-model="moi" :class="fieldClass" :disabled="busy">
            <option value="">Not specified</option>
            <option v-for="(label, id) in MOI_TERMS" :key="id" :value="id">
              {{ label }} ({{ id }})
            </option>
          </select>
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
          maxlength="4000"
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
    </fieldset>

    <fieldset class="space-y-4">
      <legend class="mb-2 text-sm font-medium">Methodology &amp; provenance</legend>
      <div class="grid gap-4 sm:grid-cols-2">
        <div class="space-y-2">
          <Label for="gda-methodology">Methodology (optional)</Label>
          <Input
            id="gda-methodology"
            v-model="methodology"
            maxlength="100"
            placeholder="Kidney Gene Curation"
            :disabled="busy"
          />
        </div>
        <div class="space-y-2">
          <Label for="gda-methodology_version">Methodology version (optional)</Label>
          <Input
            id="gda-methodology_version"
            v-model="methodologyVersion"
            maxlength="50"
            placeholder="draft iteration 3"
            :disabled="busy"
          />
        </div>
        <div class="space-y-2">
          <Label for="gda-source">Curated in</Label>
          <select id="gda-source" v-model="source" :class="fieldClass" :disabled="busy">
            <option value="kgdb">KGDB</option>
            <option value="gene_curator">Gene Curator</option>
          </select>
        </div>
      </div>
      <div v-if="source === 'gene_curator'" class="grid gap-4 sm:grid-cols-2">
        <div class="space-y-2">
          <Label for="gda-external_id">Gene Curator ID</Label>
          <Input
            id="gda-external_id"
            v-model="externalId"
            maxlength="100"
            :disabled="busy"
            :aria-invalid="!!errors.external_id"
            :aria-describedby="describedBy('external_id')"
          />
          <p v-if="errors.external_id" id="gda-external_id-error" class="text-sm text-destructive">
            {{ errors.external_id }}
          </p>
        </div>
        <div class="space-y-2">
          <Label for="gda-external_url">Gene Curator link</Label>
          <Input
            id="gda-external_url"
            v-model="externalUrl"
            type="url"
            placeholder="https://"
            :disabled="busy"
            :aria-invalid="!!errors.external_url"
            :aria-describedby="describedBy('external_url')"
          />
          <p
            v-if="errors.external_url"
            id="gda-external_url-error"
            class="text-sm text-destructive"
          >
            {{ errors.external_url }}
          </p>
        </div>
        <div class="space-y-2">
          <Label for="gda-external_curator">Gene Curator curator (optional)</Label>
          <Input
            id="gda-external_curator"
            v-model="externalCurator"
            maxlength="255"
            :disabled="busy"
          />
        </div>
        <div class="space-y-2">
          <Label for="gda-external_reviewer">Gene Curator reviewer (optional)</Label>
          <Input
            id="gda-external_reviewer"
            v-model="externalReviewer"
            maxlength="255"
            :disabled="busy"
          />
        </div>
      </div>
      <div class="grid gap-4 sm:grid-cols-3">
        <div class="space-y-2">
          <Label for="gda-score_genetic">Genetic points (optional)</Label>
          <Input
            id="gda-score_genetic"
            v-model="scoreGenetic"
            type="number"
            min="0"
            max="100"
            step="0.5"
            :disabled="busy"
            :aria-invalid="!!errors.score_genetic"
            :aria-describedby="describedBy('score_genetic')"
          />
          <p
            v-if="errors.score_genetic"
            id="gda-score_genetic-error"
            class="text-sm text-destructive"
          >
            {{ errors.score_genetic }}
          </p>
        </div>
        <div class="space-y-2">
          <Label for="gda-score_experimental">Experimental points (optional)</Label>
          <Input
            id="gda-score_experimental"
            v-model="scoreExperimental"
            type="number"
            min="0"
            max="100"
            step="0.5"
            :disabled="busy"
            :aria-invalid="!!errors.score_experimental"
            :aria-describedby="describedBy('score_experimental')"
          />
          <p
            v-if="errors.score_experimental"
            id="gda-score_experimental-error"
            class="text-sm text-destructive"
          >
            {{ errors.score_experimental }}
          </p>
        </div>
        <div class="space-y-2">
          <Label for="gda-score_total">Total points (optional)</Label>
          <Input
            id="gda-score_total"
            v-model="scoreTotal"
            type="number"
            min="0"
            max="100"
            step="0.5"
            :disabled="busy"
            :aria-invalid="!!errors.score_total"
            :aria-describedby="describedBy('score_total')"
          />
          <p v-if="errors.score_total" id="gda-score_total-error" class="text-sm text-destructive">
            {{ errors.score_total }}
          </p>
        </div>
      </div>
    </fieldset>

    <fieldset class="space-y-4">
      <legend class="mb-2 text-sm font-medium">Diagnostics &amp; resources (not scored)</legend>
      <div class="grid gap-4 sm:grid-cols-3" :data-row-error="rowErrors.tx ? '' : undefined">
        <div class="space-y-2">
          <Label for="gda-tx-refseq">RefSeq transcript</Label>
          <Input
            id="gda-tx-refseq"
            v-model="transcript.refseq"
            placeholder="NM_000000.0"
            :disabled="busy"
          />
        </div>
        <div class="space-y-2">
          <Label for="gda-tx-ensembl">Ensembl transcript</Label>
          <Input
            id="gda-tx-ensembl"
            v-model="transcript.ensembl"
            placeholder="ENST00000000000.0"
            :disabled="busy"
          />
        </div>
        <div class="space-y-2">
          <Label for="gda-tx-mane">MANE status</Label>
          <select
            id="gda-tx-mane"
            v-model="transcript.mane_status"
            :class="fieldClass"
            :disabled="busy"
          >
            <option value="">—</option>
            <option v-for="m in MANE_STATUSES" :key="m" :value="m">{{ MANE_LABELS[m] }}</option>
          </select>
        </div>
        <div class="space-y-2">
          <Label for="gda-tx-legacy">Literature transcript</Label>
          <Input id="gda-tx-legacy" v-model="transcript.legacy_transcript" :disabled="busy" />
        </div>
        <div class="space-y-2 sm:col-span-2">
          <Label for="gda-tx-numbering">Numbering conversion note</Label>
          <Input
            id="gda-tx-numbering"
            v-model="transcript.numbering_conversion"
            maxlength="500"
            :disabled="busy"
          />
        </div>
        <div class="space-y-2 sm:col-span-3">
          <Label for="gda-tx-verified_via">Transcript verified via (tool and field)</Label>
          <Input
            id="gda-tx-verified_via"
            v-model="transcript.verified_via"
            maxlength="300"
            :disabled="busy"
          />
        </div>
        <p v-if="rowErrors.tx" class="text-sm text-destructive sm:col-span-3">
          {{ rowErrors.tx }}
        </p>
      </div>

      <div class="space-y-3">
        <h4 class="text-sm font-medium">Detectability limits</h4>
        <div class="space-y-2">
          <Label for="gda-det-note">Detectability note (optional)</Label>
          <Input
            id="gda-det-note"
            v-model="detectabilityNote"
            maxlength="500"
            placeholder="e.g. standard short-read testing adequate"
            :disabled="busy"
          />
        </div>
        <div
          v-for="(d, i) in detectability"
          :key="`det-${i}`"
          class="grid gap-3 rounded-md border p-3 sm:grid-cols-2"
          :data-row-error="rowErrors[`det-${i}`] ? '' : undefined"
        >
          <div class="space-y-2 sm:col-span-2">
            <Label :for="`gda-det-${i}-challenge`">Challenge</Label>
            <Input
              :id="`gda-det-${i}-challenge`"
              v-model="d.challenge"
              maxlength="300"
              :disabled="busy"
            />
          </div>
          <div class="space-y-2">
            <Label :for="`gda-det-${i}-share`">Share of variants (optional)</Label>
            <Input
              :id="`gda-det-${i}-share`"
              v-model="d.share_of_variants"
              maxlength="100"
              :disabled="busy"
            />
          </div>
          <div class="space-y-2">
            <Label :for="`gda-det-${i}-methods`">Methods, comma-separated (optional)</Label>
            <Input :id="`gda-det-${i}-methods`" v-model="d.methods" :disabled="busy" />
          </div>
          <div class="flex items-center gap-2 sm:col-span-2">
            <input
              :id="`gda-det-${i}-negative`"
              v-model="d.negative_report_does_not_exclude"
              type="checkbox"
              class="size-4 rounded border-input focus-visible:ring-2 focus-visible:ring-ring"
              :disabled="busy"
            />
            <Label :for="`gda-det-${i}-negative`"
              >A negative short-read result does not exclude a variant</Label
            >
          </div>
          <p
            v-if="rowErrors[`det-${i}`]"
            :id="`gda-det-${i}-error`"
            class="text-sm text-destructive sm:col-span-2"
          >
            {{ rowErrors[`det-${i}`] }}
          </p>
          <Button
            type="button"
            variant="outline"
            size="sm"
            class="justify-self-start"
            :disabled="busy"
            @click="detectability.splice(i, 1)"
          >
            Remove limit {{ i + 1 }}
          </Button>
        </div>
        <Button
          type="button"
          variant="outline"
          size="sm"
          data-testid="add-detectability"
          :disabled="busy"
          @click="addDetectability"
        >
          Add detectability limit
        </Button>
      </div>

      <div class="space-y-3">
        <h4 class="text-sm font-medium">Resources</h4>
        <div
          v-for="(r, i) in resources"
          :key="`res-${i}`"
          class="grid gap-3 rounded-md border p-3 sm:grid-cols-3"
          :data-row-error="rowErrors[`res-${i}`] ? '' : undefined"
        >
          <div class="space-y-2">
            <Label :for="`gda-res-${i}-type`">Type</Label>
            <select :id="`gda-res-${i}-type`" v-model="r.type" :class="fieldClass" :disabled="busy">
              <option v-for="t in RESOURCE_TYPES" :key="t" :value="t">
                {{ RESOURCE_LABELS[t] }}
              </option>
            </select>
          </div>
          <div class="space-y-2">
            <Label :for="`gda-res-${i}-name`">Name</Label>
            <Input :id="`gda-res-${i}-name`" v-model="r.name" maxlength="200" :disabled="busy" />
          </div>
          <div class="space-y-2">
            <Label :for="`gda-res-${i}-url`">Link</Label>
            <Input
              :id="`gda-res-${i}-url`"
              v-model="r.url"
              type="url"
              placeholder="https://"
              :disabled="busy"
            />
          </div>
          <div class="space-y-2">
            <Label :for="`gda-res-${i}-language`">Language (optional)</Label>
            <Input
              :id="`gda-res-${i}-language`"
              v-model="r.language"
              maxlength="20"
              :disabled="busy"
            />
          </div>
          <div class="space-y-2">
            <Label :for="`gda-res-${i}-country`">Country or scope (optional)</Label>
            <Input
              :id="`gda-res-${i}-country`"
              v-model="r.country_or_scope"
              maxlength="100"
              :disabled="busy"
            />
          </div>
          <div class="space-y-2">
            <Label :for="`gda-res-${i}-method`">Verified by</Label>
            <select
              :id="`gda-res-${i}-method`"
              v-model="r.method"
              :class="fieldClass"
              :disabled="busy"
            >
              <option v-for="m in VERIFIED_METHODS" :key="m" :value="m">
                {{ m.replaceAll('_', ' ') }}
              </option>
            </select>
          </div>
          <div class="space-y-2">
            <Label :for="`gda-res-${i}-date`">Verified on</Label>
            <Input :id="`gda-res-${i}-date`" v-model="r.date" type="date" :disabled="busy" />
          </div>
          <p
            v-if="rowErrors[`res-${i}`]"
            :id="`gda-res-${i}-error`"
            class="text-sm text-destructive sm:col-span-3"
          >
            {{ rowErrors[`res-${i}`] }}
          </p>
          <Button
            type="button"
            variant="outline"
            size="sm"
            class="justify-self-start"
            :disabled="busy"
            @click="resources.splice(i, 1)"
          >
            Remove resource {{ i + 1 }}
          </Button>
        </div>
        <Button
          type="button"
          variant="outline"
          size="sm"
          data-testid="add-resource"
          :disabled="busy"
          @click="addResource"
        >
          Add resource
        </Button>
      </div>
    </fieldset>

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
