/**
 * A theme switch restyles the canvas with the new theme's tokens: the watcher runs after
 * VueUse has toggled the `dark` class (flush 'post'), and nodes carry no bypass colours.
 */
import { describe, it, expect, vi } from 'vitest'
import { mount, flushPromises } from '@vue/test-utils'
import { ref, watch } from 'vue'

const styleSpy = vi.fn()
vi.mock('cytoscape', () => {
  const fake: unknown = new Proxy(function () {}, {
    get: (_t, key) => {
      if (key === 'then') return undefined
      if (key === 'length') return 0
      if (key === 'destroyed') return () => false
      if (key === 'style') return (...args: unknown[]) => (styleSpy(...args), fake)
      return fake
    },
    apply: () => fake
  })
  return { default: fake }
})
vi.mock('cytoscape-cose-bilkent', () => ({ default: {} }))
// Resolved colour follows the DOM class, as getComputedStyle would
vi.mock('../canvasColor', () => ({
  canvasColor: () => (document.documentElement.classList.contains('dark') ? 'dark' : 'light'),
  clearCanvasColors: vi.fn()
}))
// Like VueUse: the class is toggled in a post-flush watcher
const isDark = ref(false)
watch(isDark, v => document.documentElement.classList.toggle('dark', v), { flush: 'post' })
vi.mock('@/composables/useAppTheme', () => ({ useAppTheme: () => ({ isDark }) }))

import NetworkGraph from '../NetworkGraph.vue'

const networkData = {
  nodes: 1,
  edges: 0,
  components: 1,
  cytoscape_json: { elements: [{ data: { id: 'a', gene_id: 1, label: 'PKD1', cluster_id: 0 } }] }
}

describe('NetworkGraph theme switch', () => {
  it('rebuilds the stylesheet with the new theme colours', async () => {
    mount(NetworkGraph, { props: { networkData } })
    await flushPromises()
    styleSpy.mockClear()

    isDark.value = true
    await flushPromises()

    const sheet = styleSpy.mock.calls.at(-1)?.[0] as { style: Record<string, unknown> }[]
    expect(Array.isArray(sheet)).toBe(true)
    expect(sheet.some(rule => rule.style.color === 'dark')).toBe(true)
    expect(sheet.some(rule => rule.style.color === 'light')).toBe(false)
  })
})
