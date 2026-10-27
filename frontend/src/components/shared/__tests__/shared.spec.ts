import { describe, it, expect } from 'vitest'
import { mount } from '@vue/test-utils'
import { h, type Component } from 'vue'
import { TooltipProvider } from '@/components/ui/tooltip'
import {
  Chip,
  DataState,
  OntologyTerm,
  OntologyTermList,
  PageHeader,
  SourceLabel,
  StatusBadge
} from '@/components/shared'

// Tooltips need the provider that App.vue supplies
function render(component: Component, props: Record<string, unknown> = {}, slots = {}) {
  return mount({ render: () => h(TooltipProvider, () => h(component, props, slots)) })
}

describe('Chip', () => {
  it('renders a tier as a strength chip with its icon, tint and a focusable tooltip trigger', () => {
    const el = render(Chip, { tier: 'comprehensive_support' }).find('[data-slot="chip"]')
    expect(el.element.tagName).toBe('SPAN')
    expect(el.text()).toBe('Comprehensive Support')
    expect(el.find('svg').exists()).toBe(true)
    expect(el.attributes('style')).toContain('var(--strength-5)')
    expect(el.attributes('tabindex')).toBe('0')
  })

  it('maps classifications to strength steps and Refuted to the danger tone', () => {
    const definitive = render(Chip, { classification: 'Definitive' }).find('[data-slot="chip"]')
    expect(definitive.attributes('style')).toContain('var(--strength-5)')
    const refuted = render(Chip, { classification: 'Refuted' }).find('[data-slot="chip"]')
    expect(refuted.classes()).toContain('text-danger')
    expect(refuted.attributes('style')).toBeUndefined()
  })

  it('is a button only when clickable', async () => {
    let clicks = 0
    const el = render(Chip, { label: 'PanelApp', onClick: () => clicks++ }).find(
      '[data-slot="chip"]'
    )
    expect(el.element.tagName).toBe('BUTTON')
    expect(el.attributes('type')).toBe('button')
    await el.trigger('click')
    expect(clicks).toBe(1)
    const plain = render(Chip, { label: '12 panels' }).find('[data-slot="chip"]')
    expect(plain.element.tagName).toBe('SPAN')
    expect(plain.attributes('tabindex')).toBeUndefined()
    expect(plain.classes()).toContain('bg-muted')
  })
})

describe('StatusBadge', () => {
  it.each([
    ['failed', 'text-danger', 'Failed'],
    ['COMPLETED', 'text-success', 'Completed'],
    ['running', 'text-info', 'Running'],
    ['draft', 'text-muted-foreground', 'Draft']
  ])('%s uses one tone and label', (status, cls, label) => {
    const el = render(StatusBadge, { status }).find('[data-slot="chip"]')
    expect(el.classes()).toContain(cls)
    expect(el.text()).toBe(label)
    expect(el.find('svg').exists()).toBe(true)
  })
})

describe('OntologyTerm', () => {
  it('renders name first, then the ID in mono, linked to the source', () => {
    const a = render(OntologyTerm, { id: 'HP:0000112', name: 'Nephropathy' }).find('a')
    expect(a.attributes('href')).toBe('https://hpo.jax.org/browse/term/HP:0000112')
    expect(a.attributes('target')).toBe('_blank')
    expect(a.attributes('rel')).toContain('noopener')
    const spans = a.findAll('span')
    expect(spans[0]!.text()).toBe('Nephropathy')
    expect(spans[1]!.text()).toBe('HP:0000112')
    expect(spans[1]!.classes()).toContain('font-mono')
  })

  it('shows the ID alone when the name is missing and stays focusable without a link', () => {
    const el = render(OntologyTerm, { id: 'LOCAL-1' }).find('[data-slot="ontology-term"]')
    expect(el.element.tagName).toBe('SPAN')
    expect(el.attributes('tabindex')).toBe('0')
    expect(el.text()).toBe('LOCAL-1')
  })
})

describe('OntologyTermList', () => {
  const terms = [
    { id: 'HP:0000003', name: 'Multicystic kidney dysplasia' },
    { id: 'HP:0000107' },
    { id: 'HP:0000112', name: 'Nephropathy' },
    { id: 'HP:0000107', name: 'Renal cyst' },
    { id: 'HP:0000112', name: 'Nephropathy' }
  ]

  it('dedupes by ID (keeping the named entry) and sorts by name', () => {
    const items = render(OntologyTermList, { terms }).findAll('li')
    expect(items.map(li => li.find('span').text())).toEqual([
      'Multicystic kidney dysplasia',
      'Nephropathy',
      'Renal cyst'
    ])
  })

  it('caps at max with a show-all toggle', async () => {
    const wrapper = render(OntologyTermList, { terms, max: 2 })
    expect(wrapper.findAll('li')).toHaveLength(2)
    const button = wrapper.find('button')
    expect(button.text()).toBe('Show all 3 (1 more)')
    expect(button.attributes('aria-expanded')).toBe('false')
    await button.trigger('click')
    expect(wrapper.findAll('li')).toHaveLength(3)
    expect(wrapper.find('button').text()).toBe('Show fewer')
  })
})

describe('DataState', () => {
  const slots = { default: () => 'CONTENT' }

  it('never renders empty for an error, and emits retry', async () => {
    const wrapper = mount(DataState, {
      props: { error: new Error('Network Error'), empty: true },
      slots
    })
    expect(wrapper.attributes('data-state')).toBe('error')
    expect(wrapper.attributes('role')).toBe('alert')
    expect(wrapper.text()).toContain('Network Error')
    await wrapper.find('button').trigger('click')
    expect(wrapper.emitted('retry')).toHaveLength(1)
  })

  it.each([
    [{ loading: true, error: 'x' }, 'loading'],
    [{ empty: true, emptyMessage: 'No releases published yet.' }, 'empty']
  ])('%o renders %s', (props, state) => {
    const wrapper = mount(DataState, { props, slots })
    expect(wrapper.attributes('data-state')).toBe(state)
    expect(wrapper.text()).not.toContain('CONTENT')
  })

  it('renders the content otherwise', () => {
    expect(mount(DataState, { slots }).text()).toBe('CONTENT')
  })
})

describe('PageHeader', () => {
  it('renders one h1, the description and the slots', () => {
    const wrapper = mount(PageHeader, {
      props: { title: 'Genes', description: 'Browse kidney genes.' },
      slots: { breadcrumb: () => 'CRUMBS', actions: () => 'ACTIONS' }
    })
    expect(wrapper.findAll('h1')).toHaveLength(1)
    expect(wrapper.find('h1').text()).toBe('Genes')
    expect(wrapper.text()).toContain('Browse kidney genes.')
    expect(wrapper.text()).toContain('CRUMBS')
    expect(wrapper.text()).toContain('ACTIONS')
  })
})

describe('SourceLabel', () => {
  it('shows the display name with the chart-colour dot', () => {
    const el = render(SourceLabel, { source: 'DiagnosticPanels' }).find(
      '[data-slot="source-label"]'
    )
    expect(el.text()).toBe('Diagnostic panels')
    expect(el.find('[aria-hidden="true"]').attributes('style')).toContain('var(--source-6)')
    expect(el.attributes('tabindex')).toBe('0')
  })
})
