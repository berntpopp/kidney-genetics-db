/**
 * Consistency and copy fixes from the UI/UX audit (#329).
 */

import { describe, it, expect, vi, afterEach } from 'vitest'
import { flushPromises, mount } from '@vue/test-utils'
import type { VueWrapper } from '@vue/test-utils'
import { createRouter, createMemoryHistory, RouterView } from 'vue-router'
import NotFound from '@/views/NotFound.vue'
import FAQ from '@/views/FAQ.vue'
import DataSources from '@/views/DataSources.vue'
import GeneStructureVisualization from '@/components/visualizations/GeneStructureVisualization.vue'

vi.mock('@unhead/vue', () => ({ useHead: vi.fn() }))
vi.mock('@/api/datasources', () => ({
  datasourceApi: {
    getDataSources: vi.fn().mockResolvedValue({
      total_active: 1,
      total_unique_genes: 5080,
      sources: [
        {
          name: 'PubTator',
          status: 'active',
          stats: { gene_count: 4321, last_updated: '2025-03-04T12:00:00' }
        }
      ]
    })
  }
}))
vi.stubGlobal('logService', { info: vi.fn(), warn: vi.fn(), error: vi.fn(), debug: vi.fn() })
vi.stubGlobal(
  'ResizeObserver',
  class {
    observe() {}
    unobserve() {}
    disconnect() {}
  }
)

let wrapper: VueWrapper | undefined
afterEach(() => {
  wrapper?.unmount()
  wrapper = undefined
  document.body.innerHTML = ''
})

function routerWith(path: string, component: object) {
  return createRouter({
    history: createMemoryHistory(),
    routes: [
      { path, component },
      { path: '/:p(.*)*', component: { render: () => null } }
    ]
  })
}

describe('404 page', () => {
  it('offers a gene search that hands the query to the gene browser', async () => {
    const router = routerWith('/missing', NotFound)
    await router.push('/missing')
    await router.isReady()
    wrapper = mount(RouterView, { global: { plugins: [router] }, attachTo: document.body })

    await wrapper.get('input[aria-label="Search genes"]').setValue(' PKD1 ')
    await wrapper.get('form[role="search"]').trigger('submit')
    await flushPromises()

    expect(router.currentRoute.value.path).toBe('/genes')
    expect(router.currentRoute.value.query.search).toBe('PKD1')
  })
})

describe('FAQ', () => {
  it('uses the shared breadcrumb and an accordion that opens by its trigger', async () => {
    const router = routerWith('/faq', FAQ)
    await router.push('/faq')
    await router.isReady()
    wrapper = mount(RouterView, { global: { plugins: [router] }, attachTo: document.body })

    expect(wrapper.find('nav[aria-label="breadcrumb"] a[href="/"]').exists()).toBe(true)
    // Closed answers stay in the DOM (prerendered HTML) but hidden
    const closed = wrapper.get('[data-slot="accordion-content"]')
    expect(closed.text()).toContain('KGDB contains genes with evidence for kidney disease')
    expect(closed.attributes('hidden')).toBeDefined()
    const trigger = wrapper.get('[data-slot="accordion-trigger"]')
    expect(trigger.attributes('aria-expanded')).toBe('false')
    await trigger.trigger('click')
    expect(trigger.attributes('aria-expanded')).toBe('true')
    expect(wrapper.text()).toContain('KGDB contains')
  })
})

describe('FAQ prerender', () => {
  it('server-renders closed answers as hidden="until-found"', async () => {
    const { createSSRApp } = await import('vue')
    const { renderToString } = await import('vue/server-renderer')
    const router = routerWith('/faq', FAQ)
    await router.push('/faq')
    await router.isReady()
    const app = createSSRApp(RouterView)
    app.use(router)
    const html = await renderToString(app)
    expect(html).toContain('hidden="until-found"')
    expect(html).toContain('KGDB contains genes with evidence for kidney disease')
  })
})

