/**
 * The real user-form checkboxes must reach the submitted payload (#299).
 */

import { describe, it, expect, vi } from 'vitest'
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
const store = {
  getAllUsers: vi.fn(async () => [user]),
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
    ;(document.querySelector('table button.h-8.w-8') as HTMLButtonElement).click() // edit
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
