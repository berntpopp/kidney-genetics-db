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
        logo: `${SITE_URL}/icon-512.png`
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
      'Evidence-based kidney disease gene curation with multi-source integration from PanelApp, ClinGen, GenCC, HPO, and more.',
    url: SITE_URL,
    license: 'https://creativecommons.org/licenses/by/4.0/',
    creator: { '@id': `${SITE_URL}/#organization` },
    keywords: [
      'kidney genetics',
      'nephrology',
      'genomics',
      'gene curation',
      'kidney disease',
      'genetic research'
    ],
    ...(geneCount != null ? { variableMeasured: `${geneCount} genes` } : {}),
    ...(lastUpdate ? { dateModified: lastUpdate } : {})
  }
}

/** Bioschemas Gene schema for gene detail pages */
export function getGeneSchema(gene: {
  approved_symbol: string
  hgnc_id?: string | null
  aliases?: string[] | null
  evidence_score?: number | null
}) {
  return {
    '@context': 'https://schema.org',
    '@type': 'Gene',
    name: gene.approved_symbol,
    identifier: gene.hgnc_id ?? gene.approved_symbol,
    url: `${SITE_URL}/genes/${gene.approved_symbol}`,
    ...(gene.aliases?.length ? { alternateName: gene.aliases } : {}),
    ...(gene.hgnc_id
      ? {
          sameAs: `https://www.genenames.org/data/gene-symbol-report/#!/hgnc_id/${gene.hgnc_id}`
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
