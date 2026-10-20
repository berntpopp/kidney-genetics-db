/**
 * Gene views must reload when only the route symbol changes (#302).
 * Mounts the real App shell and gene views on a real router.
 */

import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest'
import { flushPromises, mount } from '@vue/test-utils'
import type { VueWrapper } from '@vue/test-utils'
import { createPinia } from 'pinia'
import { createHead } from '@unhead/vue/client'
import { createRouter, createMemoryHistory } from 'vue-router'
import type { Router } from 'vue-router'
import App from '@/App.vue'
import GeneDetail from '@/views/GeneDetail.vue'
import GeneStructure from '@/views/GeneStructure.vue'

vi.mock('@/api/genes', () => ({
  geneApi: {
    getGene: vi.fn(async (symbol: string) => ({
      id: symbol.charCodeAt(3),
      approved_symbol: symbol,
      hgnc_id: `HGNC:${symbol}`,
      evidence_score: 50
    })),
    getGeneEvidence: vi.fn(async () => ({ evidence: [] })),
    getGeneAnnotations: vi.fn(async () => null)
  }
}))
import { geneApi } from '@/api/genes'

vi.stubGlobal('logService', { info: vi.fn(), warn: vi.fn(), error: vi.fn(), debug: vi.fn() })
vi.stubGlobal(
  'matchMedia',
  vi.fn(() => ({ matches: false, addEventListener: vi.fn(), removeEventListener: vi.fn() }))
)

let wrapper: VueWrapper | undefined
let router: Router

async function go(nav: () => unknown) {
  await nav()
  await flushPromises()
  await new Promise(r => setTimeout(r, 300)) // out-in fade transition
  await flushPromises()
}

const heading = () => wrapper!.find('h1').text()

beforeEach(async () => {
  vi.clearAllMocks()
  router = createRouter({
    history: createMemoryHistory(),
    routes: [
      { path: '/genes', component: { render: () => null } },
      { path: '/genes/:symbol', component: GeneDetail, props: true },
      { path: '/genes/:symbol/structure', component: GeneStructure, props: true }
    ]
  })
  await router.push('/genes/PKD1')
  await router.isReady()
  wrapper = mount(App, {
    global: {
      plugins: [router, createPinia(), createHead()],
      stubs: { AppHeader: true, AppFooter: true, LogViewer: true, Toaster: true }
    },
    attachTo: document.body
  })
  await go(() => undefined)
})

afterEach(() => {
  wrapper?.unmount()
  document.body.innerHTML = ''
})

describe('gene route reuse', () => {
  it('gene detail follows symbol changes and history navigation', async () => {
    expect(heading()).toContain('PKD1')
    await go(() => router.push('/genes/PKD2'))
    expect(heading()).toContain('PKD2')
    expect(geneApi.getGeneEvidence).toHaveBeenLastCalledWith('PKD2')

    await go(() => router.back())
    expect(router.currentRoute.value.path).toBe('/genes/PKD1')
    expect(heading()).toContain('PKD1')
    expect(geneApi.getGene).toHaveBeenLastCalledWith('PKD1')
  })

  it('gene structure follows symbol changes', async () => {
    await go(() => router.push('/genes/PKD1/structure'))
    expect(heading()).toContain('PKD1')
    await go(() => router.push('/genes/PKD2/structure'))
    expect(heading()).toContain('PKD2')
    expect(geneApi.getGene).toHaveBeenLastCalledWith('PKD2')
  })
})
