/**
 * The source-specific facts behind one EvidenceCard (DESIGN.md Evidence card): a one-line
 * summary built only from structured fields (never the backend source_detail string, which
 * repeats the source name and its classifications), the stat row, the strongest
 * classification and the gene-specific link to the record at the source.
 */
import { getClassificationConfig } from '@/utils/evidenceTiers'
import type { HPOTermEntry } from '@/types/evidence'

type Data = Record<string, any>

export interface EvidenceStat {
  value: number
  unit: string
  tooltip?: string
}

export interface EvidenceMeta {
  summary: string
  stats: EvidenceStat[]
  /** Strongest ClinGen/GenCC classification, rendered as a strength chip */
  classification: string | null
  /** Record at the source for this gene; null when the source has no public page */
  link: { href: string; label: string } | null
}

export interface EvidenceGene {
  approved_symbol: string
  hgnc_id?: string | null
}

export interface EvidenceContext {
  ncbiGeneId?: string | number | null
}

/** HPO evidence terms as { id, name }; legacy rows store bare ID strings (#421) */
export const hpoTerms = (d: { hpo_terms?: HPOTermEntry[] }) =>
  (d.hpo_terms ?? []).map(t =>
    typeof t === 'string' ? { id: t, name: null } : { id: t.id, name: t.name ?? null }
  )

export const plural = (n: number, one: string, many = `${one}s`) => (n === 1 ? one : many)

const stat = (value: number, one: string, many?: string, tooltip?: string): EvidenceStat => ({
  value,
  unit: plural(value, one, many),
  ...(tooltip ? { tooltip } : {})
})

/** Strongest label by strength step; Disputed/Refuted/unknown rank below every strength */
export function strongestClassification(labels: (string | null | undefined)[]): string | null {
  let best: string | null = null
  let rank = -1
  for (const label of labels) {
    if (!label) continue
    const r = getClassificationConfig(label).strength ?? 0
    if (r > rank) [best, rank] = [label, r]
  }
  return best
}

const andMore = (first: string, more: number, unit: string) =>
  more > 0 ? `${first} and ${more} more ${plural(more, unit)}` : first

const classifiedFor = (classification: string | null, diseases: string[]) => {
  const unique = [...new Set(diseases.filter(Boolean))]
  if (!unique.length) return classification ? getClassificationConfig(classification).label : ''
  const what = andMore(unique[0]!, unique.length - 1, 'disease')
  return classification ? `${getClassificationConfig(classification).label} for ${what}` : what
}

const MOI: Record<string, string> = {
  AD: 'Autosomal dominant',
  AR: 'Autosomal recessive',
  XL: 'X-linked',
  XLD: 'X-linked dominant',
  XLR: 'X-linked recessive',
  MT: 'Mitochondrial',
  SD: 'Semidominant',
  YL: 'Y-linked'
}

/** "AD" -> "Autosomal dominant (AD)"; longer descriptions pass through */
export const formatInheritance = (moi: string | null | undefined) => {
  const key = (moi ?? '').trim()
  return MOI[key.toUpperCase()] ? `${MOI[key.toUpperCase()]} (${key})` : key
}

// PanelApp's fixed mode-of-inheritance vocabulary in the wording the GenCC/ClinGen cards use;
// the raw value stays in the tooltip, and unknown values pass through unchanged
const PANELAPP_MOI_LABELS: [RegExp, string][] = [
  [/^MONOALLELIC.*NOT imprinted/i, 'Autosomal dominant (monoallelic)'],
  [/^MONOALLELIC.*maternally imprinted/i, 'Autosomal dominant, maternally imprinted'],
  [/^MONOALLELIC.*paternally imprinted/i, 'Autosomal dominant, paternally imprinted'],
  [/^MONOALLELIC.*imprinted status unknown/i, 'Autosomal dominant, imprinting unknown'],
  [/^BIALLELIC/i, 'Autosomal recessive (biallelic)'],
  [/^BOTH.*more SEVERE/i, 'Autosomal dominant or recessive (biallelic more severe)'],
  [/^BOTH/i, 'Autosomal dominant or recessive'],
  [/^X-LINKED.*biallelic mutations in females/i, 'X-linked recessive'],
  [/^X-LINKED.*monoallelic mutations in females/i, 'X-linked, females may be affected'],
  [/^MITOCHONDRIAL/i, 'Mitochondrial'],
  [/^Other/i, 'Other'],
  [/^Unknown$/i, 'Unknown']
]
export const panelAppMoiLabel = (raw: string) =>
  PANELAPP_MOI_LABELS.find(([re]) => re.test(raw))?.[1] ?? raw

