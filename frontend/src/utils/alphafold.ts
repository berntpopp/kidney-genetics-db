/**
 * AlphaFold DB model lookup and ClinVar missense mapping for the 3D protein structure view.
 * Pure helpers (no NGL, no DOM) so the mapping rules are unit tested.
 */
import { SIGNIFICANCE } from '@/components/gene/variantColors'

/** The fields of an AlphaFold DB /api/prediction entry this view uses */
export interface AlphaFoldEntry {
  entryId: string
  uniprotAccession: string
  latestVersion: number
  modelCreatedDate?: string
  cifUrl: string
  uniprotStart: number
  uniprotEnd: number
  sequence?: string
  globalMetricValue?: number
}

export const alphafoldApiUrl = (accession: string) =>
  `https://alphafold.ebi.ac.uk/api/prediction/${encodeURIComponent(accession)}`

export const alphafoldEntryUrl = (accession: string) =>
  `https://alphafold.ebi.ac.uk/entry/${encodeURIComponent(accession)}`

/**
 * The model of the canonical accession itself. The API also returns isoform models
 * (P35680-2, ...) and, for very long proteins, fragments (F1, F2, ...); prefer F1.
 */
export function pickCanonicalModel(entries: unknown, accession: string): AlphaFoldEntry | null {
  if (!Array.isArray(entries)) return null
  const own = (entries as AlphaFoldEntry[]).filter(
    e => e?.uniprotAccession === accession && typeof e.cifUrl === 'string'
  )
  return own.find(e => e.entryId?.endsWith('-F1')) ?? own[0] ?? null
}

/**
 * The canonical model from AlphaFold DB (a public CORS API, not our backend), or null when
 * there is no prediction (404/400 or an empty list). Network and 5xx errors throw.
 */
async function fetchCanonicalModel(accession: string): Promise<AlphaFoldEntry | null> {
  const res = await fetch(alphafoldApiUrl(accession))
  if (res.status === 404 || res.status === 400) return null
  if (!res.ok) throw new Error(`AlphaFold DB responded ${res.status}`)
  return pickCanonicalModel(await res.json(), accession)
}

export type AlphaFoldModel = { entry: AlphaFoldEntry; file: Blob } | null

// Per page session: the 3D tab remounts on every visit and EBI serves files with max-age=0
const modelCache = new Map<string, Promise<AlphaFoldModel>>()

/**
 * Metadata plus the mmCIF model file, fetched once per session per accession (null: no
 * prediction). A failed load is evicted so Retry fetches again.
 */
export function fetchModel(accession: string): Promise<AlphaFoldModel> {
  let model = modelCache.get(accession)
  if (!model) {
    model = fetchCanonicalModel(accession).then(async entry => {
      if (!entry) return null
      const res = await fetch(entry.cifUrl)
      if (!res.ok) throw new Error(`AlphaFold DB model download responded ${res.status}`)
      return { entry, file: await res.blob() }
    })
    model.catch(() => modelCache.delete(accession))
    modelCache.set(accession, model)
  }
  return model
}

/**
 * AlphaFold DB's published pLDDT bins. Numeric (NGL's colour format) because these are
 * AlphaFold's fixed palette, not design tokens: the legend must match alphafold.ebi.ac.uk.
 */
export const PLDDT_BINS = [
  { min: 90, color: 0x0053d6, label: 'Very high', range: 'pLDDT > 90' },
  { min: 70, color: 0x65cbf3, label: 'Confident', range: '90 ≥ pLDDT > 70' },
  { min: 50, color: 0xffdb13, label: 'Low', range: '70 ≥ pLDDT > 50' },
  { min: -Infinity, color: 0xff7d45, label: 'Very low', range: 'pLDDT ≤ 50' }
] as const

export const plddtColor = (plddt: number): number =>
  PLDDT_BINS.find(bin => plddt > bin.min)?.color ?? PLDDT_BINS[3].color

export const cssHex = (color: number) => `#${color.toString(16).padStart(6, '0')}`

/** ClinVar protein variant as stored in the clinvar annotation's protein_variants */
export interface ClinVarProteinVariant {
  accession?: string
  title?: string
  category?: string
  classification?: string
  position?: number
  protein_change?: string
  effect_category?: string
  molecular_consequences?: string[]
  review_status?: string
}

export interface MissenseVariant {
  accession: string
  residue: number
  proteinChange: string
  /** SIGNIFICANCE key, or 'other' */
  category: string
  classification: string
  reviewStatus: string
}

export const AA: Record<string, string> = {
  Ala: 'A', Arg: 'R', Asn: 'N', Asp: 'D', Cys: 'C', Gln: 'Q', Glu: 'E', Gly: 'G', His: 'H',
  Ile: 'I', Leu: 'L', Lys: 'K', Met: 'M', Phe: 'F', Pro: 'P', Ser: 'S', Thr: 'T', Trp: 'W',
  Tyr: 'Y', Val: 'V', Sec: 'U', Pyl: 'O'
} // prettier-ignore

// One substitution only: p.Ser148Trp (not Ter, =, fs, del, ext or ranges)
export const MISSENSE_HGVS = /^p\.\(?([A-Z][a-z]{2})(\d+)([A-Z][a-z]{2})\)?$/

