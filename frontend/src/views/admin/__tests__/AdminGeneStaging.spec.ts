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
    ;(document.querySelector('button[aria-label="Approve PKD1"]') as HTMLElement).click()
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

describe('AdminGeneStaging reach (all pending items)', () => {
  const many = Array.from({ length: 30 }, (_, i) => ({
    id: 100 + i,
    original_text: `GENE${i}`,
    source_name: i % 2 ? 'PanelApp' : 'DiagnosticPanels',
    requires_expert_review: i === 3,
    created_at: null
  }))
  const rows = () => [...document.querySelectorAll('tbody tr')]

  it('requests the API maximum and says how many of the pending total are loaded', async () => {
    vi.mocked(stagingApi.getStagingStats).mockResolvedValueOnce({
      data: { total_pending: 402 }
    } as never)
    await mountView()
    expect(stagingApi.getPendingStaging).toHaveBeenCalledWith({ limit: 200 })
    expect(document.querySelector('[data-testid="staging-scope"]')?.textContent).toContain(
      'of 402 pending'
    )
  })

  it('pages 25 rows at a time and searches across every loaded item', async () => {
    vi.mocked(stagingApi.getPendingStaging).mockResolvedValueOnce({ data: many } as never)
    await mountView()
    expect(rows()).toHaveLength(25)
    ;(document.querySelector('[aria-label="Go to next page"]') as HTMLElement).click()
    await flushPromises()
    expect(rows()).toHaveLength(5)

    const search = document.querySelector('[aria-label="Search gene text"]') as HTMLInputElement
    search.value = 'gene29'
    search.dispatchEvent(new Event('input'))
    await flushPromises()
    expect(rows().map(r => r.querySelector('code')?.textContent)).toEqual(['GENE29'])
  })

  it('shows an inline error with Retry instead of an empty list when loading fails', async () => {
    vi.mocked(stagingApi.getPendingStaging).mockRejectedValueOnce(new Error('500'))
    await mountView()
    expect(document.querySelector('[data-state="error"]')?.textContent).toContain(
      'Could not load pending reviews'
    )
    expect(document.body.textContent).not.toContain('Nothing to review')
  })
})
