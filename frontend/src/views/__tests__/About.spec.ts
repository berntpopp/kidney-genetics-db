import { describe, it, expect, vi } from 'vitest'
import { toValue } from 'vue'
import { mount } from '@vue/test-utils'
import { useJsonLd } from '@/composables/useJsonLd'
import About from '@/views/About.vue'
import { TIER_CONFIG } from '@/utils/evidenceTiers'
import { withTooltips } from '@/components/auth/__tests__/formTestUtils'

vi.mock('@/composables/useSeoMeta', () => ({ useSeoMeta: vi.fn() }))
vi.mock('@/composables/useJsonLd', () => ({
  useJsonLd: vi.fn(),
  getBreadcrumbSchema: vi.fn()
}))

const mountAbout = () => mount(withTooltips(About), { global: { stubs: { RouterLink: true } } })

describe('About tier table (#314)', () => {
  it('renders one row per backend evidence tier, in order, on the 0–100 scale', () => {
    const rows = mountAbout().findAll('[data-testid="tier-row"]')
    expect(rows.map(r => r.find('dt').text())).toEqual(Object.values(TIER_CONFIG).map(t => t.label))
    expect(rows[0]?.find('dd').text()).toBe(
      'Score ≥ 50 with a curated assertion and evidence from at least 4 sources'
    )
    for (const row of rows) expect(row.text()).not.toContain('%')
  })
})

describe('About core concepts (#329)', () => {
  it('describes the science, not the server architecture', () => {
    const text = mountAbout().text()
    expect(text).not.toContain('High-Performance Architecture')
    expect(text).not.toContain('Real-Time Progress Tracking')
    expect(text).not.toContain('ThreadPoolExecutor')
    expect(text).not.toContain('circuit breaker')
    expect(text).toContain('How the evidence score works')
    expect(text).toContain('How to cite')
  })

  it('links to the real repository and documentation', () => {
    const hrefs = mountAbout()
      .findAll('a')
      .map(a => a.attributes('href'))
    expect(hrefs).toContain('https://github.com/berntpopp/kidney-genetics-db')
    expect(hrefs).toContain('https://doi.org/10.5281/zenodo.19316248')
    expect(hrefs.some(h => h?.includes('bernt-popp'))).toBe(false)
    expect(hrefs.some(h => h?.endsWith('/tree/main/docs'))).toBe(false)
  })
})

describe('About questions (merged FAQ)', () => {
  it('renders the questions as visible h3 headings under one h2, not an accordion', () => {
    const wrapper = mountAbout()
    const section = wrapper.get('section#faq')
    expect(section.get('h2').text()).toBe('Questions')
    expect(section.findAll('h3').length).toBeGreaterThan(0)
    expect(section.find('[data-slot="accordion-trigger"]').exists()).toBe(false)
    expect(wrapper.find('nav[aria-label="On this page"] a[href="#faq"]').exists()).toBe(true)
  })

  it('states the syndromic rule (#255) and clinical group method (#338)', () => {
    const text = mountAbout().text()
    expect(text).toContain('When is a gene called syndromic?')
    expect(text).toContain('If at least 30% of its terms are extra-renal')
    expect(text).toContain('How is the clinical group assigned?')
    expect(text).toContain('information content')
    expect(text).toContain("at least half of the primary group's evidence")
    expect(text).toContain('2026-09-01')
  })

  it('states no hard-coded gene or source count and does not claim continuous updates', () => {
    const text = mountAbout().text()
    expect(text).not.toMatch(/\b\d{1,3}(,\d{3})+ genes\b|\b\d+ (authoritative )?sources\b/)
    expect(text).not.toMatch(/updated continuously/i)
  })

  it('publishes the questions as FAQPage JSON-LD', () => {
    vi.mocked(useJsonLd).mockClear()
    mountAbout()
    const faqPage = vi
      .mocked(useJsonLd)
      .mock.calls.map(([schema]) => toValue(schema) as { '@type'?: string; mainEntity?: unknown[] })
      .find(schema => schema?.['@type'] === 'FAQPage')
    expect(faqPage?.mainEntity?.length).toBeGreaterThan(0)
    expect(JSON.stringify(faqPage)).toContain('When is a gene called syndromic?')
  })
})
