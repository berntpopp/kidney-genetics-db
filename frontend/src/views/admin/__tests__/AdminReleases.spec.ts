/** The release details show the curated data frozen in the export (#546). */

import { describe, it, expect, vi } from 'vitest'
import { flushPromises, mount } from '@vue/test-utils'
import { h } from 'vue'
import { TooltipProvider } from '@/components/ui/tooltip'
import AdminReleases from '@/views/admin/AdminReleases.vue'
import { listReleases } from '@/api/admin/releases'

vi.mock('@/api/admin/releases', () => ({
  listReleases: vi.fn(),
  downloadReleaseExport: vi.fn()
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

const release = (extra = {}) => ({
  id: 1,
  version: '2026.11',
  status: 'published',
  gene_count: 5080,
  published_at: '2026-11-03T10:00:00Z',
  created_at: '2026-11-03T09:00:00Z',
  updated_at: '2026-11-03T10:00:00Z',
  export_checksum: 'a'.repeat(64),
  ...extra
})

async function details(item: object) {
  vi.mocked(listReleases).mockResolvedValue({ data: { data: [item] } } as never)
  const w = mount(() => h(TooltipProvider, () => h(AdminReleases)), {
    attachTo: document.body,
    global: { stubs: { AdminHeader: true } }
  })
  await flushPromises()
  await w.find('tbody tr').trigger('click')
  await flushPromises()
  expect(document.body.textContent).toContain('Gene Count') // the details dialog is open
  const text = document.querySelector('[data-testid="release-curated-counts"]')?.textContent
  w.unmount()
  return text?.replace(/\s+/g, ' ').trim()
}

describe('AdminReleases curated counts', () => {
  it('shows association and no-association counts, including zero', async () => {
    expect(await details(release({ association_count: 1234, no_association_count: 0 }))).toContain(
      '1,234 associations, 0 no-association statements'
    )
  })

  it('hides the row for releases exported before curated data', async () => {
    expect(await details(release())).toBeUndefined()
  })
})
