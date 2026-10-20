/**
 * The real user-form checkboxes must reach the submitted payload (#299).
 */

import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest'
import { flushPromises, mount } from '@vue/test-utils'
import { h } from 'vue'
import { TooltipProvider } from '@/components/ui/tooltip'
import AdminUserManagement from '@/views/admin/AdminUserManagement.vue'

const user = {
  id: 3,
  username: 'curator1',
  email: 'curator1@example.org',
  full_name: '',
  role: 'curator',
  is_active: true,
  is_verified: false
}
const self = { ...user, id: 1, username: 'admin', role: 'admin' }
const store = {
  user: { id: 1 },
  getAllUsers: vi.fn(async () => [user, self]),
  updateUser: vi.fn(async (_id: number, updates: object) => ({ ...user, ...updates }))
}
vi.mock('@/stores/auth', () => ({ useAuthStore: () => store }))
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
vi.stubGlobal(
  'matchMedia',
  vi.fn(() => ({ matches: false, addEventListener: vi.fn(), removeEventListener: vi.fn() }))
)

describe('AdminUserManagement user form', () => {
  it('sends the toggled Active and Email Verified values on update', async () => {
    const wrapper = mount(() => h(TooltipProvider, () => h(AdminUserManagement)), {
      global: { stubs: { AdminHeader: true } },
      attachTo: document.body
    })
    await flushPromises()
    ;(document.querySelector('table button.h-8.w-8') as HTMLElement).click() // edit
    await flushPromises()

    const active = document.getElementById('is_active')!
    expect(active.getAttribute('aria-checked')).toBe('true')
    active.click()
    document.getElementById('is_verified')!.click()
    await flushPromises()
    ;[...document.querySelectorAll('button')].find(b => b.textContent?.trim() === 'Update')!.click()
    await flushPromises()

    expect(store.updateUser).toHaveBeenCalledWith(
      3,
      expect.objectContaining({ is_active: false, is_verified: true })
    )
    wrapper.unmount()
  })
})

describe('AdminUserManagement status toggle (#317)', () => {
  let wrapper: ReturnType<typeof mount> | undefined
  beforeEach(() => vi.clearAllMocks())
  afterEach(() => {
    wrapper?.unmount()
    document.body.innerHTML = ''
  })

  async function mountView() {
    wrapper = mount(() => h(TooltipProvider, () => h(AdminUserManagement)), {
      global: { stubs: { AdminHeader: true } },
      attachTo: document.body
    })
    await flushPromises()
  }
  // Row action buttons: [edit, toggle status, delete]
  const rowButtons = (username: string) =>
    [
      ...[...document.querySelectorAll('tbody tr')]
        .find(r => r.textContent?.includes(username))!
        .querySelectorAll('button')
    ] as HTMLElement[]
  const button = (text: string) =>
    [...document.querySelectorAll('button')].find(b => b.textContent?.trim() === text)!

  it('disables the status toggle, Active checkbox and role select on your own row', async () => {
    await mountView()
    expect(rowButtons('admin')[1].hasAttribute('disabled')).toBe(true)
    expect(rowButtons('curator1')[1].hasAttribute('disabled')).toBe(false)

    rowButtons('admin')[0].click() // edit own account
    await flushPromises()
    expect(document.getElementById('is_active')!.hasAttribute('disabled')).toBe(true)
    expect(document.getElementById('role')!.hasAttribute('disabled')).toBe(true)
  })

  it('keeps the role select enabled when editing another user', async () => {
    await mountView()
    rowButtons('curator1')[0].click()
    await flushPromises()
    expect(document.getElementById('role')!.hasAttribute('disabled')).toBe(false)
  })

  it('asks before deactivating another user; Cancel does nothing', async () => {
    await mountView()
    rowButtons('curator1')[1].click()
    await flushPromises()
    expect(document.querySelector('[role="alertdialog"]')?.textContent).toContain('curator1')

    button('Cancel').click()
    await flushPromises()
    expect(store.updateUser).not.toHaveBeenCalled()
  })

  it('deactivates once on confirm', async () => {
    await mountView()
    rowButtons('curator1')[1].click()
    await flushPromises()
    button('Deactivate').click()
    await flushPromises()
    expect(store.updateUser).toHaveBeenCalledTimes(1)
    expect(store.updateUser).toHaveBeenCalledWith(3, { is_active: false })
  })
})
