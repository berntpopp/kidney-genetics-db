// Plain-language result sentences, generated from the numbers (never hand-written per gene).
import type { ClusterResult, DomainResult, HotspotResult, ScanResult } from '@/types/positionStats'

const ALPHA = 0.05

export const PM1_CAVEAT =
  'Statistical support for an ACMG/AMP PM1 assessment, not a classification. Population variants are not benign variants. Research use.'

/** p or q for display; a permutation p at its floor 1/(B+1) prints as "< floor". */
export function formatP(p: number, B?: number): string {
  if (B !== undefined && p <= 1 / (B + 1) + 1e-12) {
    return `< ${Number((1 / (B + 1)).toPrecision(1))}`
  }
  // Never round a significant value up to "0.05": floor to 3 decimals just below it.
  if (p >= 0.01)
    return p < ALPHA && p.toFixed(2) === '0.05'
      ? (Math.floor(p * 1000) / 1000).toFixed(3)
      : p.toFixed(2)
  if (p >= 0.001) return p.toFixed(3)
  return B === undefined ? '< 0.001' : String(Number(p.toPrecision(1)))
}

/** "p = 0.03" or "p < 0.001" */
export const pText = (name: string, p: number, B?: number) => {
  const s = formatP(p, B)
  return s.startsWith('<') ? `${name} ${s}` : `${name} = ${s}`
}

/** Odds ratio or CI bound: 0 and ∞ spelled out, one decimal below 10. */
export const formatOR = (x: number) =>
  !Number.isFinite(x)
    ? '∞'
    : x === 0
      ? '0'
      : x < 0.1
        ? String(Number(x.toPrecision(1)))
        : x < 10
          ? x.toFixed(1)
          : x.toFixed(0)

export const featureName = (r: { label: string; type: string }) => {
  const type = r.type.toLowerCase()
  return r.label.toLowerCase().endsWith(type) ? r.label : `${r.label} ${type}`
}

export const rangeText = (start: number, end: number) =>
  start === end ? `${start}` : `${start}–${end}`

export function domainSentence(results: DomainResult[]): string {
  if (results.length === 0) return 'UniProt lists no domains or regions to test.'
  const sig = results.filter(r => r.q < ALPHA).sort((a, b) => a.q - b.q)
  if (sig.length === 0) {
    return 'No domain is significantly enriched or depleted for pathogenic missense variants compared with population variants (all q ≥ 0.05).'
  }
  const top = sig[0]
  const enriched = top.or >= 1
  const fold = formatOR(enriched ? top.or : 1 / top.or)
  const ci = enriched
    ? `${formatOR(top.lo)}–${formatOR(top.hi)}`
    : `${formatOR(1 / top.hi)}–${formatOR(top.lo === 0 ? Infinity : 1 / top.lo)}`
  let s = `Pathogenic missense variants are ${fold}× ${enriched ? 'more' : 'less'} likely than population variants to fall in the ${featureName(top)} (95% CI ${ci}; ${pText('q', top.q)}).`
  const more = sig.length - 1
  if (more > 0) {
    s += ` ${more} other feature${more > 1 ? 's also differ' : ' also differs'} significantly.`
  }
  return s
}

export function scanSentence(scan: ScanResult): string {
  const regions = scan.regions
  if (regions.length === 0) {
    return `No stretch of the protein is significantly enriched for pathogenic missense variants (${scan.w}-residue windows, family-wise adjusted p ≥ 0.05).`
  }
  const ranges = regions.map(r => rangeText(r.start, r.end))
  const list =
    ranges.length === 1 ? ranges[0] : `${ranges.slice(0, -1).join(', ')} and ${ranges.at(-1)}`
  // Several regions: give the range of adjusted p, never only the best one.
  const ps = regions.map(r => r.adjP)
  const best = pText('p', Math.min(...ps), scan.B)
  const worst = formatP(Math.max(...ps), scan.B)
  const pRange = formatP(Math.min(...ps), scan.B) === worst ? best : `${best} to ${worst}`
  const benign = regions.reduce((n, r) => n + r.benign, 0)
  const them = regions.length === 1 ? 'it' : 'them'
  const benignText =
    benign === 0
      ? `no ClinVar benign or likely benign missense variant falls in ${them}`
      : `${benign} ClinVar benign or likely benign missense variant${benign > 1 ? 's fall' : ' falls'} in ${them}`
  return `Pathogenic missense variants cluster in residues ${list} (family-wise adjusted ${pRange}); ${benignText}.`
}

export function clusterSentence(c: ClusterResult): string {
  const d = `mean Cα distance ${c.observed.toFixed(1)} Å vs ${c.nullMean.toFixed(1)} Å expected`
  return c.p < ALPHA
    ? `Pathogenic missense residues lie closer together in the 3D structure than expected by chance (${d}; ${pText('p', c.p, c.B)}).`
    : `Pathogenic missense residues are not closer together in the 3D structure than expected by chance (${d}; ${pText('p', c.p, c.B)}, not significant).`
}

/** Sorted residue numbers as ranges: [140, 141, 142, 145] -> "140–142, 145" */
export function residueRanges(residues: number[]): string {
  const sorted = [...new Set(residues)].sort((a, b) => a - b)
  const out: string[] = []
  for (let i = 0; i < sorted.length;) {
    let j = i
    while (j + 1 < sorted.length && sorted[j + 1] === sorted[j]! + 1) j++
    out.push(rangeText(sorted[i]!, sorted[j]!))
    i = j + 1
  }
  return out.join(', ')
}

export function hotspotSentence(h: HotspotResult): string {
  const k = h.clusters.length
  if (k === 0) {
    return `No ${h.radius} Å neighbourhood in the 3D structure is significantly enriched for pathogenic missense variants (family-wise adjusted p ≥ 0.05).`
  }
  // A 3D cluster is not a sequence interval: name its residues, never one min–max span.
  const where = h.clusters.map(c => {
    const ranges = residueRanges(c.residues)
    if (ranges.split(', ').length <= 6) return `residues ${ranges}`
    const n = new Set(c.residues).size
    return `${n} residues spanning ${rangeText(Math.min(...c.residues), Math.max(...c.residues))} in sequence, close together in 3D`
  })
  const list = k === 1 ? where[0] : `${where.slice(0, -1).join('; ')} and ${where.at(-1)}`
  const best = Math.min(...h.clusters.map(c => c.adjP))
  return `Pathogenic missense variants concentrate in ${k === 1 ? 'one hotspot' : `${k} hotspots`} in the 3D structure: ${list} (${h.radius} Å neighbourhoods; best family-wise adjusted ${pText('p', best, h.B)}).`
}
