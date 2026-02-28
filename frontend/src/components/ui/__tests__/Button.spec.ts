import { describe, it, expect } from 'vitest'
import { mount } from '@vue/test-utils'
import { Button } from '@/components/ui/button'

describe('Button (smoke test)', () => {
  it('renders with default props', () => {
    const wrapper = mount(Button, {
      slots: { default: 'Click me' }
    })
    expect(wrapper.text()).toContain('Click me')
    expect(wrapper.element.tagName).toBe('BUTTON')
  })

  it('applies variant classes', () => {
    const wrapper = mount(Button, {
      props: { variant: 'destructive' },
      slots: { default: 'Delete' }
    })
    expect(wrapper.text()).toContain('Delete')
    expect(wrapper.element.tagName).toBe('BUTTON')
  })

  it('handles click events', async () => {
    const wrapper = mount(Button, {
      slots: { default: 'Submit' }
    })
    await wrapper.trigger('click')
    expect(wrapper.emitted('click')).toBeTruthy()
  })
})
