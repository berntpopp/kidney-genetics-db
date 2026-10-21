import { describe, it, expect, vi } from 'vitest'
import { mount } from '@vue/test-utils'
import About from '@/views/About.vue'
import { SCORE_RANGES } from '@/utils/evidenceTiers'

vi.mock('@/composables/useSeoMeta', () => ({ useSeoMeta: vi.fn() }))
vi.mock('@/composables/useJsonLd', () => ({
  useJsonLd: vi.fn(),
  getBreadcrumbSchema: vi.fn()
}))

describe('About score table (#314)', () => {
  it('renders one row per SCORE_RANGES entry, in order', () => {
    const wrapper = mount(About, { global: { stubs: { RouterLink: true } } })
    const rows = wrapper.findAll('[data-testid="score-range-row"]')
    expect(rows.map(r => r.find('span').text())).toEqual(SCORE_RANGES.map(r => r.label))
    expect(rows[0]?.text()).toContain('≥ 95')
    expect(rows.at(-1)?.text()).toContain('< 10')
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