/** Missense = ClinVar consequence "missense variant" (effect_category 'missense') */
const isMissense = (v: ClinVarProteinVariant) =>
  v.molecular_consequences?.includes('missense variant') ?? v.effect_category === 'missense'

/**
 * The ClinVar missense variants that map onto the model: the HGVS residue must agree with
 * `position`, lie inside the protein and model range, and (when the model sequence is
 * known) the reference amino acid must match it, which catches transcript/isoform offsets.
 * Everything else is counted in `dropped`, never guessed.
 */
export function mapMissenseVariants(
  variants: ClinVarProteinVariant[] | null | undefined,
  opts: {
    length?: number
    model?: Pick<AlphaFoldEntry, 'uniprotStart' | 'uniprotEnd' | 'sequence'>
  }
): { mapped: MissenseVariant[]; dropped: number } {
  const mapped: MissenseVariant[] = []
  let dropped = 0
  const start = opts.model?.uniprotStart ?? 1
  const end = Math.min(opts.model?.uniprotEnd ?? Infinity, opts.length ?? Infinity)
  for (const v of variants ?? []) {
    if (!isMissense(v)) continue
    const m = MISSENSE_HGVS.exec(v.protein_change ?? '')
    const residue = Number(m?.[2])
    const ref = m ? AA[m[1]!] : undefined
    const ok =
      m &&
      ref &&
      AA[m[3]!] &&
      m[1] !== m[3] &&
      residue === v.position &&
      residue >= start &&
      residue <= end &&
      (!opts.model?.sequence || opts.model.sequence[residue - start] === ref)
    if (!ok) {
      dropped += 1
      continue
    }
    mapped.push({
      accession: v.accession ?? '',
      residue,
      proteinChange: v.protein_change!,
      category: v.category && v.category in SIGNIFICANCE ? v.category : 'other',
      classification: v.classification ?? '',
      reviewStatus: v.review_status ?? ''
    })
  }
  mapped.sort((a, b) => a.residue - b.residue || a.proteinChange.localeCompare(b.proteinChange))
  return { mapped, dropped }
}

/** Most to least severe; a residue with several variants takes its most severe category */
export const CATEGORY_ORDER = [...Object.keys(SIGNIFICANCE), 'other']

/** category -> residues, each residue in exactly one group (its most severe category) */
export function residuesByCategory(variants: MissenseVariant[]): Map<string, number[]> {
  const best = new Map<number, number>()
  for (const v of variants) {
    const rank = CATEGORY_ORDER.indexOf(v.category)
    best.set(v.residue, Math.min(best.get(v.residue) ?? Infinity, rank))
  }
  const groups = new Map<string, number[]>()
  for (const [residue, rank] of [...best].sort((a, b) => a[0] - b[0])) {
    const key = CATEGORY_ORDER[rank]!
    groups.set(key, [...(groups.get(key) ?? []), residue])
  }
  return groups
}

/** A UniProt domain/region feature (uniprot annotation `domains`) */
export interface ProteinFeature {
  type?: string
  description?: string
  start?: number
  end?: number
}

export interface ProteinRegion {
  key: string
  label: string
  type: string
  start: number
  end: number
}

/** Domains and regions a variant filter can select: no whole-chain feature, valid ranges, by start */
export function proteinRegions(features: ProteinFeature[] | null | undefined): ProteinRegion[] {
  const seen = new Set<string>()
  return (features ?? [])
    .filter(f => f.type !== 'Chain' && Number.isInteger(f.start) && Number.isInteger(f.end))
    .filter(f => f.start! <= f.end!)
    .map(f => ({
      key: `${f.start}-${f.end}`,
      label: f.description || f.type || 'Region',
      type: f.type || 'Region',
      start: f.start!,
      end: f.end!
    }))
    .filter(r => !seen.has(r.key) && !!seen.add(r.key))
    .sort((a, b) => a.start - b.start || a.end - b.end)
}

/**
 * The feature drawn at each residue when colouring by domain: specific features (Domain,
 * Motif, ...) win over broad Regions, and narrower over wider, so nested features stay visible.
 */
export function featureByResidue(regions: ProteinRegion[]): Map<number, ProteinRegion> {
  const broad = (r: ProteinRegion) => (r.type === 'Region' ? 0 : 1)
  const paintOrder = [...regions].sort(
    (a, b) => broad(a) - broad(b) || b.end - b.start - (a.end - a.start)
  )
  const byResidue = new Map<number, ProteinRegion>()
  for (const r of paintOrder) for (let i = r.start; i <= r.end; i++) byResidue.set(i, r)
  return byResidue
}

/** Variants passing all filters: classifications (empty = none), optional region, free-text query */
export function filterVariants(
  variants: MissenseVariant[],
  f: { categories: string[]; region?: Pick<ProteinRegion, 'start' | 'end'> | null; query?: string }
): MissenseVariant[] {
  const q = f.query?.trim().toLowerCase() ?? ''
  return variants.filter(
    v =>
      f.categories.includes(v.category) &&
      (!f.region || (v.residue >= f.region.start && v.residue <= f.region.end)) &&
      (!q ||
        v.proteinChange.toLowerCase().includes(q) ||
        v.accession.toLowerCase().includes(q) ||
        String(v.residue) === q)
  )
}

/** NGL selection of the C-alpha atoms of these residues: "(12 or 45) and .CA" */
export const caSelection = (residues: number[]) => `(${residues.join(' or ')}) and .CA`
