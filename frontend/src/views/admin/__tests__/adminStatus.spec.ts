/**
 * Admin status displays say why they warn and stay quiet without a user action (#327).
 */

import { describe, it, expect, vi, afterEach } from 'vitest'
import { h, nextTick, ref } from 'vue'
import { flushPromises, mount } from '@vue/test-utils'
import type { VueWrapper } from '@vue/test-utils'
import { TooltipProvider } from '@/components/ui/tooltip'
import { Badge } from '@/components/ui/badge'
import AdminCacheManagement from '@/views/admin/AdminCacheManagement.vue'
import AdminPipeline from '@/views/admin/AdminPipeline.vue'
import { getCacheNamespaces } from '@/api/admin/cache'
import { getAllStatus } from '@/api/admin/pipeline'

vi.mock('@/api/admin/cache', () => ({
  getCacheStats: vi.fn(async () => ({
    data: { hit_rate: 0.3, total_entries: 5, total_size_bytes: 0 }
  })),
  getCacheNamespaces: vi.fn(async () => ({ data: [] })),
  getCacheHealth: vi.fn(async () => ({
    data: {
      status: 'warning',
      cache_enabled: true,
      database_connected: true,
      issues: ['Low cache hit rate: 30.0%']
    }
  }))
}))
vi.mock('@/api/admin/pipeline', () => ({
  getAllStatus: vi.fn(async () => ({
    data: {
      data: [
        { source_name: 'HPO', category: 'data_source', status: 'completed' },
        // 11 minutes without a progress write: stalled
        {
          source_name: 'GenCC',
          category: 'data_source',
          status: 'running',
          last_update_at: new Date(Date.now() - 11 * 60_000).toISOString()
        },
        // 2 minutes: still running
        {
          source_name: 'PanelApp',
          category: 'data_source',
          status: 'running',
          last_update_at: new Date(Date.now() - 2 * 60_000).toISOString()
        },
        // No heartbeat from an older backend: keep the plain status
        {
          source_name: 'ClinGen',
          category: 'data_source',
          status: 'running',
          last_update_at: null
        },
        {
          source_name: 'annotation_pipeline',
          display_name: 'Gene Annotation Pipeline',
          category: 'internal_process',
          status: 'running',
          current_operation: '1/4 sources done · hpo: fetching',
          current_item: 1,
          total_items: 4,
          progress_percentage: 25,
          started_at: new Date(Date.now() - 6 * 60_000).toISOString(),
          last_update_at: new Date(Date.now() - 30_000).toISOString(),
          estimated_completion: new Date(Date.now() + 4.2 * 60_000).toISOString()
        }
      ]
    }
  }))
}))
vi.mock('@/services/websocket', () => ({
  useWebSocket: () => ({
    connected: ref(false),
    connect: vi.fn(),
    disconnect: vi.fn(),
    subscribe: vi.fn(() => () => {})
  })
}))
vi.mock('vue-sonner', () => ({
  toast: { success: vi.fn(), error: vi.fn(), info: vi.fn(), warning: vi.fn() }
}))
import { toast } from 'vue-sonner'
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
afterEach(() => wrapper?.unmount())

async function mountView(view: object) {
  wrapper = mount(() => h(TooltipProvider, () => h(view)), {
    global: { stubs: { AdminHeader: true } }
  })
  await flushPromises()
  return wrapper
}

describe('AdminCacheManagement health', () => {
  it('lists the API health issues next to the warning status', async () => {
    const w = await mountView(AdminCacheManagement)
    expect(w.text()).toContain('Cache Health Status: warning')
    expect(w.find('[data-testid="health-issues"]').text()).toContain('Low cache hit rate: 30.0%')
  })

  it('fires no toast on page load', async () => {
    await mountView(AdminCacheManagement)
    expect(toast.success).not.toHaveBeenCalled()
  })

  it('hides Memory Usage when the backend reports no size', async () => {
    const w = await mountView(AdminCacheManagement)
    expect(w.text()).not.toContain('Memory Usage')
  })

  it('lists every namespace unpaginated in API order', async () => {
    const names = Array.from({ length: 12 }, (_, i) => `ns${12 - i}`)
    vi.mocked(getCacheNamespaces).mockResolvedValueOnce({
      data: names.map(namespace => ({ namespace, entry_count: 1, size_mb: 0 }))
    } as never)
    const w = await mountView(AdminCacheManagement)
    expect(w.findAll('tbody tr').map(r => r.find('td').text())).toEqual(names)
  })
})

