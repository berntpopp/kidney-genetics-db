/**
 * The admin LogViewer must not load for every visitor (#328): it mounts on first open
 * and then stays mounted.
 */
import { describe, it, expect, vi } from 'vitest'
import { flushPromises, mount } from '@vue/test-utils'
import { defineComponent, h } from 'vue'
import { createPinia, setActivePinia } from 'pinia'
import { createHead } from '@unhead/vue/client'
import { createRouter, createMemoryHistory } from 'vue-router'
import App from '@/App.vue'
import { useLogStore } from '@/stores/logStore'

// The factory runs when the module is first imported, so it detects an eager (static) import
const logViewerModule = vi.hoisted(() => ({ loaded: false }))
vi.mock('@/components/admin/LogViewer.vue', () => {
  logViewerModule.loaded = true
  return {
    __esModule: true,
    default: defineComponent({ render: () => h('div', { id: 'log-viewer' }) })
  }
})
vi.stubGlobal('logService', { info: vi.fn(), warn: vi.fn(), error: vi.fn(), debug: vi.fn() })
vi.stubGlobal(
  'matchMedia',
  vi.fn(() => ({ matches: false, addEventListener: vi.fn(), removeEventListener: vi.fn() }))
)

describe('LogViewer loading', () => {
  it('mounts only after the viewer is first opened, then stays mounted', async () => {
    const router = createRouter({
      history: createMemoryHistory(),
      routes: [{ path: '/', component: { render: () => null } }]
    })
    await router.push('/')
    const pinia = createPinia()
    setActivePinia(pinia)
    const wrapper = mount(App, {
      global: {
        plugins: [router, pinia, createHead()],
        stubs: { AppHeader: true, AppFooter: true, Toaster: true }
      }
    })
    await flushPromises()
    expect(logViewerModule.loaded).toBe(false)
    expect(wrapper.find('#log-viewer').exists()).toBe(false)

    const logStore = useLogStore()
    logStore.showViewer()
    await flushPromises()
    await vi.dynamicImportSettled()
    await flushPromises()
    expect(logViewerModule.loaded).toBe(true)
    expect(wrapper.find('#log-viewer').exists()).toBe(true)

    logStore.hideViewer()
    await flushPromises()
    expect(wrapper.find('#log-viewer').exists()).toBe(true)
    wrapper.unmount()
  })
})
