/**
 * Identifier parsing and source links for HGNC, HPO, MONDO, OMIM, Orphanet, PubMed,
 * Ensembl and ClinVar. Render identifiers through OntologyTerm (name first, ID second).
 */

export type OntologySource =
  'HGNC' | 'HPO' | 'MONDO' | 'OMIM' | 'Orphanet' | 'PubMed' | 'Ensembl' | 'ClinVar'

export interface ParsedId {
  source: OntologySource
  /** Canonical display form, e.g. HP:0000112, ORPHA:93, PMID:123, VCV000012345 */
  id: string
  /** Local part without prefix, e.g. 0000112 */
  local: string
  url: string
}

interface OntologySourceConfig {
  name: string
  prefix: string
  url: (_local: string) => string
}

export const ONTOLOGY_SOURCES: Record<OntologySource, OntologySourceConfig> = {
  HGNC: {
    name: 'HGNC',
    prefix: 'HGNC',
    url: l => `https://www.genenames.org/data/gene-symbol-report/#!/hgnc_id/HGNC:${l}`
  },
  HPO: {
    name: 'Human Phenotype Ontology',
    prefix: 'HP',
    url: l => `https://hpo.jax.org/browse/term/HP:${l}`
  },
  MONDO: {
    name: 'MONDO Disease Ontology',
    prefix: 'MONDO',
    url: l => `https://monarchinitiative.org/MONDO:${l}`
  },
  OMIM: { name: 'OMIM', prefix: 'OMIM', url: l => `https://omim.org/entry/${l}` },
  Orphanet: {
    name: 'Orphanet',
    prefix: 'ORPHA',
    url: l => `https://www.orpha.net/en/disease/detail/${l}`
  },
  PubMed: { name: 'PubMed', prefix: 'PMID', url: l => `https://pubmed.ncbi.nlm.nih.gov/${l}/` },
  Ensembl: {
    name: 'Ensembl',
    prefix: '',
    url: l =>
      l.startsWith('ENSG')
        ? `https://www.ensembl.org/Homo_sapiens/Gene/Summary?g=${l}`
        : l.startsWith('ENST')
          ? `https://www.ensembl.org/Homo_sapiens/Transcript/Summary?t=${l}`
          : `https://www.ensembl.org/id/${l}`
  },
  ClinVar: {
    name: 'ClinVar',
    prefix: '',
    url: l => `https://www.ncbi.nlm.nih.gov/clinvar/variation/${l.replace(/^VCV0*/, '')}/`
  }
}

// Prefix aliases as they appear in source data (case-insensitive)
const PREFIXES: Record<string, OntologySource> = {
  hgnc: 'HGNC',
  hp: 'HPO',
  hpo: 'HPO',
  mondo: 'MONDO',
  omim: 'OMIM',
  mim: 'OMIM',
  orpha: 'Orphanet',
  orphanet: 'Orphanet',
  pmid: 'PubMed',
  pubmed: 'PubMed',
  clinvar: 'ClinVar',
  ensembl: 'Ensembl'
}

const canonical = (source: OntologySource, local: string) => {
  const { prefix } = ONTOLOGY_SOURCES[source]
  return prefix ? `${prefix}:${local}` : local
}

/**
 * Parses "HP:0000112", "MIM:173900", "Orphanet_93", "PMID: 123", "ENSG00000108753" or
 * "VCV000012345". A bare number needs `hint` (the source it came from); otherwise null.
 */
export function parseOntologyId(
  raw: string | number | null | undefined,
  hint?: OntologySource
): ParsedId | null {
  const value = String(raw ?? '').trim()
  if (!value) return null
  let source: OntologySource | undefined
  let local: string
  const prefixed = value.match(/^([A-Za-z]+)[:_]\s*(.+)$/)
  if (prefixed && PREFIXES[prefixed[1]!.toLowerCase()]) {
    source = PREFIXES[prefixed[1]!.toLowerCase()]
    local = prefixed[2]!
  } else if (/^ENS[A-Z]*\d+(\.\d+)?$/.test(value)) {
    source = 'Ensembl'
    local = value
  } else if (/^(VCV|RCV)\d+(\.\d+)?$/.test(value)) {
    source = 'ClinVar'
    local = value
  } else if (/^\d+$/.test(value) && hint) {
    source = hint
    local = value
  } else {
    return null
  }
  if (!source) return null
  return { source, id: canonical(source, local), local, url: ONTOLOGY_SOURCES[source].url(local) }
}

/** Link to the identifier at its source, or null when it cannot be parsed */
export const ontologyUrl = (raw: string | number | null | undefined, hint?: OntologySource) =>
  parseOntologyId(raw, hint)?.url ?? null
