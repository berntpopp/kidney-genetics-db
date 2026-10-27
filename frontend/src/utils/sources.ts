/**
 * Evidence sources: one display name, description, chart colour and homepage per backend
 * source name (gene_evidence.source_name). Chart colours follow one fixed order over the
 * Okabe-Ito tokens --source-1..8 (assets/main.css); they are for chart series, legends and
 * the small marker dot only, never for text or card backgrounds (DESIGN.md).
 */

import type { AnnotationSourceName } from '@/types/evidence'

export type SourceName = AnnotationSourceName

export interface SourceConfig {
  displayName: string
  description: string
  chartColor: string
  /** Source homepage; null when the source has no single public site */
  homepage: string | null
}

export const SOURCE_CONFIG: Record<SourceName, SourceConfig> = {
  ClinGen: {
    displayName: 'ClinGen',
    description:
      'Expert-panel gene-disease validity classifications from the Clinical Genome Resource',
    chartColor: 'var(--source-1)',
    homepage: 'https://clinicalgenome.org/'
  },
  GenCC: {
    displayName: 'GenCC',
    description:
      'Gene-disease classifications harmonised across submitters by the Gene Curation Coalition',
    chartColor: 'var(--source-2)',
    homepage: 'https://thegencc.org/'
  },
  PanelApp: {
    displayName: 'PanelApp',
    description:
      'Expert-reviewed diagnostic gene panels from Genomics England and PanelApp Australia',
    chartColor: 'var(--source-3)',
    homepage: 'https://panelapp.genomicsengland.co.uk/'
  },
  HPO: {
    displayName: 'HPO',
    description:
      'Gene-phenotype annotations for kidney phenotypes from the Human Phenotype Ontology',
    chartColor: 'var(--source-4)',
    homepage: 'https://hpo.jax.org/'
  },
  Literature: {
    displayName: 'Literature',
    description: 'Genes curated from kidney-disease publications',
    chartColor: 'var(--source-5)',
    homepage: 'https://pubmed.ncbi.nlm.nih.gov/'
  },
  DiagnosticPanels: {
    displayName: 'Diagnostic panels',
    description: 'Genes on commercial and academic kidney diagnostic panels',
    chartColor: 'var(--source-6)',
    homepage: null
  },
  PubTator: {
    displayName: 'PubTator3',
    description: 'Text-mined gene mentions in kidney-disease literature from NCBI PubTator3',
    chartColor: 'var(--source-7)',
    homepage: 'https://www.ncbi.nlm.nih.gov/research/pubtator3/'
  }
}

/** Source names in their fixed chart order */
export const SOURCE_NAMES = Object.keys(SOURCE_CONFIG) as SourceName[]

/** Config for a backend source name; unknown sources keep their name and the neutral colour */
export function getSourceConfig(name: string | null | undefined): SourceConfig {
  return (
    SOURCE_CONFIG[name as SourceName] ?? {
      displayName: name || 'Unknown source',
      description: '',
      chartColor: 'var(--source-8)',
      homepage: null
    }
  )
}

export const sourceDisplayName = (name: string | null | undefined): string =>
  getSourceConfig(name).displayName

/**
 * Resolves `var(--token)` to the computed colour, for chart code (D3 color(), canvas) that
 * cannot use CSS variables. Returns the input unchanged when it is not a var() or outside
 * the browser.
 */
export function resolveCssColor(value: string, el?: Element): string {
  const name = value.match(/^var\((--[\w-]+)\)$/)?.[1]
  if (!name || typeof window === 'undefined') return value
  return (
    window
      .getComputedStyle(el ?? document.documentElement)
      .getPropertyValue(name)
      .trim() || value
  )
}
