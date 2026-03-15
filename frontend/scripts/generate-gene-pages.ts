/**
 * Post-build script: generates meta-only HTML shells for gene detail pages.
 * Each shell has correct <title>, <meta>, and JSON-LD baked into the SPA shell.
 * The Vue SPA still hydrates/mounts normally on the client.
 *
 * Usage: tsx scripts/generate-gene-pages.ts
 * Requires: API running at localhost:8000 (or VITE_API_URL env var)
 */

import { readFileSync, writeFileSync, mkdirSync } from 'fs'
import { join } from 'path'

const DIST_DIR = join(import.meta.dirname, '..', 'dist')
const API_URL = process.env.VITE_API_URL || 'http://localhost:8000'
const SITE_URL = process.env.VITE_SITE_URL || 'https://kidney-genetics.org'

interface GeneAttributes {
  approved_symbol: string
  approved_name?: string | null
  hgnc_id?: string | null
  ensembl_gene_id?: string | null
  ncbi_gene_id?: string | null
  evidence_score?: number | null
}

interface ApiResponse {
  data: Array<{ id: string; type: string; attributes: GeneAttributes }>
}

function escapeHtml(s: string): string {
  return s.replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;')
}

function escapeAttr(s: string): string {
  return s
    .replace(/&/g, '&amp;')
    .replace(/"/g, '&quot;')
    .replace(/</g, '&lt;')
    .replace(/>/g, '&gt;')
}

async function main() {
  const template = readFileSync(join(DIST_DIR, 'index.html'), 'utf-8')

  console.log(`Fetching genes from ${API_URL}/api/genes ...`)
  const response = await fetch(
    `${API_URL}/api/genes?fields=approved_symbol,approved_name,hgnc_id,ensembl_gene_id,ncbi_gene_id,evidence_score&page[size]=10000`
  )

  if (!response.ok) {
    throw new Error(`API returned ${response.status}: ${await response.text()}`)
  }

  const data = (await response.json()) as ApiResponse
  const genes = data.data
  console.log(`Got ${genes.length} genes`)

  let generated = 0

  for (const gene of genes) {
    const attrs = gene.attributes
    const symbol = attrs.approved_symbol
    const name = attrs.approved_name || ''
    const score = attrs.evidence_score != null ? attrs.evidence_score.toFixed(1) : ''

    const title = name
      ? `${symbol} (${name}) — Kidney Disease Gene Evidence | KGDB`
      : `${symbol} — Kidney Disease Gene Evidence | KGDB`

    const description = `${symbol} kidney disease gene detail.${score ? ` Evidence score: ${score}.` : ''} Disease associations, expression data, and annotations from multiple genomic sources.`

    const url = `${SITE_URL}/genes/${symbol}`

    const sameAs: string[] = []
    if (attrs.hgnc_id)
      sameAs.push(`https://www.genenames.org/data/gene-symbol-report/#!/hgnc_id/${attrs.hgnc_id}`)
    if (attrs.ncbi_gene_id) sameAs.push(`https://www.ncbi.nlm.nih.gov/gene/${attrs.ncbi_gene_id}`)
    if (attrs.ensembl_gene_id)
      sameAs.push(`https://www.ensembl.org/Homo_sapiens/Gene/Summary?g=${attrs.ensembl_gene_id}`)

    const jsonLd = JSON.stringify({
      '@context': 'https://schema.org',
      '@type': 'Gene',
      'dct:conformsTo': 'https://bioschemas.org/profiles/Gene/1.0-RELEASE',
      name: symbol,
      ...(name ? { description: name } : {}),
      identifier: attrs.hgnc_id ?? symbol,
      url,
      sameAs,
      taxonomicRange: {
        '@type': 'Taxon',
        name: 'Homo sapiens',
        '@id': 'https://identifiers.org/taxonomy:9606'
      }
    })

    const html = template
      .replace(/<title>[^<]*<\/title>/, `<title>${escapeHtml(title)}</title>`)
      .replace(
        '</head>',
        `  <meta name="description" content="${escapeAttr(description)}">\n` +
          `  <meta property="og:title" content="${escapeAttr(title)}">\n` +
          `  <meta property="og:description" content="${escapeAttr(description)}">\n` +
          `  <meta property="og:url" content="${url}">\n` +
          `  <link rel="canonical" href="${url}">\n` +
          `  <script type="application/ld+json">${jsonLd}</` +
          `script>\n` +
          `</head>`
      )

    const outDir = join(DIST_DIR, 'genes', symbol)
    mkdirSync(outDir, { recursive: true })
    writeFileSync(join(outDir, 'index.html'), html)
    generated++
  }

  console.log(`Generated ${generated} gene page HTML shells`)
}

main().catch((err: unknown) => {
  console.error('Gene page generation failed:', err)
  process.exit(1)
})
