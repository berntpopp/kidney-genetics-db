/**
 * Accessible names and keyboard operability for shared controls (#322).
 */

import { describe, it, expect, vi, afterEach } from 'vitest'
import { flushPromises, mount } from '@vue/test-utils'
import type { VueWrapper } from '@vue/test-utils'
import { defineComponent, h, ref } from 'vue'
import { createPinia } from 'pinia'
import { createRouter, createMemoryHistory, RouterView } from 'vue-router'
import { getCoreRowModel, getPaginationRowModel, useVueTable } from '@tanstack/vue-table'
import DataTablePagination from '@/components/ui/data-table/DataTablePagination.vue'
import HoverPopover from '@/components/ui/HoverPopover.vue'

vi.mock('@unhead/vue', () => ({ useHead: vi.fn() }))
vi.mock('@/api/datasources', () => ({
  datasourceApi: {
    getDataSources: vi.fn().mockResolvedValue({
      total_unique_genes: 5080,
      total_active: 7,
      last_data_update: '2026-10-01T00:00:00Z',
      sources: []
    })
  }
}))
vi.stubGlobal('logService', { info: vi.fn(), warn: vi.fn(), error: vi.fn(), debug: vi.fn() })

let wrapper: VueWrapper | undefined
afterEach(() => {
  wrapper?.unmount()
  wrapper = undefined
  document.body.innerHTML = ''
})

const blank = { render: () => null }

async function mountRoute(path: string, component: object, extraRoutes: string[] = []) {
  const router = createRouter({
    history: createMemoryHistory(),
    routes: [{ path, component }, ...extraRoutes.map(p => ({ path: p, component: blank }))]
  })
  await router.push(path)
  await router.isReady()
  wrapper = mount(RouterView, {
    global: { plugins: [router, createPinia()], stubs: { KGDBLogo: true } },
    attachTo: document.body
  })
  await flushPromises()
  return { w: wrapper, router }
}

/** Accessible name of an icon-only control: aria-label, title or text. */
const nameOf = (el: Element) =>
  el.getAttribute('aria-label') || el.getAttribute('title') || el.textContent?.trim() || ''

describe('DataTablePagination', () => {
  it('names every control and pages forward by its name', async () => {
    const Host = defineComponent({
      setup() {
        const data = ref(Array.from({ length: 25 }, (_, i) => ({ id: i })))
        const table = useVueTable({
          get data() {
            return data.value
          },
          columns: [{ accessorKey: 'id' }],
          getCoreRowModel: getCoreRowModel(),
          getPaginationRowModel: getPaginationRowModel(),
          initialState: { pagination: { pageSize: 10 } }
        })
        return () => h(DataTablePagination, { table })
      }
    })
    wrapper = mount(Host)

    const controls = wrapper.findAll('button')
    expect(controls.length).toBe(5)
    for (const c of controls) expect(nameOf(c.element)).not.toBe('')
    expect(wrapper.find('[role="combobox"]').attributes('aria-label')).toBe('Rows per page')

    await wrapper.get('button[aria-label="Go to next page"]').trigger('click')
    expect(wrapper.text()).toContain('Page 2 of 3')
  })
})

describe('HoverPopover', () => {
  it('uses a real button trigger that toggles on activation and closes on Escape', async () => {
    wrapper = mount(HoverPopover, {
      slots: { default: () => 'pLI 0.98', content: () => h('p', 'popover body') },
      attachTo: document.body
    })
    const trigger = wrapper.get('button')
    expect(trigger.attributes('type')).toBe('button')
    expect(trigger.text()).toBe('pLI 0.98')
    expect(trigger.attributes('aria-expanded')).toBe('false')

    // Enter/Space on a native button dispatch click
    await trigger.trigger('click')
    await flushPromises()
    expect(trigger.attributes('aria-expanded')).toBe('true')
    expect(document.body.textContent).toContain('popover body')

    document.dispatchEvent(new window.KeyboardEvent('keydown', { key: 'Escape', bubbles: true }))
    await flushPromises()
    expect(trigger.attributes('aria-expanded')).toBe('false')
  })
})

describe('Home stat cards', () => {
  it('renders routed cards as links that navigate', async () => {
    const Home = (await import('@/views/Home.vue')).default
    const { w, router } = await mountRoute('/', Home, ['/genes', '/data-sources', '/about'])

    const genes = w.get('a.stat-card[href="/genes"]')
    expect(genes.text()).toContain('Genes with Evidence')
    expect(w.find('a.stat-card[href="/data-sources"]').exists()).toBe(true)
    // The non-routed card stays a plain element, not a fake control
    expect(w.findAll('a.stat-card')).toHaveLength(2)

    await genes.trigger('click')
    await flushPromises()
    expect(router.currentRoute.value.path).toBe('/genes')
  })
})

describe('Dashboard tier chips', () => {
  it('are toggle buttons reporting their pressed state', async () => {
    const Dashboard = (await import('@/views/Dashboard.vue')).default
    const { w } = await mountRoute('/dashboard', Dashboard)

    const chips = w.findAll('button[aria-pressed]')
    expect(chips.length).toBeGreaterThan(0)
    expect(chips.every(c => c.attributes('type') === 'button')).toBe(true)
    expect(chips[0].attributes('aria-pressed')).toBe('false')

    await chips[0].trigger('click')
    expect(w.findAll('button[aria-pressed]')[0].attributes('aria-pressed')).toBe('true')
  })
})

describe('MCP code blocks', () => {
  it('are keyboard-focusable so they can be scrolled', async () => {
    const MCP = (await import('@/views/MCP.vue')).default
    const { w } = await mountRoute('/mcp', MCP)

    const blocks = w.findAll('pre')
    expect(blocks.length).toBeGreaterThan(0)
    for (const pre of blocks) expect(pre.attributes('tabindex')).toBe('0')
  })
})

describe('App shell skip link', () => {
  it('is the first focusable element and targets the main landmark', async () => {
    const App = (await import('@/App.vue')).default
    const router = createRouter({
      history: createMemoryHistory(),
      routes: [{ path: '/', component: blank }]
    })
    await router.push('/')
    await router.isReady()
    wrapper = mount(App, {
      global: {
        plugins: [router, createPinia()],
        stubs: { AppHeader: { template: '<header><a href="/">Home</a></header>' }, AppFooter: true }
      },
      attachTo: document.body
    })

    const first = document.querySelector('a[href], button')
    expect(first?.getAttribute('href')).toBe('#main-content')
    expect(first?.textContent?.trim()).toBe('Skip to main content')
    const main = document.getElementById('main-content')
    expect(main?.tagName).toBe('MAIN')
    expect(main?.getAttribute('tabindex')).toBe('-1')
  })
})
