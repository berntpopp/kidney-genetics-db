import { describe, it, expect, vi } from 'vitest'
import { mount, flushPromises } from '@vue/test-utils'
import SourceDistributionsChart from '../SourceDistributionsChart.vue'

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
    getSourceDistributions: vi.fn().mockResolvedValue({
      data: {
        ClinGen: {
          metadata: {
            total_classifications: 2,
            total_genes: 3,
            visualization_type: 'classification_donut'
          },
          distribution: [
            { category: 'Definitive', gene_count: 2 },
            { category: 'Limited', gene_count: 1 }
          ]
        }
      }
    })
  }
}))

describe('SourceDistributionsChart metadata (#325)', () => {
  it('does not show the internal chart id to users', async () => {
    const wrapper = mount(SourceDistributionsChart)
    await flushPromises()
    expect(wrapper.text()).toContain('Total Genes')
    expect(wrapper.text()).not.toContain('classification_donut')
    expect(wrapper.text()).not.toContain('Visualization Type')
  })
})
