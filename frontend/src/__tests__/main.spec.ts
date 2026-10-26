/* eslint-disable vue/one-component-per-file -- tiny stub route components */
/**
 * Client bootstrap tests (#298): direct navigation / reload to protected routes
 * must resolve the auth guard before vite-ssg mounts the app.
 */

import { describe, it, expect, vi, beforeEach } from 'vitest'
import { defineComponent, h } from 'vue'
import { RouterView } from 'vue-router'

vi.mock('@/App.vue', () => ({ default: defineComponent({ render: () => h(RouterView) }) }))

vi.mock('@/router', () => {
  const page = (text: string) => defineComponent({ render: () => h('p', text) })
  return {
    routes: [
      { path: '/', component: page('home') },
      { path: '/login', component: page('login') },
      {
        path: '/admin',
        component: page('admin'),
        meta: { requiresAuth: true, requiresAdmin: true }
      }
    ]
  }
})

vi.mock('@/api/auth', () => ({
  refreshToken: vi.fn(),
  getCurrentUser: vi.fn(),
  logout: vi.fn()
}))

import * as authApi from '@/api/auth'

const admin = { id: 1, username: 'admin', email: 'a@example.org', role: 'admin' }

async function bootAt(path: string) {
  vi.resetModules()
  document.body.innerHTML = '<div id="app"></div>'
  window.history.replaceState(null, '', path)
  await import('@/main')
  await vi.waitFor(() => expect(document.querySelector('#app p')).not.toBeNull(), {
    timeout: 2000
  })
  return { text: document.querySelector('#app p')!.textContent, path: window.location.pathname }
}

// The first test pays the cold import of main.ts, which exceeds 5 s on a loaded runner
describe('client bootstrap auth guard', { timeout: 30000 }, () => {
  beforeEach(() => {
    localStorage.clear()
    vi.mocked(authApi.refreshToken).mockReset()
    vi.mocked(authApi.getCurrentUser).mockReset()
  })

  it('mounts a public route', async () => {
    expect(await bootAt('/')).toEqual({ text: 'home', path: '/' })
  })

  it('redirects an anonymous direct navigation to /admin to login', async () => {
    const result = await bootAt('/admin')
    expect(result).toEqual({ text: 'login', path: '/login' })
    expect(authApi.refreshToken).not.toHaveBeenCalled()
  })

  it('renders /admin on reload for an authenticated admin session', async () => {
    localStorage.setItem('user', JSON.stringify(admin))
    vi.mocked(authApi.refreshToken).mockResolvedValue({ access_token: 'fresh' } as never)
    vi.mocked(authApi.getCurrentUser).mockResolvedValue(admin as never)
    const result = await bootAt('/admin')
    expect(result).toEqual({ text: 'admin', path: '/admin' })
    expect(authApi.refreshToken).toHaveBeenCalledTimes(1)
  })

  it('redirects to login when the stored session can no longer be refreshed', async () => {
    localStorage.setItem('user', JSON.stringify(admin))
    vi.mocked(authApi.refreshToken).mockRejectedValue(new Error('expired'))
    const result = await bootAt('/admin')
    expect(result).toEqual({ text: 'login', path: '/login' })
  })
})
