import { describe, it, expect, vi } from 'vitest'
import { mount } from '@vue/test-utils'
import UpSetChart from '../UpSetChart.vue'

// Keep the chart in its loading state: the API never answers
vi.mock('@/api/statistics', () => ({
  statisticsApi: { getSourceOverlaps: vi.fn(() => new Promise(() => {})) }
}))

describe('UpSetChart loading layout (#324)', () => {
  it('renders the gene-count badge invisibly before data arrives', () => {
    const wrapper = mount(UpSetChart)
    const badge = wrapper.find('.invisible')
    expect(badge.exists()).toBe(true)
    expect(badge.text()).toContain('genes')
  })
})

describe('UpSetChart heading level (#322)', () => {
  it('titles the card with an h2 so it follows the dashboard h1', () => {
    const wrapper = mount(UpSetChart)
    expect(wrapper.find('[data-slot="card-title"]').element.tagName).toBe('H2')
  })
})
