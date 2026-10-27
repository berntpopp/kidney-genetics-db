/**
 * An invalid submit moves focus to the email field so its error is announced (#327).
 */

import { describe, it, expect, vi, afterEach } from 'vitest'
import { DOMWrapper, flushPromises, mount, type VueWrapper } from '@vue/test-utils'
import { createPinia } from 'pinia'
import ForgotPasswordModal from '@/components/auth/ForgotPasswordModal.vue'
import { expectLinkedError } from './formTestUtils'

vi.mock('@/api/auth', () => ({ requestPasswordReset: vi.fn() }))
import * as authApi from '@/api/auth'
vi.stubGlobal('logService', { info: vi.fn(), warn: vi.fn(), error: vi.fn(), debug: vi.fn() })

let wrapper: VueWrapper | undefined
afterEach(() => {
  wrapper?.unmount()
  document.body.innerHTML = ''
})

async function submit(email = '') {
  wrapper = mount(ForgotPasswordModal, {
    props: { open: true },
    attachTo: document.body,
    global: { plugins: [createPinia()] }
  })
  await flushPromises()
  // DialogContent teleports to body, outside the wrapper
  const q = (sel: string) => new DOMWrapper(document.querySelector(sel)!)
  await q('input[name="email"]').setValue(email)
  ;(document.querySelector('button[type="submit"]') as HTMLElement).focus()
  await q('form').trigger('submit')
  // vee-validate validates asynchronously before calling the submit handler
  await new Promise(resolve => setTimeout(resolve, 10))
  await flushPromises()
}

describe('ForgotPasswordModal', () => {
  it.each(['', 'not-an-email'])(
    'links the error and focuses the email field for %j (#327)',
    async email => {
      await submit(email)
      expectLinkedError(document, 'email')
      expect(document.activeElement?.getAttribute('name')).toBe('email')
      expect(authApi.requestPasswordReset).not.toHaveBeenCalled()
    }
  )

  it('announces a failed request without moving focus (#327)', async () => {
    vi.mocked(authApi.requestPasswordReset).mockRejectedValueOnce({
      response: { status: 500, data: { detail: 'Server error' } }
    })
    await submit('user@example.org')
    expect(authApi.requestPasswordReset).toHaveBeenCalled()
    expect(document.activeElement?.getAttribute('type')).toBe('submit')
    expect(document.querySelector('[role="alert"]')?.textContent?.trim()).toBe('Server error')
  })
})
