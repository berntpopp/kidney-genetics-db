/**
 * Admin status displays say why they warn and stay quiet without a user action (#327).
 */

import { describe, it, expect, vi, afterEach } from 'vitest'
import { h, ref } from 'vue'
import { flushPromises, mount } from '@vue/test-utils'
import type { VueWrapper } from '@vue/test-utils'
import { TooltipProvider } from '@/components/ui/tooltip'
import { Badge } from '@/components/ui/badge'
import AdminCacheManagement from '@/views/admin/AdminCacheManagement.vue'
import AdminPipeline from '@/views/admin/AdminPipeline.vue'

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
    data: { data: [{ source_name: 'HPO', category: 'data_source', status: 'completed' }] }
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
})

describe('AdminPipeline status badge', () => {
  it('shows Completed with the outline badge variant', async () => {
    const w = await mountView(AdminPipeline)
    const badge = w.findAllComponents(Badge).find(b => b.text() === 'completed')!
    expect(badge.props('variant')).toBe('outline')
  })
})
