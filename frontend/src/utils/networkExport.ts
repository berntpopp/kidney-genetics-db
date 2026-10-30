/**
 * Export builders for the protein-protein interaction network. Input is Cytoscape element
 * JSON as the API returns it (or cy.elements().jsons()): nodes carry gene_id, label and
 * cluster_id; edges carry source, target, string_score (0-1000) and weight.
 */
import { toCsv } from './csv'

export interface NetworkElement {
  data: Record<string, any>
  position?: { x: number; y: number }
}

export interface NetworkExportContext {
  /** gene_id -> HGNC ID */
  hgncIds?: Map<number, string>
  /** Backend cluster id -> display name, e.g. "Cluster 1" */
  clusterName?: (_clusterId: number) => string
}

const split = (elements: NetworkElement[]) => {
  const nodes = elements.filter(e => e.data.source === undefined)
  const edges = elements.filter(e => e.data.source !== undefined)
  return { nodes, edges }
}

const clusterOf = (data: Record<string, any>, ctx: NetworkExportContext) =>
  data.cluster_id === undefined || data.cluster_id === null
    ? ''
    : (ctx.clusterName?.(data.cluster_id) ?? String(data.cluster_id))

/** Rows of [symbol, HGNC ID, gene id, cluster, degree]; degree counts edges in the export */
function nodeRows(elements: NetworkElement[], ctx: NetworkExportContext) {
  const { nodes, edges } = split(elements)
  const degree = new Map<string, number>()
  for (const { data } of edges) {
    degree.set(String(data.source), (degree.get(String(data.source)) ?? 0) + 1)
    degree.set(String(data.target), (degree.get(String(data.target)) ?? 0) + 1)
  }
  return nodes.map(({ data }) => [
    data.label ?? '',
    ctx.hgncIds?.get(Number(data.gene_id)) ?? '',
    data.gene_id ?? '',
    clusterOf(data, ctx),
    degree.get(String(data.id)) ?? 0
  ])
}

function edgeRows(elements: NetworkElement[]) {
  const { nodes, edges } = split(elements)
  const label = new Map(nodes.map(({ data }) => [String(data.id), data.label ?? data.id]))
  return edges.map(({ data }) => [
    label.get(String(data.source)) ?? data.source,
    label.get(String(data.target)) ?? data.target,
    data.string_score ?? ''
  ])
}

export const nodesCsv = (elements: NetworkElement[], ctx: NetworkExportContext = {}): string =>
  toCsv(['Gene Symbol', 'HGNC ID', 'Gene ID', 'Cluster', 'Degree'], nodeRows(elements, ctx))

export const edgesCsv = (elements: NetworkElement[]): string =>
  toCsv(['Source Symbol', 'Target Symbol', 'STRING Score'], edgeRows(elements))

/** Cytoscape desktop .cyjs (File > Import > Network from File) */
export function cyjs(elements: NetworkElement[], name: string): string {
  const { nodes, edges } = split(elements)
  const strip = ({ data, position }: NetworkElement) => (position ? { data, position } : { data })
  return JSON.stringify(
    {
      format_version: '1.0',
      generated_by: 'Kidney-Genetics Database',
      data: { name },
      elements: { nodes: nodes.map(strip), edges: edges.map(strip) }
    },
    null,
    2
  )
}

const xml = (value: unknown) =>
  String(value ?? '').replace(
    /[<>&"']/g,
    c => ({ '<': '&lt;', '>': '&gt;', '&': '&amp;', '"': '&quot;', "'": '&apos;' })[c]!
  )

/** GraphML (yEd, Gephi, Cytoscape, igraph) with symbol, HGNC ID, cluster and STRING score */
export function graphml(elements: NetworkElement[], ctx: NetworkExportContext = {}): string {
  const { nodes, edges } = split(elements)
  const lines = [
    '<?xml version="1.0" encoding="UTF-8"?>',
    '<graphml xmlns="http://graphml.graphdrawing.org/xmlns">',
    '  <key id="label" for="node" attr.name="label" attr.type="string"/>',
    '  <key id="hgnc_id" for="node" attr.name="hgnc_id" attr.type="string"/>',
    '  <key id="gene_id" for="node" attr.name="gene_id" attr.type="int"/>',
    '  <key id="cluster" for="node" attr.name="cluster" attr.type="string"/>',
    '  <key id="string_score" for="edge" attr.name="string_score" attr.type="double"/>',
    '  <graph id="G" edgedefault="undirected">'
  ]
  for (const { data } of nodes) {
    lines.push(
      `    <node id="${xml(data.id)}">`,
      `      <data key="label">${xml(data.label)}</data>`,
      `      <data key="hgnc_id">${xml(ctx.hgncIds?.get(Number(data.gene_id)))}</data>`,
      `      <data key="gene_id">${xml(data.gene_id)}</data>`,
      `      <data key="cluster">${xml(clusterOf(data, ctx))}</data>`,
      '    </node>'
    )
  }
  for (const { data } of edges) {
    lines.push(
      `    <edge source="${xml(data.source)}" target="${xml(data.target)}">`,
      `      <data key="string_score">${xml(data.string_score)}</data>`,
      '    </edge>'
    )
  }
  lines.push('  </graph>', '</graphml>')
  return lines.join('\n')
}
