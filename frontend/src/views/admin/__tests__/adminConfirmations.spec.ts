/**
 * Actions that delete data or start pipeline-wide runs ask first and name their
 * scope (#317): Cancel must not call the API, confirming calls it exactly once.
 */

import { describe, it, expect, vi, afterEach, beforeEach } from 'vitest'
import type { Component, SetupContext } from 'vue'
import { h, ref } from 'vue'
import { flushPromises, mount } from '@vue/test-utils'
import type { VueWrapper } from '@vue/test-utils'
import { TooltipProvider } from '@/components/ui/tooltip'
import AdminBackups from '@/views/admin/AdminBackups.vue'
import AdminPipeline from '@/views/admin/AdminPipeline.vue'
import AdminAnnotations from '@/views/admin/AdminAnnotations.vue'

const backupApi = vi.hoisted(() => ({
  loadStats: vi.fn(async () => ({ total_backups: 3, retention_days: 14 })),
  loadBackups: vi.fn(async () => ({ backups: [], total: 0 })),
  cleanupOldBackups: vi.fn(async () => ({ deleted_count: 2 }))
}))
vi.mock('@/composables/useBackupApi', () => ({
  useBackupApi: () => ({ ...backupApi, loading: ref(false) })
}))

vi.mock('@/api/admin/pipeline', () => ({
  getAllStatus: vi.fn(async () => ({
    data: {
      data: [
        { source_name: 'PanelApp', category: 'data_source', status: 'idle' },
        { source_name: 'HPO', category: 'data_source', status: 'completed' }
      ]
    }
  })),
  triggerUpdate: vi.fn(async () => ({ data: {} }))
}))
import * as pipelineApi from '@/api/admin/pipeline'
vi.mock('@/services/websocket', () => ({
  useWebSocket: () => ({
    connected: ref(false),
    connect: vi.fn(),
    disconnect: vi.fn(),
    subscribe: vi.fn(() => () => {})
  })
}))

vi.mock('@/api/admin/annotations', () => ({
  getAnnotationStatistics: vi.fn(async () => ({ data: {} })),
  getAnnotationSources: vi.fn(async () => ({ data: [] })),
  getPipelineStatus: vi.fn(async () => ({ data: { pipeline_ready: true } })),
  getScheduledJobs: vi.fn(async () => ({ data: { jobs: [] } })),
  triggerPipelineUpdate: vi.fn(async () => ({ data: { task_id: 't1' } }))
}))
import * as annotationsApi from '@/api/admin/annotations'

vi.mock('vue-sonner', () => ({
  toast: { success: vi.fn(), error: vi.fn(), info: vi.fn(), warning: vi.fn() }
}))
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
beforeEach(() => vi.clearAllMocks())
afterEach(() => {
  wrapper?.unmount()
  document.body.innerHTML = ''
})

const button = (text: string) =>
  [...document.querySelectorAll('button')].find(b => b.textContent?.trim() === text) as HTMLElement
const dialogText = () => document.querySelector('[role="alertdialog"]')?.textContent ?? ''

// Renders only the header's actions slot (the real header needs a router)
const HeaderStub = {
  setup:
    (_: unknown, { slots }: SetupContext) =>
    () =>
      h('div', slots.actions?.())
}

async function mountView(view: Component) {
  wrapper = mount(() => h(TooltipProvider, () => h(view)), {
    global: { stubs: { AdminHeader: HeaderStub, DataSourceProgress: true } },
    attachTo: document.body
  })
  await flushPromises()
}

async function click(text: string) {
  button(text).click()
  await flushPromises()
}

const cases = [
  {
    name: 'Backups "Cleanup Old"',
    view: AdminBackups,
    open: 'Cleanup Old',
    confirm: 'Delete Expired Backups',
    scope: '14 days',
    api: () => backupApi.cleanupOldBackups
  },
  {
    name: 'Pipeline "Run All Data Sources"',
    view: AdminPipeline,
    open: 'Run All Data Sources',
    confirm: 'Run All',
    scope: 'PanelApp',
    api: () => pipelineApi.triggerUpdate
  },
  {
    name: 'Annotations "Run Full Update"',
    view: AdminAnnotations,
    open: 'Run Full Update',
    confirm: 'Start Update',
    scope: 'all annotation sources',
    api: () => annotationsApi.triggerPipelineUpdate
  }
]

describe.each(cases)('$name confirmation', ({ view, open, confirm, scope, api }) => {
  it('names the scope and does nothing on Cancel', async () => {
    await mountView(view)
    await click(open)
    expect(dialogText()).toContain(scope)
    await click('Cancel')
    expect(api()).not.toHaveBeenCalled()
    expect(document.querySelector('[role="alertdialog"]')).toBeNull()
  })

  it('calls the API once on confirm', async () => {
    await mountView(view)
    await click(open)
    await click(confirm)
    // Run All triggers each listed source once
    expect(api()).toHaveBeenCalledTimes(view === AdminPipeline ? 2 : 1)
  })
})

describe('Backups cleanup without retention data', () => {
  it('stays disabled when the stats (retention period) fail to load', async () => {
    backupApi.loadStats.mockRejectedValueOnce(new Error('500'))
    await mountView(AdminBackups)
    expect(button('Cleanup Old').hasAttribute('disabled')).toBe(true)
  })
})
