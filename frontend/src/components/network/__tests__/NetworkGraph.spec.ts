import { describe, it, expect, vi } from 'vitest'
import { mount, flushPromises } from '@vue/test-utils'

// Chainable stand-in for Cytoscape: every property is a callable returning the stand-in
vi.mock('cytoscape', () => {
  const fake: unknown = new Proxy(function () {}, {
    get: (_t, key) => (key === 'then' ? undefined : fake),
    apply: () => fake
  })
  return { default: fake }
})
vi.mock('cytoscape-cose-bilkent', () => ({ default: {} }))

import NetworkGraph from '../NetworkGraph.vue'

const networkData = {
  nodes: 2,
  edges: 1,
  components: 1,
  cytoscape_json: {
    elements: [
      { data: { id: 'a', gene_id: 1, label: 'PKD1', cluster_id: 0, color: '#FFEB3B' } },
      { data: { id: 'b', gene_id: 2, label: 'PKD2', cluster_id: 1, color: '#1976D2' } }
    ]
  }
}

describe('NetworkGraph legibility (#325)', () => {
  it('labels the counts as the displayed network', async () => {
    const wrapper = mount(NetworkGraph, { props: { networkData } })
    await flushPromises()
    expect(wrapper.text()).toContain('Displayed: 2 genes, 1 interactions, 1 component(s)')
  })

  it('has no duplicate clustering or STRING-score controls', async () => {
    const wrapper = mount(NetworkGraph, { props: { networkData } })
    await flushPromises()
    expect(wrapper.text()).not.toContain('Clustering')
    expect(wrapper.text()).not.toContain('Min STRING Score')
  })

  it('renders keyboard-focusable cluster legend chips with foreground text', async () => {
    const wrapper = mount(NetworkGraph, { props: { networkData } })
    await flushPromises()
    const chips = wrapper.findAll('.cluster-chip')
    expect(chips.length).toBe(2)
    for (const chip of chips) {
      expect(chip.attributes('tabindex')).toBe('0')
      expect(chip.attributes('role')).toBe('button')
      expect(chip.classes()).toContain('text-foreground')
      expect(chip.attributes('style') ?? '').not.toContain('color: white')
    }
  })
})
