import { afterEach, describe, expect, it, vi } from 'vitest'
import {
  caSelection,
  cssHex,
  featureByResidue,
  fetchModel,
  filterVariants,
  proteinRegions,
  mapMissenseVariants,
  pickCanonicalModel,
  plddtColor,
  residuesByCategory,
  type ClinVarProteinVariant
} from '../alphafold'

const v = (over: Partial<ClinVarProteinVariant>): ClinVarProteinVariant => ({
  accession: 'VCV000012645',
  category: 'pathogenic',
  classification: 'Pathogenic',
  position: 3,
  protein_change: 'p.Ser3Trp',
  effect_category: 'missense',
  molecular_consequences: ['missense variant'],
  ...over
})

describe('pickCanonicalModel', () => {
  const entry = (acc: string, id: string) => ({
    entryId: id,
    uniprotAccession: acc,
    cifUrl: `https://x/${id}.cif`
  })

  it('picks the canonical accession, not an isoform, preferring fragment F1', () => {
    const entries = [
      entry('P35680-2', 'AF-P35680-2-F1'),
      entry('P35680', 'AF-P35680-F2'),
      entry('P35680', 'AF-P35680-F1')
    ]
    expect(pickCanonicalModel(entries, 'P35680')?.entryId).toBe('AF-P35680-F1')
  })

  it('returns null for no prediction or a non-array body', () => {
    expect(pickCanonicalModel([], 'Q8WZ42')).toBeNull()
    expect(pickCanonicalModel([entry('P35680-2', 'AF-P35680-2-F1')], 'P35680')).toBeNull()
    expect(pickCanonicalModel({ detail: 'x' }, 'P35680')).toBeNull()
  })
})

describe('plddtColor', () => {
  it('uses the four AlphaFold bins with exclusive lower bounds', () => {
    expect(cssHex(plddtColor(95))).toBe('#0053d6')
    expect(cssHex(plddtColor(90))).toBe('#65cbf3')
    expect(cssHex(plddtColor(70.5))).toBe('#65cbf3')
    expect(cssHex(plddtColor(70))).toBe('#ffdb13')
    expect(cssHex(plddtColor(50))).toBe('#ff7d45')
    expect(cssHex(plddtColor(0))).toBe('#ff7d45')
  })
})

describe('mapMissenseVariants', () => {
  const model = { uniprotStart: 1, uniprotEnd: 5, sequence: 'MASKL' }

  it('keeps missense variants whose residue, range and reference amino acid agree', () => {
    const { mapped, dropped } = mapMissenseVariants([v({})], { length: 5, model })
    expect(dropped).toBe(0)
    expect(mapped).toEqual([
      {
        accession: 'VCV000012645',
        residue: 3,
        proteinChange: 'p.Ser3Trp',
        category: 'pathogenic',
        classification: 'Pathogenic',
        reviewStatus: ''
      }
    ])
  })

  it('ignores non-missense variants without counting them', () => {
    const truncating = v({
      protein_change: 'p.Ser3Ter',
      effect_category: 'truncating',
      molecular_consequences: ['nonsense']
    })
    expect(mapMissenseVariants([truncating], { length: 5, model })).toEqual({
      mapped: [],
      dropped: 0
    })
  })

  it('drops missense variants that cannot be mapped', () => {
    const bad = [
      v({ position: 4 }), // HGVS residue disagrees with position
      v({ protein_change: 'p.Arg3Trp' }), // reference is Ser in the model sequence
      v({ position: 9, protein_change: 'p.Ser9Trp' }), // beyond protein length
      v({ protein_change: 'p.(Ser3_Lys4delinsTrp)' }), // not a single substitution
      v({ protein_change: undefined })
    ]
    expect(mapMissenseVariants(bad, { length: 5, model })).toEqual({ mapped: [], dropped: 5 })
  })

  it('drops residues outside a fragment model and skips the sequence check without one', () => {
    const fragment = { uniprotStart: 1, uniprotEnd: 2 }
    expect(mapMissenseVariants([v({})], { length: 5, model: fragment }).dropped).toBe(1)
    expect(
      mapMissenseVariants([v({ protein_change: 'p.Arg3Trp' })], { length: 5 }).mapped
    ).toHaveLength(1)
  })

  it('maps unknown categories to other and sorts by residue', () => {
    const { mapped } = mapMissenseVariants(
      [v({ position: 4, protein_change: 'p.Lys4Glu', category: 'drug_response' }), v({})],
      { length: 5, model }
    )
    expect(mapped.map(m => [m.residue, m.category])).toEqual([
      [3, 'pathogenic'],
      [4, 'other']
    ])
  })
})

