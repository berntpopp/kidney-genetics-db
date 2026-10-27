/**
 * The header login modal announces errors like the standalone Login page (#327).
 */

import { describe, it, expect, vi, afterEach } from 'vitest'
import { DOMWrapper, flushPromises, mount, type VueWrapper } from '@vue/test-utils'
import { createPinia } from 'pinia'
import LoginModal from '@/components/auth/LoginModal.vue'
import { expectLinkedError, withTooltips } from './formTestUtils'

vi.mock('@/api/auth', () => ({ login: vi.fn() }))
import * as authApi from '@/api/auth'
vi.stubGlobal('logService', { info: vi.fn(), warn: vi.fn(), error: vi.fn(), debug: vi.fn() })

let wrapper: VueWrapper | undefined
afterEach(() => {
  wrapper?.unmount()
  document.body.innerHTML = ''
})

async function submit(user = '', pass = '') {
  wrapper = mount(withTooltips(LoginModal, { open: true }), {
    attachTo: document.body,
    global: { plugins: [createPinia()], stubs: { ForgotPasswordModal: true } }
  })
  await flushPromises()
  // DialogContent teleports to body, outside the wrapper
  const q = (sel: string) => new DOMWrapper(document.querySelector(sel)!)
  await q('input[name="username"]').setValue(user)
  await q('input[name="password"]').setValue(pass)
  await q('form').trigger('submit')
  // vee-validate validates asynchronously before calling the submit handler
  await new Promise(resolve => setTimeout(resolve, 10))
  await flushPromises()
}

describe('LoginModal', () => {
  it('links field errors to their inputs', async () => {
    await submit()
    for (const name of ['username', 'password']) expectLinkedError(document, name)
    expect(authApi.login).not.toHaveBeenCalled()
  })

  it('moves focus to the first invalid field (#327)', async () => {
    await submit('admin')
    expect(document.activeElement?.getAttribute('name')).toBe('password')
  })

  it('announces a failed sign-in', async () => {
    vi.mocked(authApi.login).mockRejectedValueOnce({
      response: { status: 401, data: { detail: 'Incorrect username/email or password' } }
    })
    await submit('admin', 'wrong')
    expect(document.querySelector('[role="alert"]')?.textContent?.trim()).toBe(
      'Incorrect username/email or password'
    )
  })
})
