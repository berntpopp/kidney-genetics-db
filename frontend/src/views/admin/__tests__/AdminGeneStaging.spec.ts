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
import { Select } from '@/components/ui/select'

vi.mock('@/api/admin/staging', () => ({
  getStagingStats: vi.fn(async () => ({ data: {} })),
  getNormalizationStats: vi.fn(async () => ({ data: {} })),
  getPendingStaging: vi.fn(async () => ({
    data: {
      items: [
        { id: 7, original_text: 'PKD1', source_name: 'PanelApp', created_at: null },
        { id: 8, original_text: 'PKD2', source_name: 'PanelApp', created_at: null }
      ],
      pagination: { total: 2, limit: 25, offset: 0, has_more: false }
    }
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
  vi.mocked(stagingApi.getPendingStaging).mockClear()
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

describe('AdminGeneStaging server paging (#422)', () => {
  const page = (offset: number, count: number, total: number) => ({
    data: {
      items: Array.from({ length: count }, (_, i) => ({
        id: 100 + offset + i,
        original_text: `GENE${offset + i}`,
        source_name: 'PanelApp',
        created_at: null
      })),
      pagination: { total, limit: 25, offset, has_more: offset + count < total }
    }
  })
  const rows = () => [...document.querySelectorAll('tbody tr')]
  const lastCall = () => vi.mocked(stagingApi.getPendingStaging).mock.calls.at(-1)?.[0]
  const nextPage = async () => {
    ;(document.querySelector('[aria-label="Go to next page"]') as HTMLElement).click()
    await flushPromises()
  }

  it('reaches every pending item by paging on the server', async () => {
    vi.mocked(stagingApi.getPendingStaging)
      .mockResolvedValueOnce(page(0, 25, 402) as never)
      .mockResolvedValueOnce(page(25, 25, 402) as never)
    await mountView()
    expect(lastCall()).toEqual({ limit: 25, offset: 0 })
    expect(rows()).toHaveLength(25)
    expect(document.body.textContent).toContain('402 pending items')
    expect(document.body.textContent).toContain('Page 1 of 17')
    expect(document.body.textContent).not.toContain('highest-priority')

    await nextPage()
    expect(lastCall()).toEqual({ limit: 25, offset: 25 })
    expect(rows()[0]?.querySelector('code')?.textContent).toBe('GENE25')
  })

  it('sends the expert and search filters to the server from the first page', async () => {
    for (let i = 0; i < 4; i++) {
      vi.mocked(stagingApi.getPendingStaging).mockResolvedValueOnce(page(0, 25, 402) as never)
    }
    await mountView()
    await nextPage()
    expect(lastCall()).toMatchObject({ offset: 25 })

    ;(document.querySelector('#expert-only') as HTMLElement).click()
    await flushPromises()
    expect(lastCall()).toEqual({ limit: 25, offset: 0, requires_expert_review: true })

    const search = document.querySelector('[aria-label="Search gene text"]') as HTMLElement & {
      value: string
    }
    search.value = ' gene29 '
    search.dispatchEvent(new Event('input'))
    await new Promise(resolve => setTimeout(resolve, 350)) // search is debounced
    await flushPromises()
    expect(lastCall()).toEqual({
      limit: 25,
      offset: 0,
      requires_expert_review: true,
      search: 'gene29'
    })
  })

  it('sends the chosen source to the server', async () => {
    await mountView()
    // The Select popup does not open in jsdom, so choose through its v-model
    wrapper!.findComponent(Select).vm.$emit('update:modelValue', 'ClinGen')
    await flushPromises()
    expect(lastCall()).toEqual({ limit: 25, offset: 0, source_filter: 'ClinGen' })
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