describe('AdminPipeline status badge', () => {
  it('shows Completed with the outline badge variant', async () => {
    const w = await mountView(AdminPipeline)
    const badge = w.findAllComponents(Badge).find(b => b.text() === 'completed')!
    expect(badge.props('variant')).toBe('outline')
  })
})

describe('AdminPipeline stalled sources', () => {
  const badgeOf = (w: VueWrapper, name: string) =>
    w
      .findAll('[data-testid="source-card"]')
      .find(c => c.text().includes(name))!
      .findComponent(Badge)

  it('flags a running source with no progress update for over 10 minutes', async () => {
    const w = await mountView(AdminPipeline)
    const badge = badgeOf(w, 'GenCC')
    expect(badge.text()).toBe('stalled')
    expect(badge.props('variant')).toBe('destructive')
    expect(badge.attributes('title')).toContain('last progress update 11 min ago')
  })

  it('keeps running for recent updates and when last_update_at is missing', async () => {
    const w = await mountView(AdminPipeline)
    expect(badgeOf(w, 'PanelApp').text()).toBe('running')
    expect(badgeOf(w, 'ClinGen').text()).toBe('running')
  })

  it('turns a source stalled while the page stays open', async () => {
    vi.useFakeTimers({ toFake: ['Date', 'setInterval', 'clearInterval'] })
    try {
      const w = await mountView(AdminPipeline)
      expect(badgeOf(w, 'PanelApp').text()).toBe('running')
      vi.advanceTimersByTime(9 * 60_000)
      await nextTick()
      expect(badgeOf(w, 'PanelApp').text()).toBe('stalled')
    } finally {
      vi.useRealTimers()
    }
  })
})

describe('AdminPipeline annotation pipeline card', () => {
  const card = (w: VueWrapper) =>
    w.findAll('.border-dashed').find(c => c.text().includes('Gene Annotation Pipeline'))!

  it('shows sources done, percentage and both timestamps from the progress row', async () => {
    const w = await mountView(AdminPipeline)
    const text = card(w).text()
    expect(text).toContain('1/4 sources done · hpo: fetching')
    expect(text).toContain('25%')
    expect(text).toContain('Started: 6 min ago')
    expect(card(w).find('[role="status"]').text()).toBe('1 of 4 sources done')
    expect(text).toContain('About 5 min left') // 4.2 min rounds up
  })

  it('says so when the run passes its estimate instead of counting below zero', async () => {
    vi.useFakeTimers({ toFake: ['Date', 'setInterval', 'clearInterval'] })
    const snapshot = await getAllStatus()
    vi.mocked(getAllStatus).mockImplementation(async () => snapshot)
    try {
      const w = await mountView(AdminPipeline)
      vi.advanceTimersByTime(5 * 60_000)
      await flushPromises()
      expect(card(w).text()).toContain('Running longer than estimated')
    } finally {
      vi.useRealTimers()
    }
  })

  it('keeps relative times counting and polls while the socket is down', async () => {
    vi.useFakeTimers({ toFake: ['Date', 'setInterval', 'clearInterval'] })
    const snapshot = await getAllStatus() // the same row on every poll, as the server would send
    vi.mocked(getAllStatus).mockImplementation(async () => snapshot)
    try {
      const w = await mountView(AdminPipeline)
      const calls = vi.mocked(getAllStatus).mock.calls.length
      vi.advanceTimersByTime(2 * 60_000)
      await flushPromises()
      expect(card(w).text()).toContain('Started: 8 min ago')
      expect(vi.mocked(getAllStatus).mock.calls.length).toBeGreaterThan(calls)
    } finally {
      vi.useRealTimers()
    }
  })
})
