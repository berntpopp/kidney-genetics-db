/**
 * The emailed /reset-password?token=... link sets a new password with that token.
 */

import { describe, it, expect, vi, afterEach } from 'vitest'
import { flushPromises, mount, type VueWrapper } from '@vue/test-utils'
import { createPinia } from 'pinia'
import { createRouter, createMemoryHistory } from 'vue-router'
import ResetPassword from '@/views/ResetPassword.vue'
import { TooltipProvider } from '@/components/ui/tooltip'

vi.mock('@/api/auth', () => ({ resetPassword: vi.fn() }))
import * as authApi from '@/api/auth'
vi.stubGlobal('logService', { info: vi.fn(), warn: vi.fn(), error: vi.fn(), debug: vi.fn() })
vi.stubGlobal(
  'matchMedia',
  vi.fn(() => ({ matches: false, addEventListener: vi.fn(), removeEventListener: vi.fn() }))
)

let wrapper: VueWrapper | undefined
afterEach(() => {
  wrapper?.unmount()
  vi.clearAllMocks()
})

async function open(url: string) {
  const router = createRouter({
    history: createMemoryHistory(),
    routes: [{ path: '/:rest(.*)', component: ResetPassword }]
  })
  await router.push(url)
  wrapper = mount(
    {
      components: { TooltipProvider },
      template: '<TooltipProvider><RouterView /></TooltipProvider>'
    },
    { global: { plugins: [router, createPinia()] } }
  )
  await flushPromises()
  return wrapper
}

async function submit(password: string, confirm: string) {
  await wrapper!.find('input[name="password"]').setValue(password)
  await wrapper!.find('input[name="confirm"]').setValue(confirm)
  await wrapper!.find('form').trigger('submit')
  await new Promise(resolve => setTimeout(resolve, 10))
  await flushPromises()
}

describe('ResetPassword', () => {
  it('sends the token from the link with the new password', async () => {
    vi.mocked(authApi.resetPassword).mockResolvedValueOnce({ detail: 'ok' })
    await open('/reset-password?token=tok-123')
    await submit('New-Password-1', 'New-Password-1')

    expect(authApi.resetPassword).toHaveBeenCalledWith('tok-123', 'New-Password-1')
    expect(wrapper!.find('[role="status"]').text()).toContain('password has been changed')
  })

  it('does not submit mismatched passwords', async () => {
    await open('/reset-password?token=tok-123')
    await submit('New-Password-1', 'Other-Password-2')

    expect(authApi.resetPassword).not.toHaveBeenCalled()
    expect(wrapper!.text()).toContain('Passwords do not match')
  })

  it('explains a link without a token instead of showing the form', async () => {
    await open('/reset-password')

    expect(wrapper!.find('form').exists()).toBe(false)
    expect(wrapper!.find('[role="alert"]').text()).toContain('no reset token')
    expect(wrapper!.text()).not.toContain('valid for one hour')
  })

  it('shows an expired or used token error from the API', async () => {
    vi.mocked(authApi.resetPassword).mockRejectedValueOnce({
      response: { data: { error: { detail: 'Invalid or expired reset token' } } }
    })
    await open('/reset-password?token=old')
    await submit('New-Password-1', 'New-Password-1')

    const alert = wrapper!.find('[role="alert"]')
    expect(alert.text()).toContain('Invalid or expired reset token')
    expect(alert.find('a').text()).toBe('Request a new link')
  })
})
