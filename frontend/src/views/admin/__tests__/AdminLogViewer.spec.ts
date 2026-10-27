/** Request columns appear only when a row on the page has request data (#423). */

import { describe, it, expect, vi } from 'vitest'
import { flushPromises, mount } from '@vue/test-utils'
import { h } from 'vue'
import { TooltipProvider } from '@/components/ui/tooltip'
import AdminLogViewer from '@/views/admin/AdminLogViewer.vue'
import { queryLogs } from '@/api/admin/logs'

const log = (id: number, extra = {}) => ({
  id,
  timestamp: '2026-10-27T10:00:00Z',
  level: 'INFO',
  message: `message ${id}`,
  ...extra
})

vi.mock('@/api/admin/logs', () => ({
  queryLogs: vi.fn(),
  getLogStatistics: vi.fn(async () => ({ data: {} })),
  cleanupLogs: vi.fn(),
  exportLogs: vi.fn()
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

async function headers(logs: object[]) {
  vi.mocked(queryLogs).mockResolvedValue({
    data: { logs, pagination: { total: logs.length } }
  } as never)
  const w = mount(() => h(TooltipProvider, () => h(AdminLogViewer)), {
    global: { stubs: { AdminHeader: true } }
  })
  await flushPromises()
  const names = w.findAll('thead th').map(th => th.text())
  w.unmount()
  return names
}

describe('AdminLogViewer request columns', () => {
  it('hides Method, Path, Status and Duration when no row has them', async () => {
    expect(await headers([log(1), log(2)])).toEqual(['Timestamp', 'Level', 'Message', 'Actions'])
  })

  it('shows them when any row is a request log', async () => {
    const names = await headers([
      log(1),
      log(2, { method: 'GET', path: '/api/genes', status_code: 200, duration_ms: 12 })
    ])
    expect(names).toEqual([
      'Timestamp',
      'Level',
      'Method',
      'Path',
      'Status',
      'Duration',
      'Message',
      'Actions'
    ])
  })
})
