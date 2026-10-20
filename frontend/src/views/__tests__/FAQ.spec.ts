import { describe, it, expect, vi } from 'vitest'
import { mount } from '@vue/test-utils'
import { SCORE_RANGES } from '@/utils/evidenceTiers'
import { useJsonLd } from '@/composables/useJsonLd'
import FAQ from '@/views/FAQ.vue'

vi.mock('@/composables/useSeoMeta', () => ({ useSeoMeta: vi.fn() }))
vi.mock('@/composables/useJsonLd', () => ({
  useJsonLd: vi.fn(),
  getBreadcrumbSchema: vi.fn()
}))

describe('FAQ score bands (#314)', () => {
  it('states the SCORE_RANGES bands in the FAQPage JSON-LD, not the old ones', () => {
    mount(FAQ, { global: { stubs: { RouterLink: true } } })
    const faqPage = vi
      .mocked(useJsonLd)
      .mock.calls.map(([schema]) => schema as { '@type'?: string; mainEntity?: unknown[] })
      .find(schema => schema['@type'] === 'FAQPage')
    const text = JSON.stringify(faqPage)
    for (const range of SCORE_RANGES) expect(text).toContain(`\\"${range.label}\\"`)
    expect(text).toContain('≥ 95 \\"Exceptional\\"')
    expect(text).toContain('< 10 \\"Minimal\\"')
    expect(text).not.toContain('80-94')
    expect(text).not.toContain('Moderate/Limited')
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
