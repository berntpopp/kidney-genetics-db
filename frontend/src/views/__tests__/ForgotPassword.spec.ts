/**
 * The reset-password page announces errors like the Login page (#327).
 */

import { describe, it, expect, vi, afterEach } from 'vitest'
import { flushPromises, mount, type VueWrapper } from '@vue/test-utils'
import { createPinia } from 'pinia'
import { createRouter, createMemoryHistory } from 'vue-router'
import ForgotPassword from '@/views/ForgotPassword.vue'

vi.mock('@/api/auth', () => ({ requestPasswordReset: vi.fn() }))
import * as authApi from '@/api/auth'
vi.stubGlobal('logService', { info: vi.fn(), warn: vi.fn(), error: vi.fn(), debug: vi.fn() })
vi.stubGlobal(
  'matchMedia',
  vi.fn(() => ({ matches: false, addEventListener: vi.fn(), removeEventListener: vi.fn() }))
)

let wrapper: VueWrapper | undefined
afterEach(() => wrapper?.unmount())

async function submit(email = '') {
  const router = createRouter({
    history: createMemoryHistory(),
    routes: [{ path: '/:rest(.*)', component: { render: () => null } }]
  })
  wrapper = mount(ForgotPassword, {
    global: { plugins: [router, createPinia()] },
    attachTo: document.body
  })
  await flushPromises()
  await wrapper.find('#page-forgot-email').setValue(email)
  ;(wrapper.find('button[type="submit"]').element as HTMLElement).focus()
  await wrapper.find('form').trigger('submit')
  // vee-validate validates asynchronously before calling the submit handler
  await new Promise(resolve => setTimeout(resolve, 10))
  await flushPromises()
  return wrapper
}

describe('ForgotPassword', () => {
  it('links the error and focuses the email field on an invalid submit (#327)', async () => {
    const w = await submit('not-an-email')
    const input = w.find('#page-forgot-email')
    expect(input.attributes('aria-invalid')).toBe('true')
    expect(input.attributes('aria-describedby')).toBe('page-forgot-email-error')
    expect(w.find('#page-forgot-email-error').text()).not.toBe('')
    expect(document.activeElement?.id).toBe('page-forgot-email')
    expect(authApi.requestPasswordReset).not.toHaveBeenCalled()
  })

  it('announces a failed request (#327)', async () => {
    vi.mocked(authApi.requestPasswordReset).mockRejectedValueOnce({
      response: { status: 500, data: { detail: 'Server error' } }
    })
    const w = await submit('user@example.org')
    expect(w.find('[role="alert"]').text()).toBe('Server error')
    expect(w.find('#page-forgot-email').attributes('aria-invalid')).toBe('false')
  })
})
