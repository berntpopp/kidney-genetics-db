/**
 * NetworkGraph against a real, headless Cytoscape: the instance is not reactive, a data change
 * re-renders once (one instance, one layout), search clears its previous highlight and reports
 * invalid patterns, and graph and legend colour clusters identically beyond Okabe-Ito's 7.
 */
import { describe, it, expect, vi } from 'vitest'
import { mount, flushPromises } from '@vue/test-utils'
import { isProxy } from 'vue'

const counts = vi.hoisted(() => ({ created: 0, layouts: 0 }))
// Every element JSON handed to Cytoscape, to check nodes arrive styled
const given = vi.hoisted(() => [] as { data: Record<string, unknown> }[])

vi.mock('cytoscape', async importOriginal => {
  const real = ((await importOriginal()) as { default: any }).default
  const factory = Object.assign((opts: Record<string, unknown>) => {
    counts.created++
    given.push(...((opts.elements as typeof given) ?? []))
    const cy = real({ ...opts, container: undefined, headless: true })
    const add = cy.add.bind(cy)
    cy.add = (eles: typeof given) => (given.push(...eles), add(eles))
    const layout = cy.layout.bind(cy)
    cy.layout = (o: Record<string, unknown>) => {
      counts.layouts++
      return layout({ ...o, name: 'grid', animate: false })
    }
    return cy
  }, real)
  return { default: factory }
})
vi.mock('cytoscape-fcose', () => ({ default: () => {} }))
vi.mock('../canvasColor', () => ({ canvasColor: (v: string) => v, clearCanvasColors: () => {} }))
vi.stubGlobal('logService', { info: vi.fn(), warn: vi.fn(), error: vi.fn(), debug: vi.fn() })

import NetworkGraph from '../NetworkGraph.vue'
import { CLUSTER_PALETTE } from '../clusterPalette'

/** 14 clusters of decreasing size (rank = cluster id), plus one 2-gene cluster */
function network(clusters = 14) {
  const elements: { data: Record<string, unknown> }[] = []
  let gene = 1
  for (let c = 0; c <= clusters; c++) {
    const size = c === clusters ? 2 : 3 + clusters - c
    const ids: number[] = []
    for (let i = 0; i < size; i++, gene++) {
      ids.push(gene)
      elements.push({ data: { id: String(gene), gene_id: gene, label: `G${gene}`, cluster_id: c } })
    }
    for (let i = 1; i < ids.length; i++) {
      elements.push({ data: { id: `${ids[0]}_${ids[i]}`, source: String(ids[0]), target: String(ids[i]), weight: 0.7 } }) // prettier-ignore
    }
  }
  return {
    nodes: gene - 1,
    edges: elements.length - (gene - 1),
    components: 1,
    cytoscape_json: { elements }
  }
}

const settle = async () => {
  for (let i = 0; i < 5; i++) {
    await flushPromises()
    await new Promise(r => setTimeout(r, 20))
  }
}

