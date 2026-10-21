import { describe, it, expect, vi } from 'vitest'
import { mount } from '@vue/test-utils'
import About from '@/views/About.vue'
import { TIER_CONFIG } from '@/utils/evidenceTiers'

vi.mock('@/composables/useSeoMeta', () => ({ useSeoMeta: vi.fn() }))
vi.mock('@/composables/useJsonLd', () => ({
  useJsonLd: vi.fn(),
  getBreadcrumbSchema: vi.fn()
}))

describe('About tier table (#314)', () => {
  it('renders one row per backend evidence tier, in order', () => {
    const wrapper = mount(About, { global: { stubs: { RouterLink: true } } })
    const rows = wrapper.findAll('[data-testid="tier-row"]')
    expect(rows.map(r => r.find('span').text())).toEqual(
      Object.values(TIER_CONFIG).map(t => t.label)
    )
    expect(rows[0]?.text()).toContain('score ≥50%')
  })
})

describe('About core concepts (#329)', () => {
  it('describes the science, not the server architecture', () => {
    const text = mount(About, { global: { stubs: { RouterLink: true } } }).text()
    expect(text).not.toContain('High-Performance Architecture')
    expect(text).not.toContain('Real-Time Progress Tracking')
    expect(text).not.toContain('ThreadPoolExecutor')
  })
})
