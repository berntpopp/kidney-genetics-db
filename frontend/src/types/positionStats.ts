// Shapes of GET /api/genes/{symbol}/position-statistics (computed server-side).
import type { ProteinRegion } from '@/utils/alphafold'

export const DEFAULT_SEED = 20261031

export type DomainResult = ProteinRegion & {
  caseIn: number
  ctrlIn: number
  caseOut: number
  ctrlOut: number
  p: number
  or: number
  lo: number
  hi: number
  q: number
}

export type ScanResult = {
  windows: {
    start: number
    end: number
    centre: number
    cases: number
    ctrls: number
    p: number
    adjP: number
  }[]
  regions: {
    start: number
    end: number
    cases: number
    ctrls: number
    benign: number
    adjP: number
  }[]
  B: number
  seed: number
  w: number
}

export type ClusterResult = {
  observed: number
  nullMean: number
  nullLo: number
  nullHi: number
  p: number
  histogram: { x0: number; x1: number; n: number }[]
  nCaseResidues: number
  B: number
  seed: number
}

export type HotspotResult = {
  clusters: {
    residues: number[]
    residueAdjP: number[]
    cases: number
    ctrls: number
    adjP: number
  }[]
  B: number
  seed: number
  radius: number
}

export type VariantSetSummary = {
  cases: number
  controls: number
  benign: number
  dropped: { clinvar: number; gnomad: number }
  checked: { clinvar: number; gnomad: number }
}

export type PositionStatistics = {
  gene: string
  accession: string
  length: number
  status: 'ready' | 'withheld' | 'too-few'
  message: string | null
  variantSet: VariantSetSummary
  linear: { domains: DomainResult[]; scan: ScanResult } | null
  spatial: { cluster: ClusterResult | null; hotspots: HotspotResult } | null
  spatialMessage: string | null
  provenance: {
    clinvar: string
    gnomad: string
    uniprot: string
    alphafold: { entryId: string; version: number } | null
    minStars: number
    seed: number
  }
}
