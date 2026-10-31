/**
 * Chart colours follow the design tokens: classifications on the strength ramp by meaning
 * (not by index), source series in the fixed utils/sources.ts order with display names, and
 * a failed overlap load shows an error with Retry instead of a blank card.
 */
import { describe, it, expect, vi, beforeEach } from 'vitest'

vi.mock('vue-router', () => import('@/test/routerStub'))
import { mount, flushPromises } from '@vue/test-utils'

vi.stubGlobal(
  'ResizeObserver',
  class {
    observe() {}
    unobserve() {}
    disconnect() {}
  }
)
vi.stubGlobal('logService', { info: vi.fn(), error: vi.fn(), warn: vi.fn() })

vi.mock('@/api/statistics', () => ({
  statisticsApi: {
    getSourceDistributions: vi.fn(),
    getEvidenceComposition: vi.fn(),
    getSourceOverlaps: vi.fn()
  }
}))
import { statisticsApi } from '@/api/statistics'
import D3BarChart from '../D3BarChart.vue'
import SourceDistributionsChart from '../SourceDistributionsChart.vue'
import UpSetChart from '../UpSetChart.vue'

const api = vi.mocked(statisticsApi)

describe('chart colours', () => {
  beforeEach(() => vi.clearAllMocks())

  it('colours ClinGen classifications by strength, strongest first', async () => {
    api.getSourceDistributions.mockResolvedValue({
      data: {
        ClinGen: {
          metadata: { total_genes: 4, visualization_type: 'classification_donut' },
          distribution: [
            { category: 'Limited', gene_count: 1 },
            { category: 'Disputed', gene_count: 1 },
            { category: 'Definitive', gene_count: 2 }
          ]
        }
      }
    } as never)
    const w = mount(SourceDistributionsChart)
    await flushPromises()
    // Multi-label classifications are bars (not a parts-of-a-whole donut)
    const bars = w.findComponent(D3BarChart).props('data') as { category: string; color: string }[]
    expect(bars.map(b => b.category)).toEqual(['Definitive', 'Limited', 'Disputed'])
    expect(bars.map(b => b.color)).toEqual([
      'var(--strength-5)',
      'var(--strength-2)',
      'var(--warning)'
    ])
  })

  it('shows a retryable error when the overlap sources fail to load', async () => {
    api.getSourceOverlaps.mockRejectedValue(new Error('Network Error'))
    const w = mount(UpSetChart)
    await flushPromises()
    expect(w.find('[role="alert"]').text()).toContain('Could not load source overlaps')
    const retry = w.findAll('button').find(b => b.text() === 'Retry')
    expect(retry).toBeDefined()
    await retry!.trigger('click')
    await flushPromises()
    expect(api.getSourceOverlaps.mock.calls.length).toBeGreaterThan(2)
  })
})
