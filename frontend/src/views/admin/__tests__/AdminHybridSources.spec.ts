/**
 * The upload shows an indeterminate state, not a timer-driven percentage (#318), and a
 * Replace upload (deletes the provider's existing data) is confirmed first.
 */

import { describe, it, expect, vi, afterEach } from 'vitest'
import { flushPromises, mount } from '@vue/test-utils'
import type { VueWrapper } from '@vue/test-utils'
import { h } from 'vue'
import { TooltipProvider } from '@/components/ui/tooltip'
import AdminHybridSources from '@/views/admin/AdminHybridSources.vue'
import * as ingestionApi from '@/api/admin/ingestion'

let finishUpload: (_v: unknown) => void = () => {}
vi.mock('@/api/admin/ingestion', () => ({
  getSourceStatus: vi.fn(async () => ({ data: { data: {} } })),
  listUploads: vi.fn(async () => ({ data: { data: [] } })),
  getAuditTrail: vi.fn(async () => ({ data: { data: [] } })),
  listIdentifiers: vi.fn(async () => ({ data: { data: { identifiers: [] } } })),
  uploadSourceFile: vi.fn(() => new Promise(resolve => (finishUpload = resolve)))
}))
vi.mock('vue-sonner', () => ({ toast: { success: vi.fn(), error: vi.fn() } }))
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
  document.body.innerHTML = ''
  vi.clearAllMocks()
})

async function mountWithFile() {
  wrapper = mount(() => h(TooltipProvider, () => h(AdminHybridSources)), {
    global: { stubs: { AdminHeader: true, AdminStatsCard: true } },
    attachTo: document.body
  })
  await flushPromises()
  const input = wrapper.find('input[type="file"]')
  Object.defineProperty(input.element, 'files', {
    value: [new File(['{}'], 'panels.json', { type: 'application/json' })]
  })
  await input.trigger('change')
}

const button = (text: string) =>
  [...document.querySelectorAll('button')].find(b => b.textContent?.includes(text)) as HTMLElement

describe('AdminHybridSources upload', () => {
  it('"Browse files" opens the hidden file picker', async () => {
    await mountWithFile()
    const input = document.querySelector('input[type="file"]')!
    const click = vi.spyOn(input, 'click').mockImplementation(() => {})
    button('Browse files').click()
    expect(click).toHaveBeenCalledTimes(1)
  })

  it('shows an indeterminate status while uploading, with no percentage', async () => {
    vi.useFakeTimers()
    await mountWithFile()
    button('Upload diagnostic panels file').click()
    await vi.advanceTimersByTimeAsync(1000)

    const status = wrapper!.find('[role="status"]')
    expect(status.text()).toContain('Uploading')
    expect(wrapper!.find('[role="progressbar"]').exists()).toBe(false)
    expect(wrapper!.text()).not.toMatch(/\d+%/)

    finishUpload({ data: { data: { status: 'success' } } })
    await flushPromises()
    expect(wrapper!.find('p[role="status"]').exists()).toBe(false)
    vi.useRealTimers()
  })

  it('asks before a Replace upload; Cancel uploads nothing', async () => {
    await mountWithFile()
    document.getElementById('mode-replace')!.click()
    await flushPromises()
    button('Replace with diagnostic panels file').click()
    await flushPromises()

    expect(document.querySelector('[role="alertdialog"]')?.textContent).toContain('deleted')
    button('Cancel').click()
    await flushPromises()
    expect(ingestionApi.uploadSourceFile).not.toHaveBeenCalled()

    button('Replace with diagnostic panels file').click()
    await flushPromises()
    button('Replace data').click()
    await flushPromises()
    expect(ingestionApi.uploadSourceFile).toHaveBeenCalledWith(
      'DiagnosticPanels',
      expect.any(File),
      null,
      'replace'
    )
  })
})
