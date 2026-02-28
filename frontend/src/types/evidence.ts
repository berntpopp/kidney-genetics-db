/**
 * Evidence source type definitions for kidney genetics database
 *
 * Per-source typed interfaces for all annotation sources.
 * EvidenceSource.source_data is typed as EvidenceData union.
 *
 * @module types/evidence
 */

// ---------------------------------------------------------------------------
// Per-source evidence data interfaces
// ---------------------------------------------------------------------------

export interface ClinGenValidity {
  disease: string
  classification: string
  moi: string
  panel: string
}

export interface ClinGenEvidenceData {
  validity_count: number
  validities: ClinGenValidity[]
  diseases: string[]
  classifications: string[]
  expert_panels: string[]
  modes_of_inheritance: string[]
  max_classification_score: number
  evidence_score: number
  last_updated: string
}

export interface GenCCSubmission {
  disease: string
  classification: string
  submitter: string
  moi: string
}

export interface GenCCEvidenceData {
  submission_count: number
  submissions: GenCCSubmission[]
  diseases: string[]
  classifications: string[]
  submitters: string[]
  modes_of_inheritance: string[]
  evidence_score: number
}

export interface HPOEvidenceData {
  hpo_terms: string[]
  term_count?: number
  evidence_score: number
}

export interface PanelAppEvidenceData {
  panel_count: number
  panels: string[]
  regions: string[]
  phenotypes: string[]
  modes_of_inheritance: string[]
  evidence_levels: string[]
  last_updated: string
}

export interface PubTatorEvidenceData {
  pmids: string[]
  publication_count: number
  total_mentions: number
  evidence_score: number
}

export interface DiagnosticPanelsEvidenceData {
  panels: string[]
  providers: string[]
  panel_count: number
  provider_count: number
}

export interface LiteratureEvidenceData {
  publications: string[]
  publication_count: number
  publication_details?: Record<string, unknown>
}

// ---------------------------------------------------------------------------
// Union types
// ---------------------------------------------------------------------------

/** Union of all known annotation source name literals */
export type AnnotationSourceName =
  | 'ClinGen'
  | 'GenCC'
  | 'HPO'
  | 'PanelApp'
  | 'PubTator'
  | 'DiagnosticPanels'
  | 'Literature'

/**
 * Union of all known per-source evidence data shapes.
 * Falls back to Record<string, unknown> for HGNC / gnomAD / GTEx / other sources
 * whose fields are not rendered by frontend views.
 */
export type EvidenceData =
  | ClinGenEvidenceData
  | GenCCEvidenceData
  | HPOEvidenceData
  | PanelAppEvidenceData
  | PubTatorEvidenceData
  | DiagnosticPanelsEvidenceData
  | LiteratureEvidenceData
  | Record<string, unknown>