describe('NetworkGraph behaviour', () => {
  it('keeps Cytoscape out of Vue reactivity', async () => {
    const wrapper = mount(NetworkGraph, { props: { networkData: network(2) } })
    await settle()
    const cy = (wrapper.vm as any).cyInstance
    expect(cy).toBeTruthy()
    expect(isProxy(cy)).toBe(false)
    expect(cy.__v_skip).toBe(true)
    wrapper.unmount()
  })

  it('renders once on mount and once per data change, reusing the instance', async () => {
    counts.created = 0
    counts.layouts = 0
    const wrapper = mount(NetworkGraph, { props: { networkData: network(2) } })
    await settle()
    expect(counts).toEqual({ created: 1, layouts: 1 })

    await wrapper.setProps({ networkData: network(3) })
    await settle()
    expect(counts).toEqual({ created: 1, layouts: 2 })
    expect((wrapper.vm as any).cyInstance.nodes().length).toBe(network(3).nodes)
    wrapper.unmount()
  })

  it('colours 14 clusters distinctly and the legend matches the graph', async () => {
    const wrapper = mount(NetworkGraph, { props: { networkData: network(14) } })
    await settle()
    const cy = (wrapper.vm as any).cyInstance
    const colorOf = (c: number) => cy.nodes(`[cluster_id = ${c}]`).first().data('color')

    const top12 = Array.from({ length: 12 }, (_, c) => colorOf(c))
    expect(top12).toEqual([...CLUSTER_PALETTE])
    // Ranks 12-13 reuse hues with a second shape; the 2-gene cluster is grey
    expect(cy.nodes('[cluster_id = 12]').first().data('shape')).toBe('round-diamond')
    expect(colorOf(14)).toBe('var(--source-8)')

    for (const chip of wrapper.findAll('.cluster-chip')) {
      const c = Number(chip.text().match(/Cluster (\d+)/)![1]) - 1
      const swatch = chip.find('span[aria-hidden="true"]')
      expect(swatch.attributes('style')).toContain(`background-color: ${colorOf(c)}`)
    }
    wrapper.unmount()
  })

  it('clears the previous search highlight and reports invalid patterns', async () => {
    const wrapper = mount(NetworkGraph, { props: { networkData: network(2) } })
    await settle()
    const cy = (wrapper.vm as any).cyInstance
    const input = wrapper.find('input[aria-label="Search genes in the network"]')

    await input.setValue('G1')
    await input.trigger('keyup.enter')
    await wrapper
      .findAll('button')
      .find(b => b.text().includes('Highlight All'))!
      .trigger('click')
    expect(cy.getElementById('1').hasClass('search-match')).toBe(true)

    await input.setValue('G2')
    await input.trigger('keyup.enter')
    expect(cy.getElementById('1').hasClass('search-match')).toBe(false)

    await input.setValue('***')
    await input.trigger('keyup.enter')
    await flushPromises()
    expect(wrapper.find('[role="alert"]').text()).toContain('Too many consecutive wildcards')
    expect(wrapper.text()).not.toContain('No genes match')
    wrapper.unmount()
  })

  it('summarises the network for assistive technology', async () => {
    const wrapper = mount(NetworkGraph, { props: { networkData: network(2) } })
    await settle()
    const label = wrapper.find('[role="img"]').attributes('aria-label')
    expect(label).toContain(`${network(2).nodes} genes`)
    expect(label).toContain('3 clusters')
    wrapper.unmount()
  })

  // Cytoscape warns once per node and property ("Do not assign mappings to elements without
  // corresponding data") when a node arrives without the data its 'data(...)' styles read
  it('hands Cytoscape nodes that already carry their colour, outline and shape', async () => {
    given.length = 0
    const wrapper = mount(NetworkGraph, { props: { networkData: network(2) } })
    await settle()
    await wrapper.setProps({ networkData: network(3) })
    await settle()
    const nodes = given.filter(el => !el.data.source)
    expect(nodes.length).toBe(network(2).nodes + network(3).nodes)
    for (const { data } of nodes) {
      expect(data).toEqual(
        expect.objectContaining({
          color: expect.any(String),
          outline: expect.any(String),
          shape: expect.any(String)
        })
      )
    }
    wrapper.unmount()
  })

  it('keeps positions on a clustering result: recolours, drops filtered nodes, no new layout', async () => {
    counts.layouts = 0
    const built = network(2)
    const wrapper = mount(NetworkGraph, { props: { networkData: built } })
    await settle()
    const cy = (wrapper.vm as any).cyInstance
    cy.nodes().forEach((n: any, i: number) => n.position({ x: i * 7, y: i * 3 }))
    const before = cy.getElementById('1').position()

    // Same graph, new cluster ids, and the last (2-gene) cluster filtered out
    const dropped = new Set(cy.nodes('[cluster_id = 2]').map((n: any) => n.id()))
    const elements = built.cytoscape_json.elements
      .filter(el => !dropped.has(el.data.id as string) && !dropped.has(el.data.target as string))
      .map(el =>
        el.data.source
          ? el
          : { data: { ...el.data, cluster_id: 9 - (el.data.cluster_id as number) } }
      )
    const genes = elements.filter(el => !el.data.source).length
    await wrapper.setProps({
      networkData: { ...built, nodes: genes, cytoscape_json: { elements } }
    })
    await settle()

    expect(counts.layouts).toBe(1)
    expect(cy.nodes().length).toBe(genes)
    expect(cy.getElementById('1').position()).toEqual(before)
    expect(cy.getElementById('1').data('cluster_id')).toBe(9)
    wrapper.unmount()
  })

  it('names clusters with their label in the legend chips', async () => {
    const wrapper = mount(NetworkGraph, {
      props: { networkData: network(2), clusterLabels: new Map([[0, 'Renal cyst']]) }
    })
    await settle()
    const chips = wrapper.findAll('.cluster-chip')
    expect(chips[0].text()).toContain('Cluster 1')
    expect(chips[0].text()).toContain('Renal cyst')
    expect(chips[0].find('[title="Renal cyst"]').exists()).toBe(true)
    expect(chips[1].text()).not.toContain('·')
    wrapper.unmount()
  })

  it('lists genes in a table view whose rows emit nodeClick', async () => {
    const wrapper = mount(NetworkGraph, { props: { networkData: network(2) } })
    await settle()
    await wrapper
      .findAll('button')
      .find(b => b.text() === 'Table')!
      .trigger('click')
    await settle()
    const rows = wrapper.findAll('tbody tr')
    expect(rows.length).toBe(network(2).nodes)
    // Default sort: degree, hub first (each cluster's first gene links to the rest)
    expect(rows[0].text()).toContain('G1')
    expect(rows[0].text()).toContain('Cluster 1')
    await rows[0].find('button').trigger('keydown', { key: 'Enter' })
    expect(wrapper.emitted('nodeClick')).toEqual([[{ label: 'G1', gene_id: 1, cluster_id: 0 }]])
    wrapper.unmount()
  })
})
