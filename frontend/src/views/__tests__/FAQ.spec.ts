import { describe, it, expect, vi } from 'vitest'
import { mount } from '@vue/test-utils'
import { TIER_CONFIG } from '@/utils/evidenceTiers'
import { useJsonLd } from '@/composables/useJsonLd'
import FAQ from '@/views/FAQ.vue'

vi.mock('@/composables/useSeoMeta', () => ({ useSeoMeta: vi.fn() }))
vi.mock('@/composables/useJsonLd', () => ({
  useJsonLd: vi.fn(),
  getBreadcrumbSchema: vi.fn()
}))

describe('FAQ evidence tiers (#314)', () => {
  it('states the backend evidence tiers in the FAQPage JSON-LD, not score-range labels', () => {
    mount(FAQ, { global: { stubs: { RouterLink: true } } })
    const faqPage = vi
      .mocked(useJsonLd)
      .mock.calls.map(([schema]) => schema as { '@type'?: string; mainEntity?: unknown[] })
      .find(schema => schema['@type'] === 'FAQPage')
    const text = JSON.stringify(faqPage)
    for (const tier of Object.values(TIER_CONFIG)) expect(text).toContain(`\\"${tier.label}\\"`)
    expect(text).not.toContain('Exceptional')
    expect(text).not.toContain('Very Strong')
  })
})

describe('FAQ heading order (#322)', () => {
  it('renders the question headers as h2 directly under the h1', () => {
    const wrapper = mount(FAQ, { global: { stubs: { RouterLink: true } } })
    const levels = wrapper.findAll('h1, h2, h3, h4, h5, h6').map(h => h.element.tagName)
    expect(levels[0]).toBe('H1')
    expect(levels.slice(1).length).toBeGreaterThan(0)
    expect(new Set(levels.slice(1))).toEqual(new Set(['H2']))
  })
})

describe('FAQ syndromic rule (#255)', () => {
  it('states the 30% extra-renal HPO threshold', () => {
    const text = mount(FAQ, { global: { stubs: { RouterLink: true } } }).text()
    expect(text).toContain('When is a gene called syndromic?')
    expect(text).toContain('If at least 30% of its terms are extra-renal')
  })
})

describe('FAQ clinical groups (#338)', () => {
  it('defines the frequency x information content method and the HPO release', () => {
    const text = mount(FAQ, { global: { stubs: { RouterLink: true } } }).text()
    expect(text).toContain('How is the clinical group assigned?')
    expect(text).toContain('information content')
    expect(text).toContain("at least 40% of the primary group's evidence")
    expect(text).toContain('2026-09-01')
  })
})