/** PanelApp panels deduplicated by region and panel ID (the payload repeats them) */
export const uniquePanels = (panels: Data[] = []) => [
  ...new Map(panels.map(p => [`${p.region}:${p.id}`, p])).values()
]

export interface PanelAppPhenotype {
  name: string
  omim: string | null
}

/**
 * PanelApp phenotypes are free text with embedded OMIM numbers ("Renal cysts and diabetes
 * syndrome, MIM#137920", "... 137920 AD"). Splits off the 6-digit OMIM number and the trailing
 * inheritance code, then deduplicates by name (keeping an entry that has an OMIM number).
 */
export function parsePanelAppPhenotypes(raw: string[] = []): PanelAppPhenotype[] {
  const byName = new Map<string, PanelAppPhenotype>()
  for (const text of raw) {
    const omim = text.match(/(?<!\d)(\d{6})(?!\d)/)?.[1] ?? null
    const name = text
      .replace(/(?<!\d)\d{6}(?!\d)/g, '')
      .replace(/\b(?:OMIM|MIM)\s*#?:?/gi, '')
      .replace(/[{}]/g, '')
      .replace(/\s+\b(?:AD|AR|XL|XLD|XLR)\s*$/, '')
      .replace(/[\s,;:#]+$/g, '')
      .replace(/\s+/g, ' ')
      .trim()
    if (!name) continue
    const key = name.toLowerCase()
    const seen = byName.get(key)
    if (!seen || (!seen.omim && omim)) byName.set(key, { name, omim: omim ?? seen?.omim ?? null })
  }
  // One row per OMIM entry: keep the longest spelling ("NIDDM" vs the full disease name)
  const byOmim = new Map<string, PanelAppPhenotype>()
  for (const [key, ph] of byName) {
    if (!ph.omim) continue
    const kept = byOmim.get(ph.omim)
    if (!kept) byOmim.set(ph.omim, ph)
    else byName.delete(kept.name.length >= ph.name.length ? key : kept.name.toLowerCase())
    if (kept && kept.name.length < ph.name.length) byOmim.set(ph.omim, ph)
  }
  return [...byName.values()].sort((a, b) => a.name.localeCompare(b.name))
}

/** Diagnostic-panel provider labels that are ingestion artefacts, not lab names */
export const isRealProvider = (provider: string) => !/^seeded from\b/i.test(provider.trim())

export function evidenceMeta(
  source: string,
  data: Data | null | undefined,
  gene: EvidenceGene,
  ctx: EvidenceContext = {}
): EvidenceMeta {
  const d: Data = data ?? {}
  const symbol = encodeURIComponent(gene.approved_symbol)
  const hgnc = gene.hgnc_id ?? d.hgnc_id ?? d.hgnc_ids?.[0] ?? null

  switch (source) {
    case 'ClinGen': {
      const validities: Data[] = d.validities ?? []
      const classification = strongestClassification(
        validities.length ? validities.map(v => v.classification) : (d.classifications ?? [])
      )
      const top = validities.find(v => v.classification === classification)
      const diseases = [
        top?.disease_name,
        ...validities.map(v => v.disease_name),
        ...(d.diseases ?? [])
      ]
      const count = d.validity_count ?? validities.length
      const panels = (d.expert_panels ?? []).length
      return {
        summary: classifiedFor(classification, diseases),
        stats: [stat(count, 'assessment'), ...(panels ? [stat(panels, 'expert panel')] : [])],
        classification,
        link: hgnc
          ? { href: `https://search.clinicalgenome.org/kb/genes/${hgnc}`, label: 'View on ClinGen' }
          : null
      }
    }
    case 'GenCC': {
      const submissions: Data[] = d.submissions ?? []
      const classification = strongestClassification(
        submissions.length ? submissions.map(s => s.classification) : (d.classifications ?? [])
      )
      const top = submissions.find(s => s.classification === classification)
      const diseases: string[] = d.diseases ?? []
      return {
        summary: classifiedFor(classification, [top?.disease_name, ...diseases]),
        stats: [
          stat(d.submission_count ?? submissions.length, 'submission'),
          stat((d.submitters ?? []).length, 'submitter'),
          stat(diseases.length, 'disease')
        ],
        classification,
        link: hgnc
          ? { href: `https://search.thegencc.org/genes/${hgnc}`, label: 'View on GenCC' }
          : null
      }
    }
    case 'HPO': {
      const terms = hpoTerms(d)
      const names = terms
        .map(t => t.name)
        .filter((n): n is string => !!n)
        .sort((a, b) => a.localeCompare(b))
      return {
        summary: names.length
          ? andMore(names.slice(0, 2).join(', '), terms.length - Math.min(names.length, 2), 'term')
          : 'Kidney phenotypes annotated to this gene',
        stats: [stat(terms.length, 'phenotype term')],
        classification: null,
        link: ctx.ncbiGeneId
          ? {
              href: `https://hpo.jax.org/browse/gene/NCBIGene:${ctx.ncbiGeneId}`,
              label: 'View on HPO'
            }
          : null
      }
    }
    case 'PanelApp': {
      const panels = uniquePanels(d.panels)
      const regions: string[] = d.regions ?? [...new Set(panels.map(p => p.region))]
      return {
        summary: panels.length
          ? andMore(panels[0]!.name, panels.length - 1, 'panel')
          : 'Listed on expert-reviewed gene panels',
        stats: [stat(panels.length, 'panel'), stat(regions.length, 'region')],
        classification: null,
        link: {
          href: `https://panelapp.genomicsengland.co.uk/panels/entities/${symbol}`,
          label: 'View on PanelApp'
        }
      }
    }
    case 'DiagnosticPanels': {
      const panels: string[] = d.provider_panels
        ? [...new Set(Object.values(d.provider_panels as Record<string, string[]>).flat())]
        : (d.panels ?? [])
      const providers = (
        d.provider_panels ? Object.keys(d.provider_panels) : (d.providers ?? [])
      ).filter(isRealProvider)
      return {
        summary: panels.length
          ? andMore([...panels].sort()[0]!, panels.length - 1, 'panel')
          : 'Listed on diagnostic gene panels',
        stats: [
          stat(panels.length, 'panel'),
          ...(providers.length ? [stat(providers.length, 'provider')] : [])
        ],
        classification: null,
        link: null
      }
    }
    case 'Literature': {
      const pmids: string[] = d.publications ?? Object.keys(d.publication_details ?? {})
      const count = d.publication_count ?? pmids.length
      return {
        summary: 'Curated from kidney-disease publications',
        stats: [stat(count, 'publication')],
        classification: null,
        link: pmids.length
          ? {
              href: `https://pubmed.ncbi.nlm.nih.gov/?term=${pmids.map(encodeURIComponent).join('+OR+')}`,
              label: 'View on PubMed'
            }
          : null
      }
    }
    case 'PubTator': {
      // Same deduplicated set PubTatorEvidence lists
      const sampled = new Set(
        (d.top_mentions ?? d.mentions ?? []).map((m: { pmid: unknown }) => m.pmid)
      ).size
      return {
        summary: `Text-mined mentions of ${gene.approved_symbol} in kidney-disease abstracts`,
        stats: [
          stat(d.publication_count ?? (d.pmids ?? []).length, 'publication'),
          ...(sampled
            ? [
                stat(
                  sampled,
                  'sampled mention',
                  undefined,
                  'Highest-scoring mention records retained for display; not a total mention count'
                )
              ]
            : [])
        ],
        classification: null,
        link: {
          href: `https://www.ncbi.nlm.nih.gov/research/pubtator3/docsum?text=${symbol}`,
          label: 'View on PubTator3'
        }
      }
    }
    default:
      return { summary: '', stats: [], classification: null, link: null }
  }
}
