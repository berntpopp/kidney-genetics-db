/**
 * Colours for ClinVar clinical significance, variant effect and protein feature type, shared
 * by the ClinVar chips and the gene-structure / protein-domain plots so both read the same.
 *
 * Clinical significance is not evidence strength, so it never uses the strength ramp. It is
 * a risk axis, so it borrows the status tones with labels as the non-colour cue: pathogenic
 * and likely pathogenic -> danger, uncertain (VUS, conflicting) -> warning, benign and likely
 * benign -> neutral (green is reserved for success). "Likely" steps are the same hue mixed
 * toward the canvas. Effects and feature types are categories, so they use the chart series
 * tokens --source-n.
 */
import type { StatusTone } from '@/utils/status'

const mix = (token: string, pct: number) =>
  `color-mix(in oklab, var(${token}) ${pct}%, var(--background))`

export interface SignificanceConfig {
  label: string
  /** Chip tone (STATUS_TONE_CLASSES) */
  tone: StatusTone
  /** Plot colour (CSS; resolve with computedColor for SVG/canvas) */
  color: string
  description: string
}

export const SIGNIFICANCE: Record<string, SignificanceConfig> = {
  pathogenic: {
    label: 'Pathogenic',
    tone: 'danger',
    color: 'var(--danger)',
    description: 'Classified as disease-causing in ClinVar'
  },
  likely_pathogenic: {
    label: 'Likely pathogenic',
    tone: 'danger',
    color: mix('--danger', 55),
    description: 'Probably disease-causing (>90% certainty) in ClinVar'
  },
  vus: {
    label: 'VUS',
    tone: 'warning',
    color: 'var(--warning)',
    description: 'Variant of uncertain significance: not enough evidence either way'
  },
  conflicting: {
    label: 'Conflicting',
    tone: 'warning',
    color: mix('--warning', 55),
    description: 'Submitters disagree on the classification'
  },
  likely_benign: {
    label: 'Likely benign',
    tone: 'neutral',
    color: mix('--muted-foreground', 55),
    description: 'Probably not disease-causing (>90% certainty) in ClinVar'
  },
  benign: {
    label: 'Benign',
    tone: 'neutral',
    color: 'var(--muted-foreground)',
    description: 'Classified as not disease-causing in ClinVar'
  }
}

const OTHER = mix('--muted-foreground', 30)

export const significanceColor = (category: string | null | undefined) =>
  SIGNIFICANCE[category ?? '']?.color ?? OTHER

export const EFFECTS: Record<string, { label: string; color: string; description: string }> = {
  truncating: {
    label: 'Truncating',
    color: 'var(--source-6)',
    description: 'Nonsense, frameshift or essential splice-site variants'
  },
  missense: { label: 'Missense', color: 'var(--source-1)', description: 'Amino-acid substitution' },
  inframe: {
    label: 'In-frame',
    color: 'var(--source-3)',
    description: 'In-frame insertion or deletion'
  },
  splice_region: {
    label: 'Splice region',
    color: 'var(--source-4)',
    description: 'Near a splice site, outside the essential positions'
  },
  synonymous: {
    label: 'Synonymous',
    color: 'var(--source-5)',
    description: 'No change to the amino acid'
  },
  other: { label: 'Other', color: 'var(--source-8)', description: 'Any other consequence' }
}

export const effectColor = (effect: string | null | undefined) =>
  EFFECTS[effect ?? '']?.color ?? EFFECTS.other!.color

export const FEATURE_COLORS: Record<string, string> = {
  Domain: 'var(--source-1)',
  Region: 'var(--source-3)',
  Motif: 'var(--source-2)',
  Transmembrane: 'var(--source-6)',
  Signal: 'var(--source-5)',
  Propeptide: 'var(--source-4)',
  Chain: 'var(--source-8)'
}

export const featureColor = (type: string | null | undefined) =>
  FEATURE_COLORS[type ?? ''] ?? 'var(--source-8)'

/**
 * The computed colour of any CSS colour (var(), color-mix()), for SVG attributes that must
 * survive serialisation (PNG export) and for canvas. Re-run after a theme change.
 */
export function computedColor(css: string, el?: Element | null): string {
  if (typeof document === 'undefined') return css
  const probe = document.createElement('span')
  probe.style.color = css
  probe.style.display = 'none'
  ;(el ?? document.body).appendChild(probe)
  const value = window.getComputedStyle(probe).color
  probe.remove()
  return value || css
}
