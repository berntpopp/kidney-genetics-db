/**
 * NetworkGraph against a real, headless Cytoscape: the instance is not reactive, a data change
 * re-renders once (one instance, one layout), search clears its previous highlight and reports
 * invalid patterns, and graph and legend colour clusters identically beyond Okabe-Ito's 7.
 */
import { describe, it, expect, vi } from 'vitest'
import { mount, flushPromises } from '@vue/test-utils'
import { isProxy } from 'vue'

const counts = vi.hoisted(() => ({ created: 0, layouts: 0 }))

vi.mock('cytoscape', async importOriginal => {
  const real = ((await importOriginal()) as { default: any }).default
  const factory = Object.assign((opts: Record<string, unknown>) => {
    counts.created++
    const cy = real({ ...opts, container: undefined, headless: true })
    const layout = cy.layout.bind(cy)
    cy.layout = (o: Record<string, unknown>) => {
      counts.layouts++
      return layout({ ...o, name: 'grid', animate: false })
    }
    return cy
  }, real)
  return { default: factory }
})
vi.mock('cytoscape-cose-bilkent', () => ({ default: () => {} }))
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
})
