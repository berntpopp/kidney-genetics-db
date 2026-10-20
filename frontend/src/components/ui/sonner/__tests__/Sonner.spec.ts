import { describe, it, expect, afterEach } from 'vitest'
import { mount } from '@vue/test-utils'
import { Toaster } from '..'

describe('Toaster theme', () => {
  afterEach(() => localStorage.clear())

  it.each(['dark', 'light'])('follows the stored app theme (%s)', async mode => {
    localStorage.setItem('kgdb-color-mode', mode)
    const wrapper = mount(Toaster, { attachTo: document.body })
    await wrapper.vm.$nextTick()
    expect(document.querySelector('[data-sonner-theme]')?.getAttribute('data-sonner-theme')).toBe(
      mode
    )
    wrapper.unmount()
  })
})
