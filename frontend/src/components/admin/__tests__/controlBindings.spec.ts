/**
 * Real Switch/Checkbox controls must reach the submitted admin form values (#299).
 */

import { describe, it, expect, vi, afterEach } from 'vitest'
import { flushPromises, mount } from '@vue/test-utils'
import type { VueWrapper } from '@vue/test-utils'
import BackupCreateDialog from '@/components/admin/backups/BackupCreateDialog.vue'
import BackupRestoreDialog from '@/components/admin/backups/BackupRestoreDialog.vue'

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

const clickButton = (text: string) =>
  [...document.querySelectorAll('button')].find(b => b.textContent?.includes(text))!.click()

describe('admin form switches', () => {
  it('backup create submits the toggled include options', async () => {
    wrapper = mount(BackupCreateDialog, {
      props: { modelValue: true },
      attachTo: document.body
    })
    await flushPromises()
    document.getElementById('include-logs')!.click()
    document.getElementById('include-cache')!.click()
    await flushPromises()
    clickButton('Create Backup')

    expect(wrapper.emitted('create')![0][0]).toMatchObject({
      includeLogs: true,
      includeCache: true
    })
  })
  it('backup restore shows enabled defaults and submits an unticked option', async () => {
    wrapper = mount(BackupRestoreDialog, {
      props: { modelValue: true, backup: { id: 1, filename: 'b.dump' } },
      attachTo: document.body
    })
    await flushPromises()
    const safety = document.getElementById('safety-backup')!
    expect(safety.getAttribute('aria-checked')).toBe('true')
    safety.click()
    await flushPromises()
    clickButton('Restore Database')

    expect(wrapper.emitted('restore')![0][0]).toEqual({
      createSafetyBackup: false,
      runAnalyze: true
    })
  })
})
