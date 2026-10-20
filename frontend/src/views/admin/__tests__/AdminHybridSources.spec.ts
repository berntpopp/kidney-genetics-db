/**
 * The upload shows an indeterminate state, not a timer-driven percentage (#318).
 */

import { describe, it, expect, vi } from 'vitest'
import { flushPromises, mount } from '@vue/test-utils'
import AdminHybridSources from '@/views/admin/AdminHybridSources.vue'

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

describe('AdminHybridSources upload', () => {
  it('shows an indeterminate status while uploading, with no percentage', async () => {
    vi.useFakeTimers()
    const wrapper = mount(AdminHybridSources, {
      global: { stubs: { AdminHeader: true, AdminStatsCard: true } },
      attachTo: document.body
    })
    await flushPromises()

    const input = wrapper.find('input[type="file"]')
    Object.defineProperty(input.element, 'files', {
      value: [new File(['{}'], 'panels.json', { type: 'application/json' })]
    })
    await input.trigger('change')
    await wrapper
      .findAll('button')
      .find(b => b.text().includes('Upload DiagnosticPanels'))!
      .trigger('click')
    await vi.advanceTimersByTimeAsync(1000)

    const status = wrapper.find('[role="status"]')
    expect(status.text()).toContain('Uploading')
    expect(wrapper.find('[role="progressbar"]').exists()).toBe(false)
    expect(wrapper.text()).not.toMatch(/\d+%/)

    finishUpload({ data: { data: { status: 'success' } } })
    await flushPromises()
    expect(wrapper.find('[role="status"]').exists()).toBe(false)
    wrapper.unmount()
    vi.useRealTimers()
  })
})
