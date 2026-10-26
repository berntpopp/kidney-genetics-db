/**
 * Staging review records the logged-in user server-side (#286): the dialogs must
 * not ask for or send a free-text reviewer.
 */

import { describe, it, expect, vi, afterEach } from 'vitest'
import { flushPromises, mount } from '@vue/test-utils'
import type { VueWrapper } from '@vue/test-utils'
import { TooltipProvider } from '@/components/ui/tooltip'
import { h } from 'vue'
import AdminGeneStaging from '@/views/admin/AdminGeneStaging.vue'

vi.mock('@/api/admin/staging', () => ({
  getStagingStats: vi.fn(async () => ({ data: {} })),
  getNormalizationStats: vi.fn(async () => ({ data: {} })),
  getPendingStaging: vi.fn(async () => ({
    data: [
      { id: 7, original_text: 'PKD1', source_name: 'PanelApp', created_at: null },
      { id: 8, original_text: 'PKD2', source_name: 'PanelApp', created_at: null }
    ]
  })),
  approveStaging: vi.fn(async () => ({ data: {} })),
  rejectStaging: vi.fn(async () => ({ data: {} }))
}))
import * as stagingApi from '@/api/admin/staging'

vi.mock('vue-sonner', () => ({ toast: { success: vi.fn(), error: vi.fn(), warning: vi.fn() } }))
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
})

const buttonByText = (text: string) =>
  [...document.querySelectorAll('button')].find(b => b.textContent?.includes(text))!

async function mountView() {
  wrapper = mount(() => h(TooltipProvider, () => h(AdminGeneStaging)), {
    global: { stubs: { AdminHeader: true } },
    attachTo: document.body
  })
  await flushPromises()
}

describe('AdminGeneStaging review dialogs', () => {
  it('approves without a reviewer field or payload key', async () => {
    await mountView()
    ;(document.querySelector('button.text-green-600') as HTMLElement).click()
    await flushPromises()

    expect(document.body.textContent).not.toContain('Your Name/ID')
    // The pipeline uses the pair as-is, so the HGNC ID is required (#375)
    expect(buttonByText('Approve as Valid Gene').hasAttribute('disabled')).toBe(true)
    const hgnc = document.querySelector('#approve-hgnc') as HTMLElement & { value: string }
    hgnc.value = 'HGNC:9008'
    hgnc.dispatchEvent(new Event('input'))
    await flushPromises()
    buttonByText('Approve as Valid Gene').click()
    await flushPromises()

    expect(stagingApi.approveStaging).toHaveBeenCalledWith(7, {
      approved_symbol: 'PKD1',
      hgnc_id: 'HGNC:9008',
      notes: null
    })
  })
  it('offers no row selection or bulk actions the API cannot perform (#318)', async () => {
    await mountView()
    expect(document.querySelectorAll('table [role="checkbox"]')).toHaveLength(0)
    expect(document.body.textContent).not.toContain('Bulk')
  })
})
