/**
 * Chart colours follow the design tokens: classifications on the strength ramp by meaning
 * (not by index), source series in the fixed utils/sources.ts order with display names, and
 * a failed overlap load shows an error with Retry instead of a blank card.
 */
import { describe, it, expect, vi, beforeEach } from 'vitest'
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
import SourceDistributionsChart from '../SourceDistributionsChart.vue'
import EvidenceCompositionChart from '../EvidenceCompositionChart.vue'
import UpSetChart from '../UpSetChart.vue'

const api = vi.mocked(statisticsApi)
const legend = (w: ReturnType<typeof mount>) =>
  w.findAll('[data-testid="donut-legend"] li').map(li => ({
    text: li.text(),
    style: li.find('span').attributes('style') ?? ''
  }))

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
    const items = legend(w)
    expect(items.map(i => i.text.split(/\d/)[0])).toEqual(['Definitive', 'Limited', 'Disputed'])
    expect(items[0]!.style).toContain('var(--strength-5)')
    expect(items[1]!.style).toContain('var(--strength-2)')
    expect(items[2]!.style).toContain('var(--warning)')
  })

  it('shows source weights with display names in the fixed source order', async () => {
    api.getEvidenceComposition.mockResolvedValue({
      data: {
        evidence_tier_distribution: [],
        source_contribution_weights: { PubTator: 0.5, DiagnosticPanels: 0.3, ClinGen: 0.2 }
      }
    } as never)
    const w = mount(EvidenceCompositionChart)
    await flushPromises()
    await w
      .findAll('button')
      .find(b => b.text() === 'Weights')!
      .trigger('click')
    const items = legend(w)
    expect(items.map(i => i.text)).toEqual([
      'ClinGen20.0%',
      'Diagnostic panels30.0%',
      'PubTator350.0%'
    ])
    expect(items[0]!.style).toContain('var(--source-1)')
    expect(items[2]!.style).toContain('var(--source-7)')
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
