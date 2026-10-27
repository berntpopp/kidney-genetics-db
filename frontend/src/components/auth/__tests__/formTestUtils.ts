import { h, type Component } from 'vue'
import { expect } from 'vitest'
import { TooltipProvider } from '@/components/ui/tooltip'

/** Wrap a component in the TooltipProvider that App.vue provides at runtime */
export const withTooltips = (component: Component, props: Record<string, unknown> = {}) => ({
  render: () => h(TooltipProvider, () => h(component, props))
})

export const field = (root: Pick<Element, 'querySelector'>, name: string) =>
  root.querySelector<HTMLElement>(`input[name="${name}"]`)!

/** The field is invalid and aria-describedby points at its non-empty FormMessage (#327) */
export function expectLinkedError(root: Pick<Element, 'querySelector'>, name: string) {
  const input = field(root, name)
  expect(input.getAttribute('aria-invalid')).toBe('true')
  const message = (input.getAttribute('aria-describedby') ?? '')
    .split(' ')
    .map(id => root.querySelector(`[id="${id}"]`))
    .find(el => el?.getAttribute('data-slot') === 'form-message')
  expect(message?.textContent?.trim()).toBeTruthy()
}
