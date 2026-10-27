/**
 * An invalid change-password submit focuses the offending field and links it to the error (#327).
 */

import { describe, it, expect, vi, afterEach } from 'vitest'
import { flushPromises, mount, type VueWrapper } from '@vue/test-utils'
import { createPinia } from 'pinia'
import { createRouter, createMemoryHistory } from 'vue-router'
import Profile from '@/views/Profile.vue'
import { expectLinkedError, field, withTooltips } from '@/components/auth/__tests__/formTestUtils'

vi.mock('@/api/auth', () => ({ changePassword: vi.fn() }))
import * as authApi from '@/api/auth'
vi.stubGlobal('logService', { info: vi.fn(), warn: vi.fn(), error: vi.fn(), debug: vi.fn() })

let wrapper: VueWrapper | undefined
afterEach(() => wrapper?.unmount())

async function submit(current = '', next = '', confirm = '') {
  const router = createRouter({
    history: createMemoryHistory(),
    routes: [{ path: '/:rest(.*)', component: { render: () => null } }]
  })
  wrapper = mount(withTooltips(Profile), {
    global: { plugins: [router, createPinia()] },
    attachTo: document.body
  })
  await flushPromises()
  await wrapper.find('input[name="currentPassword"]').setValue(current)
  await wrapper.find('input[name="newPassword"]').setValue(next)
  await wrapper.find('input[name="confirmPassword"]').setValue(confirm)
  const form = wrapper.find('form')
  ;(form.find('button[type="submit"]').element as HTMLElement).focus()
  await form.trigger('submit')
  // vee-validate validates asynchronously before calling the submit handler
  await new Promise(resolve => setTimeout(resolve, 10))
  await flushPromises()
  return wrapper
}

describe('Profile change password', () => {
  it.each([
    ['', '', '', 'currentPassword'],
    ['old', '', '', 'newPassword'],
    ['old', 'Str0ng!pass', 'other', 'confirmPassword'],
    ['old', 'short', 'short', 'newPassword']
  ])('focuses and links the invalid field for %j/%j/%j (#327)', async (c, n, f, name) => {
    const w = await submit(c, n, f)
    expect(document.activeElement?.getAttribute('name')).toBe(name)
    expectLinkedError(w.element, name)
    if (c) expect(field(w.element, 'currentPassword').getAttribute('aria-invalid')).toBe('false')
    expect(authApi.changePassword).not.toHaveBeenCalled()
  })

  it('shows account data as text, not disabled inputs', async () => {
    const w = await submit()
    expect(w.findAll('input[disabled]').length).toBe(0)
    expect(w.find('dl').exists()).toBe(true)
  })
})
