/**
 * An invalid change-password submit focuses the offending field and links it to the error (#327).
 */

import { describe, it, expect, vi, afterEach } from 'vitest'
import { flushPromises, mount, type VueWrapper } from '@vue/test-utils'
import { createPinia } from 'pinia'
import { createRouter, createMemoryHistory } from 'vue-router'
import Profile from '@/views/Profile.vue'

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
  wrapper = mount(Profile, {
    global: { plugins: [router, createPinia()] },
    attachTo: document.body
  })
  await flushPromises()
  await wrapper.find('#current-password').setValue(current)
  await wrapper.find('#new-password').setValue(next)
  await wrapper.find('#confirm-password').setValue(confirm)
  const form = wrapper.find('#current-password').element.closest('form')!
  ;(form.querySelector('button[type="submit"]') as HTMLElement).focus()
  form.dispatchEvent(new Event('submit'))
  await flushPromises()
  return wrapper
}

describe('Profile change password', () => {
  it.each([
    ['', '', '', 'current-password'],
    ['old', '', '', 'new-password'],
    ['old', 'Str0ng!pass', 'other', 'confirm-password'],
    ['old', 'short', 'short', 'new-password']
  ])('focuses and links the invalid field for %j/%j/%j (#327)', async (c, n, f, field) => {
    const w = await submit(c, n, f)
    const input = w.find(`#${field}`)
    expect(document.activeElement?.id).toBe(field)
    expect(input.attributes('aria-invalid')).toBe('true')
    expect(input.attributes('aria-describedby')).toBe('password-error')
    expect(w.find('#password-error').attributes('role')).toBe('alert')
    for (const other of ['current-password', 'new-password', 'confirm-password']) {
      if (other !== field)
        expect(w.find(`#${other}`).attributes('aria-describedby')).toBeUndefined()
    }
    expect(authApi.changePassword).not.toHaveBeenCalled()
  })
})
