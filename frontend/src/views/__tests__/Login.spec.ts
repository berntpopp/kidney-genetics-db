import { describe, it, expect, vi } from 'vitest'
import { flushPromises, mount } from '@vue/test-utils'
import { createPinia } from 'pinia'
import { createRouter, createMemoryHistory } from 'vue-router'
import Login from '@/views/Login.vue'
import { expectLinkedError, field, withTooltips } from '@/components/auth/__tests__/formTestUtils'

vi.mock('vue-sonner', () => ({ toast: { success: vi.fn(), error: vi.fn() } }))
import { toast } from 'vue-sonner'
vi.mock('@/api/auth', () => ({ login: vi.fn() }))
import * as authApi from '@/api/auth'
vi.stubGlobal('logService', { info: vi.fn(), warn: vi.fn(), error: vi.fn(), debug: vi.fn() })

vi.stubGlobal(
  'matchMedia',
  vi.fn(() => ({ matches: false, addEventListener: vi.fn(), removeEventListener: vi.fn() }))
)

async function mountAt(path: string, attach = false) {
  const router = createRouter({
    history: createMemoryHistory(),
    routes: [
      { path: '/login', component: Login },
      { path: '/:rest(.*)', component: { render: () => null } }
    ]
  })
  await router.push(path)
  const wrapper = mount(withTooltips(Login), {
    global: { plugins: [router, createPinia()] },
    attachTo: attach ? document.body : undefined
  })
  await flushPromises()
  return wrapper
}

async function submit(wrapper: Awaited<ReturnType<typeof mountAt>>, user = '', pass = '') {
  await wrapper.find('input[name="username"]').setValue(user)
  await wrapper.find('input[name="password"]').setValue(pass)
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

    for (const name of ['username', 'password']) expectLinkedError(wrapper.element, name)
    // Empty submit shows the schema messages, not vee-validate's generic "Required"
    expect(wrapper.text()).toContain('Username or email is required')
    expect(wrapper.text()).toContain('Password is required')
    expect(authApi.login).not.toHaveBeenCalled()
  })

  it('moves focus to the first invalid field on submit (#327)', async () => {
    const wrapper = await mountAt('/login', true)
    ;(wrapper.find('button[type="submit"]').element as HTMLElement).focus()
    await submit(wrapper)
    expect(document.activeElement?.getAttribute('name')).toBe('username')

    await submit(wrapper, 'admin')
    expect(document.activeElement?.getAttribute('name')).toBe('password')
    wrapper.unmount()
  })

  it('offers no no-op "Remember me" option', async () => {
    const wrapper = await mountAt('/login')
    expect(wrapper.text()).not.toContain('Remember me')
    expect(wrapper.find('input[type="checkbox"]').exists()).toBe(false)
  })

  it('submits once when Enter is pressed in the password field', async () => {
    vi.mocked(authApi.login).mockClear()
    vi.mocked(authApi.login).mockRejectedValueOnce(new Error('Network Error'))
    const wrapper = await mountAt('/login')
    await wrapper.find('input[name="username"]').setValue('admin')
    const pass = wrapper.find('input[name="password"]')
    await pass.setValue('secret')
    await pass.trigger('keyup', { key: 'Enter' })
    await wrapper.find('form').trigger('submit')
    await new Promise(resolve => setTimeout(resolve, 10))
    await flushPromises()
    expect(authApi.login).toHaveBeenCalledTimes(1)
  })

  it('announces bad credentials with the API message (#327)', async () => {
    vi.mocked(authApi.login).mockRejectedValueOnce({
      response: { status: 401, data: { detail: 'Incorrect username/email or password' } }
    })
    const wrapper = await mountAt('/login')
    await submit(wrapper, 'admin', 'wrong')

    const alert = wrapper.find('[role="alert"]')
    expect(alert.text()).toBe('Incorrect username/email or password')
    expect(field(wrapper.element, 'username').getAttribute('aria-invalid')).toBe('false')
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
