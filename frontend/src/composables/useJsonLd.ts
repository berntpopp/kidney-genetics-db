/**
 * JSON-LD structured data composable using @unhead/vue
 *
 * Provides helpers for injecting Schema.org / Bioschemas structured data
 * into the document <head> as <script type="application/ld+json">.
 */

import { type MaybeRefOrGetter, toValue, watchEffect } from 'vue'
import { useHead } from '@unhead/vue'

const SITE_URL = (import.meta.env.VITE_SITE_URL as string) || 'https://kidney-genetics.org'
const SITE_NAME = 'Kidney Genetics Database'

/**
 * Inject a JSON-LD script block into <head>.
 * Accepts a static object or a reactive getter for dynamic schemas.
 */
export function useJsonLd(schema: MaybeRefOrGetter<Record<string, unknown>>) {
  const head = useHead({})

  watchEffect(() => {
    const resolved = toValue(schema)
    if (head) {
      head.patch({
        script: [
          {
            type: 'application/ld+json',
            innerHTML: JSON.stringify(resolved)
          }
        ]
      })
    }
  })
}

/** Organization + WebSite schema with SearchAction (global) */
export function getOrganizationWebSiteSchema() {
  return {
    '@context': 'https://schema.org',
    '@graph': [
      {
        '@type': 'Organization',
        '@id': `${SITE_URL}/#organization`,
        name: SITE_NAME,
        url: SITE_URL,
        description:
          'Research platform for evidence-based kidney disease gene curation with multi-source integration.',
        logo: {
          '@type': 'ImageObject',
          url: `${SITE_URL}/icon-512.png`,
          width: 512,
          height: 512
        },
        sameAs: ['https://github.com/berntpopp/kidney-genetics-db']
      },
      {
        '@type': 'WebSite',
        '@id': `${SITE_URL}/#website`,
        name: SITE_NAME,
        url: SITE_URL,
        publisher: { '@id': `${SITE_URL}/#organization` },
        potentialAction: {
          '@type': 'SearchAction',
          target: {
            '@type': 'EntryPoint',
            urlTemplate: `${SITE_URL}/genes?search={search_term_string}`
          },
          'query-input': 'required name=search_term_string'
        }
      }
    ]
  }
}

/** Dataset schema for the Home page */
export function getDatasetSchema(geneCount?: number, lastUpdate?: string) {
  return {
    '@context': 'https://schema.org',
    '@type': 'Dataset',
    name: 'Kidney Genetics Database',
    description:
      'Evidence-based kidney disease gene curation with multi-source integration. Curated nephrology gene panel and renal genetics resource from PanelApp, ClinGen, GenCC, HPO, and more.',
    url: SITE_URL,
    license: 'https://creativecommons.org/licenses/by/4.0/',
    isAccessibleForFree: true,
    creator: { '@id': `${SITE_URL}/#organization` },
    keywords: [
      'kidney genetics',
      'nephrology',
      'genomics',
      'gene curation',
      'kidney disease',
      'genetic research',
      'nephrology gene panel',
      'renal genetics database',
      'nephropathy gene list',
      'kidney genomics resource'
    ],
    distribution: {
      '@type': 'DataDownload',
      encodingFormat: 'application/json',
      contentUrl: `${SITE_URL}/api/genes`
    },
    ...(geneCount != null
      ? {
          variableMeasured: {
            '@type': 'PropertyValue',
            name: 'Number of curated genes',
            value: geneCount
          }
        }
      : {}),
    ...(lastUpdate ? { dateModified: lastUpdate } : {})
  }
}

/** Bioschemas Gene schema for gene detail pages (Gene 1.0-RELEASE profile) */
export function getGeneSchema(gene: {
  approved_symbol: string
  approved_name?: string | null
  hgnc_id?: string | null
  aliases?: string[] | null
  evidence_score?: number | null
  ensembl_gene_id?: string | null
  ncbi_gene_id?: string | null
  uniprot_id?: string | null
  chromosome?: string | null
}) {
  const sameAs: string[] = []
  if (gene.hgnc_id) {
    sameAs.push(`https://www.genenames.org/data/gene-symbol-report/#!/hgnc_id/${gene.hgnc_id}`)
  }
  if (gene.ncbi_gene_id) {
    sameAs.push(`https://www.ncbi.nlm.nih.gov/gene/${gene.ncbi_gene_id}`)
  }
  if (gene.ensembl_gene_id) {
    sameAs.push(`https://www.ensembl.org/Homo_sapiens/Gene/Summary?g=${gene.ensembl_gene_id}`)
  }
  if (gene.uniprot_id) {
    sameAs.push(`https://www.uniprot.org/uniprot/${gene.uniprot_id}`)
  }

  return {
    '@context': 'https://schema.org',
    '@type': 'Gene',
    'dct:conformsTo': 'https://bioschemas.org/profiles/Gene/1.0-RELEASE',
    '@id': `${SITE_URL}/genes/${gene.approved_symbol}`,
    name: gene.approved_symbol,
    ...(gene.approved_name ? { description: gene.approved_name } : {}),
    identifier: gene.hgnc_id ?? gene.approved_symbol,
    url: `${SITE_URL}/genes/${gene.approved_symbol}`,
    ...(gene.aliases?.length ? { alternateName: gene.aliases } : {}),
    sameAs,
    taxonomicRange: {
      '@type': 'Taxon',
      name: 'Homo sapiens',
      '@id': 'https://identifiers.org/taxonomy:9606'
    },
    ...(gene.uniprot_id
      ? {
          encodesBioChemEntity: {
            '@type': 'BioChemEntity',
            '@id': `https://www.uniprot.org/uniprot/${gene.uniprot_id}`,
            name: `${gene.approved_symbol} protein`
          }
        }
      : {}),
    ...(gene.chromosome
      ? {
          isPartOfBioChemEntity: {
            '@type': 'BioChemEntity',
            name: `Chromosome ${gene.chromosome}`
          }
        }
      : {}),
    isPartOf: { '@id': `${SITE_URL}/#website` }
  }
}

/** BreadcrumbList schema from breadcrumb items */
export function getBreadcrumbSchema(
  breadcrumbs: Array<{ title: string; to?: string | null; disabled?: boolean }>
) {
  return {
    '@context': 'https://schema.org',
    '@type': 'BreadcrumbList',
    itemListElement: breadcrumbs.map((crumb, index) => ({
      '@type': 'ListItem',
      position: index + 1,
      name: crumb.title,
      ...(crumb.to ? { item: `${SITE_URL}${crumb.to}` } : {})
    }))
  }
}
