import { describe, it, expect, vi } from 'vitest'
import { flushPromises, mount } from '@vue/test-utils'
import { createPinia } from 'pinia'
import { createRouter, createMemoryHistory } from 'vue-router'
import Login from '@/views/Login.vue'

vi.mock('vue-sonner', () => ({ toast: { success: vi.fn(), error: vi.fn() } }))
import { toast } from 'vue-sonner'

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
  mount(Login, { global: { plugins: [router, createPinia()] } })
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
})
