import { describe, it, expect, vi } from 'vitest'
import { mount } from '@vue/test-utils'
import D3DonutChart from '../D3DonutChart.vue'

vi.stubGlobal(
  'ResizeObserver',
  class {
    observe() {}
    disconnect() {}
  }
)

vi.stubGlobal('logService', { info: vi.fn(), error: vi.fn(), warn: vi.fn() })

describe('D3DonutChart legend (#325)', () => {
  it('shows every category with its count without hovering', () => {
    const wrapper = mount(D3DonutChart, {
      props: {
        data: [
          { category: 'Definitive', gene_count: 3, color: '#22c55e' },
          { category: 'Limited', gene_count: 1 }
        ]
      }
    })
    const items = wrapper.findAll('[data-testid="donut-legend"] li').map(li => li.text())
    expect(items).toEqual(['Definitive3 (75.0%)', 'Limited1 (25.0%)'])
  })
})