describe('Data Sources cards', () => {
  it('group thousands, print ISO dates and invent no "API" type', async () => {
    const router = routerWith('/data-sources', DataSources)
    wrapper = mount(DataSources, { global: { plugins: [router] } })
    await flushPromises()

    const text = wrapper.text()
    expect(text).toContain('4,321')
    expect(text).toContain('2025-03-04')
    expect(text).not.toMatch(/\bAPI\b/)
  })
})

describe('Gene structure filter chips', () => {
  it('are toggle buttons with spelled-out labels', async () => {
    wrapper = mount(GeneStructureVisualization, {
      props: {
        geneSymbol: 'PKD1',
        ensemblData: { exons: [], canonical_transcript: {}, start: 1, end: 100, strand: 1 },
        clinvarData: {
          genomic_variants: [
            { genomic_start: 10, category: 'pathogenic', effect_category: 'missense' },
            { genomic_start: 20, category: 'benign', effect_category: 'synonymous' }
          ]
        }
      },
      attachTo: document.body
    })
    await flushPromises()

    expect(wrapper.text()).toContain('Classification')
    expect(wrapper.text()).not.toContain('Class.')
    expect(wrapper.text()).toMatch(/\d+ of 2 loaded variants shown/)

    const chip = wrapper.findAll('button[aria-pressed]')[0]
    expect(chip.attributes('type')).toBe('button')
    const before = chip.attributes('aria-pressed')
    await chip.trigger('click')
    expect(wrapper.findAll('button[aria-pressed]')[0].attributes('aria-pressed')).not.toBe(before)
  })
})

describe('Evidence card footer', () => {
  it('omits the date line instead of printing "Unknown"', async () => {
    const { h } = await import('vue')
    const { Accordion } = await import('@/components/ui/accordion')
    const EvidenceCard = (await import('@/components/evidence/EvidenceCard.vue')).default
    const evidence = { source_name: 'ClinGen', evidence_data: {}, evidence_date: null }
    wrapper = mount(
      {
        render: () =>
          h(Accordion, { type: 'single', defaultValue: 'ClinGen' }, () =>
            h(EvidenceCard, { evidence })
          )
      },
      { global: { stubs: { ClinGenEvidence: true } } }
    )
    await flushPromises()

    expect(wrapper.text()).toContain('View Source')
    expect(wrapper.text()).not.toContain('Unknown')
  })
})

describe('Main navigation', () => {
  it('links the FAQ from the header, not only the footer', async () => {
    vi.stubGlobal('matchMedia', () => ({
      matches: false,
      addEventListener() {},
      removeEventListener() {}
    }))
    const { createPinia } = await import('pinia')
    const AppHeader = (await import('@/layouts/AppHeader.vue')).default
    const router = routerWith('/', { render: () => null })
    await router.push('/')
    await router.isReady()
    const { h } = await import('vue')
    const { TooltipProvider } = await import('@/components/ui/tooltip')
    wrapper = mount(
      { render: () => h(TooltipProvider, () => h(AppHeader)) },
      { global: { plugins: [router, createPinia()] } }
    )

    const link = wrapper.get('nav a[href="/faq"]')
    expect(link.text()).toBe('FAQ')
    expect(link.attributes('aria-current')).toBeUndefined()
    // Icon-only theme toggle has an accessible name, not just a title
    expect(wrapper.find('button[aria-label="Switch to dark mode"]').exists()).toBe(true)
  })

  it('marks the gene browser active on gene detail routes', async () => {
    vi.stubGlobal('matchMedia', () => ({
      matches: false,
      addEventListener() {},
      removeEventListener() {}
    }))
    const { h } = await import('vue')
    const { createPinia } = await import('pinia')
    const { TooltipProvider } = await import('@/components/ui/tooltip')
    const AppHeader = (await import('@/layouts/AppHeader.vue')).default
    const router = routerWith('/genes/:symbol', { render: () => null })
    await router.push('/genes/PKD1')
    await router.isReady()
    wrapper = mount(
      { render: () => h(TooltipProvider, () => h(AppHeader)) },
      { global: { plugins: [router, createPinia()] } }
    )

    const link = wrapper.get('nav a[href="/genes"]')
    expect(link.attributes('aria-current')).toBe('page')
    expect(link.classes()).toContain('border-primary')
  })
})
