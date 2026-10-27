/** A table wider than its container fades the edge with hidden columns (#423). */

import { describe, it, expect } from 'vitest'
import { mount } from '@vue/test-utils'
import { nextTick } from 'vue'
import { Table } from '@/components/ui/table'

const setSize = (el: HTMLElement, scrollWidth: number, scrollLeft = 0) => {
  Object.defineProperty(el, 'clientWidth', { value: 390, configurable: true })
  Object.defineProperty(el, 'scrollWidth', { value: scrollWidth, configurable: true })
  el.scrollLeft = scrollLeft
}

describe('Table scroll cue', () => {
  it('fades the right edge, then both, then none as the overflow changes', async () => {
    const wrapper = mount(Table)
    const el = wrapper.get('[data-slot="table-container"]').element as HTMLElement
    const mask = () => el.style.maskImage

    setSize(el, 390)
    el.dispatchEvent(new Event('scroll'))
    await nextTick()
    expect(mask()).toBe('')

    setSize(el, 900)
    el.dispatchEvent(new Event('scroll'))
    await nextTick()
    expect(mask()).toMatch(/^linear-gradient\(to right, black, .*transparent\)$/)

    setSize(el, 900, 200)
    el.dispatchEvent(new Event('scroll'))
    await nextTick()
    expect(mask()).toMatch(/^linear-gradient\(to right, transparent, .*transparent\)$/)
  })
})
