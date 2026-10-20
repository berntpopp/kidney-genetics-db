import { describe, it, expect, vi } from 'vitest'
import { mount, flushPromises } from '@vue/test-utils'
import EvidenceCompositionChart from '../EvidenceCompositionChart.vue'

vi.stubGlobal(
  'ResizeObserver',
  class {
    observe() {}
    disconnect() {}
  }
)
vi.stubGlobal('logService', { info: vi.fn(), error: vi.fn(), warn: vi.fn() })

vi.mock('@/api/statistics', () => ({
  statisticsApi: {
    getEvidenceComposition: vi.fn().mockResolvedValue({
      data: {
        evidence_tier_distribution: [
          {
            tier: 'comprehensive_support',
            tier_label: 'Comprehensive Support',
            gene_count: 1,
            color: '#4CAF50'
          }
        ]
      }
    })
  }
}))

describe('EvidenceCompositionChart tiers (#325)', () => {
  it('colors tiers from TIER_CONFIG, not the backend palette', async () => {
    const wrapper = mount(EvidenceCompositionChart)
    await flushPromises()
    const swatch = wrapper.find('[data-testid="donut-legend"] li span')
    // TIER_CONFIG.comprehensive_support.color = #22c55e
    expect(swatch.attributes('style')).toContain('rgb(34, 197, 94)')
  })
})
