import { describe, it, expect, vi } from 'vitest'
import { mount } from '@vue/test-utils'
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
    expect(rows[0]?.find('dd').text()).toBe('Score ≥ 50 with evidence from at least 4 sources')
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
