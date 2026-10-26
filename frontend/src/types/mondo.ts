/** MONDO annotation payload (gene_annotations.annotations, source "mondo", #28). */

export interface MondoDisease {
  mondo_id: string
  label: string | null
  source_ids: string[]
  sources: string[]
}

export interface MondoUnmapped {
  source_id: string
  sources: string[]
  reason: string
  candidates?: string[]
}

export interface MondoAnnotation {
  mondo_diseases: MondoDisease[]
  mapped_count: number
  unmapped: MondoUnmapped[]
  unmapped_count: number
  ambiguous: MondoUnmapped[]
  ambiguous_count: number
  provenance: {
    mondo_release: string
    sssom_url: string
    sssom_sha256: string
    predicate: string
    license: string
  }
}