describe('residuesByCategory', () => {
  it('assigns each residue once, to its most severe category', () => {
    const base = { accession: '', proteinChange: '', classification: '', reviewStatus: '' }
    const groups = residuesByCategory([
      { ...base, residue: 12, category: 'vus' },
      { ...base, residue: 12, category: 'likely_pathogenic' },
      { ...base, residue: 45, category: 'vus' },
      { ...base, residue: 7, category: 'pathogenic' }
    ])
    expect(Object.fromEntries(groups)).toEqual({
      pathogenic: [7],
      likely_pathogenic: [12],
      vus: [45]
    })
    expect(caSelection(groups.get('vus')!)).toBe('(45) and .CA')
    expect(caSelection([12, 45])).toBe('(12 or 45) and .CA')
  })
})

describe('proteinRegions', () => {
  it('lists domains and regions by start, without the chain, duplicates or bad ranges', () => {
    const regions = proteinRegions([
      { type: 'Chain', description: 'HNF1B', start: 1, end: 557 },
      { type: 'Domain', description: 'POU-specific atypical', start: 93, end: 188 },
      { type: 'Region', description: 'Dimerization', start: 1, end: 31 },
      { type: 'Region', description: 'Dimerization', start: 1, end: 31 },
      { type: 'Region', description: 'Broken', start: 50, end: 40 },
      { type: 'Region', description: 'No range' }
    ])
    expect(regions.map(r => [r.label, r.type, r.start, r.end])).toEqual([
      ['Dimerization', 'Region', 1, 31],
      ['POU-specific atypical', 'Domain', 93, 188]
    ])
  })
})

describe('featureByResidue', () => {
  it('paints specific features over broad regions and narrower over wider', () => {
    const regions = proteinRegions([
      { type: 'Region', description: 'Dimerization', start: 1, end: 31 },
      { type: 'Domain', description: 'HNF-p1', start: 1, end: 32 },
      { type: 'Region', description: 'Disordered', start: 60, end: 90 },
      { type: 'Region', description: 'Linker', start: 64, end: 70 }
    ])
    const at = featureByResidue(regions)
    expect(at.get(10)?.label).toBe('HNF-p1') // Domain beats the Region it overlaps
    expect(at.get(65)?.label).toBe('Linker') // the narrower Region wins inside the wider one
    expect(at.get(80)?.label).toBe('Disordered')
    expect(at.has(45)).toBe(false) // no feature: drawn as plain chain
  })
})

describe('filterVariants', () => {
  const base = { classification: '', reviewStatus: '' }
  const variants = [
    { ...base, accession: 'VCV1', residue: 20, proteinChange: 'p.Gly20Arg', category: 'vus' },
    {
      ...base,
      accession: 'VCV2',
      residue: 150,
      proteinChange: 'p.Arg150Trp',
      category: 'pathogenic'
    },
    { ...base, accession: 'VCV3', residue: 160, proteinChange: 'p.Ser160Leu', category: 'vus' }
  ]
  const all = ['pathogenic', 'vus']
  const ids = (f: Parameters<typeof filterVariants>[1]) =>
    filterVariants(variants, f).map(v => v.accession)

  it('combines classification, region and query', () => {
    expect(ids({ categories: ['vus'] })).toEqual(['VCV1', 'VCV3'])
    expect(ids({ categories: [] })).toEqual([])
    expect(ids({ categories: all, region: { start: 93, end: 188 } })).toEqual(['VCV2', 'VCV3'])
    expect(ids({ categories: ['vus'], region: { start: 93, end: 188 } })).toEqual(['VCV3'])
    expect(ids({ categories: all, query: ' arg150 ' })).toEqual(['VCV2'])
    expect(ids({ categories: all, query: 'vcv3' })).toEqual(['VCV3'])
    expect(ids({ categories: all, query: '20' })).toEqual(['VCV1'])
  })
})

describe('fetchModel', () => {
  afterEach(() => vi.unstubAllGlobals())
  const entry = { entryId: 'AF-Q00001-F1', uniprotAccession: 'Q00001', cifUrl: 'https://x/m.cif' }
  const ok = (body: unknown) => ({
    ok: true,
    status: 200,
    json: async () => body,
    blob: async () => new Blob(['cif'])
  })

  it('fetches metadata and model file once per accession', async () => {
    const fetch = vi
      .fn()
      .mockResolvedValueOnce(ok([entry]))
      .mockResolvedValueOnce(ok(null))
    vi.stubGlobal('fetch', fetch)
    const first = await fetchModel('Q00001')
    expect(first?.entry.entryId).toBe('AF-Q00001-F1')
    expect(await fetchModel('Q00001')).toBe(first)
    expect(fetch).toHaveBeenCalledTimes(2)
  })

  it('evicts a failed load so a retry fetches again', async () => {
    const fetch = vi
      .fn()
      .mockResolvedValueOnce({ ok: false, status: 503 })
      .mockResolvedValueOnce({ ok: false, status: 404 })
    vi.stubGlobal('fetch', fetch)
    await expect(fetchModel('Q00002')).rejects.toThrow('503')
    expect(await fetchModel('Q00002')).toBeNull()
    expect(fetch).toHaveBeenCalledTimes(2)
  })
})
