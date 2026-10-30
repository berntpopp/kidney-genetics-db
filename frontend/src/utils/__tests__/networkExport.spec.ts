import { describe, it, expect } from 'vitest'
import { cyjs, edgesCsv, graphml, nodesCsv } from '../networkExport'

const elements = [
  { data: { id: '1', gene_id: 1, label: 'PKD1', cluster_id: 0 }, position: { x: 1, y: 2 } },
  { data: { id: '2', gene_id: 2, label: 'PKD2', cluster_id: 0 } },
  { data: { id: '3', gene_id: 3, label: 'A&B<1>', cluster_id: 1 } },
  { data: { id: '1_2', source: '1', target: '2', weight: 0.9, string_score: 900 } },
  { data: { id: '1_3', source: '1', target: '3', weight: 0.5, string_score: 500 } }
]
const ctx = {
  hgncIds: new Map([[1, 'HGNC:9008']]),
  clusterName: (id: number) => `Cluster ${id + 1}`
}

describe('network export builders', () => {
  it('writes one node row per gene with HGNC id, cluster and degree', () => {
    expect(nodesCsv(elements, ctx).split('\r\n')).toEqual([
      'Gene Symbol,HGNC ID,Gene ID,Cluster,Degree',
      'PKD1,HGNC:9008,1,Cluster 1,2',
      'PKD2,,2,Cluster 1,1',
      'A&B<1>,,3,Cluster 2,1'
    ])
  })

  it('writes edges by gene symbol with the raw STRING score', () => {
    expect(edgesCsv(elements).split('\r\n')).toEqual([
      'Source Symbol,Target Symbol,STRING Score',
      'PKD1,PKD2,900',
      'PKD1,A&B<1>,500'
    ])
  })

  it('writes Cytoscape desktop .cyjs with nodes, edges and positions', () => {
    const json = JSON.parse(cyjs(elements, 'kgdb_network'))
    expect(json.format_version).toBe('1.0')
    expect(json.data.name).toBe('kgdb_network')
    expect(json.elements.nodes).toHaveLength(3)
    expect(json.elements.edges).toHaveLength(2)
    expect(json.elements.nodes[0].position).toEqual({ x: 1, y: 2 })
    expect(json.elements.edges[0].data).toMatchObject({ source: '1', target: '2' })
  })

  it('writes well-formed, escaped GraphML', () => {
    const xml = graphml(elements, ctx)
    const doc = new window.DOMParser().parseFromString(xml, 'application/xml')
    expect(doc.getElementsByTagName('parsererror')).toHaveLength(0)
    expect(doc.getElementsByTagName('node')).toHaveLength(3)
    expect(doc.getElementsByTagName('edge')).toHaveLength(2)
    expect(xml).toContain('A&amp;B&lt;1&gt;')
  })
})
