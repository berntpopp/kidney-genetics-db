import { describe, it, expect, vi } from 'vitest'
import { flushPromises, mount } from '@vue/test-utils'
import { createPinia } from 'pinia'
import { createRouter, createMemoryHistory } from 'vue-router'
import Login from '@/views/Login.vue'

vi.mock('vue-sonner', () => ({ toast: { success: vi.fn(), error: vi.fn() } }))
import { toast } from 'vue-sonner'
vi.mock('@/api/auth', () => ({ login: vi.fn() }))
import * as authApi from '@/api/auth'
vi.stubGlobal('logService', { info: vi.fn(), warn: vi.fn(), error: vi.fn(), debug: vi.fn() })

vi.stubGlobal(
  'matchMedia',
  vi.fn(() => ({ matches: false, addEventListener: vi.fn(), removeEventListener: vi.fn() }))
)

async function mountAt(path: string) {
  const router = createRouter({
    history: createMemoryHistory(),
    routes: [
      { path: '/login', component: Login },
      { path: '/:rest(.*)', component: { render: () => null } }
    ]
  })
  await router.push(path)
  const wrapper = mount(Login, { global: { plugins: [router, createPinia()] } })
  await flushPromises()
  return wrapper
}

async function submit(wrapper: Awaited<ReturnType<typeof mountAt>>, user = '', pass = '') {
  await wrapper.find('#page-login-username').setValue(user)
  await wrapper.find('#page-login-password').setValue(pass)
  await wrapper.find('form').trigger('submit')
  // vee-validate validates asynchronously before calling the submit handler
  await new Promise(resolve => setTimeout(resolve, 10))
  await flushPromises()
}

describe('Login', () => {
  it('tells the user to sign in again after a password change (#290)', async () => {
    await mountAt('/login?reason=password_changed')
    expect(toast.success).toHaveBeenCalledWith('Password changed. Please sign in again.', {
      duration: 5000
    })
  })

  it('shows no message on a normal visit', async () => {
    vi.mocked(toast.success).mockClear()
    await mountAt('/login')
    expect(toast.success).not.toHaveBeenCalled()
  })

  it('links field errors to their inputs (#327)', async () => {
    const wrapper = await mountAt('/login')
    await submit(wrapper)

    for (const field of ['username', 'password']) {
      const input = wrapper.find(`#page-login-${field}`)
      const errorId = `page-login-${field}-error`
      expect(input.attributes('aria-invalid')).toBe('true')
      expect(input.attributes('aria-describedby')).toBe(errorId)
      expect(wrapper.find(`#${errorId}`).text()).not.toBe('')
    }
    expect(authApi.login).not.toHaveBeenCalled()
  })

  it('announces bad credentials with the API message (#327)', async () => {
    vi.mocked(authApi.login).mockRejectedValueOnce({
      response: { status: 401, data: { detail: 'Incorrect username/email or password' } }
    })
    const wrapper = await mountAt('/login')
    await submit(wrapper, 'admin', 'wrong')

    const alert = wrapper.find('[role="alert"]')
    expect(alert.text()).toBe('Incorrect username/email or password')
    expect(wrapper.find('#page-login-username').attributes('aria-invalid')).toBe('false')
  })

  it('announces an unreachable server distinctly (#327)', async () => {
    vi.mocked(authApi.login).mockRejectedValueOnce(new Error('Network Error'))
    const wrapper = await mountAt('/login')
    await submit(wrapper, 'admin', 'secret')

    expect(wrapper.find('[role="alert"]').text()).toContain('Could not reach the sign-in service')
  })

  it('does not blame the network for a 429 without detail (#327)', async () => {
    vi.mocked(authApi.login).mockRejectedValueOnce({
      response: { status: 429, data: { error: 'Rate limit exceeded' } }
    })
    const wrapper = await mountAt('/login')
    await submit(wrapper, 'admin', 'secret')

    const alert = wrapper.find('[role="alert"]')
    expect(alert.exists()).toBe(true)
    expect(alert.text()).not.toContain('Could not reach')
  })
})
