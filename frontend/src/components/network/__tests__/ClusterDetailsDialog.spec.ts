/**
 * Cluster dialog: genes are named by their HGNC identifier (linked), never by internal
 * numeric ids, and HPO statistic chips are tinted with readable text, never white on colour.
 */
import { describe, it, expect, vi } from 'vitest'
import { mount, flushPromises } from '@vue/test-utils'
import { createRouter, createMemoryHistory } from 'vue-router'
import { TooltipProvider } from '@/components/ui/tooltip'
import { h } from 'vue'
import ClusterDetailsDialog from '../ClusterDetailsDialog.vue'

vi.stubGlobal('logService', { info: vi.fn(), warn: vi.fn(), error: vi.fn(), debug: vi.fn() })

describe('ClusterDetailsDialog', () => {
  it('shows HGNC identifiers and tinted HPO chips', async () => {
    const router = createRouter({
      history: createMemoryHistory(),
      routes: [{ path: '/:p(.*)*', component: { render: () => null } }]
    })
    mount(
      {
        render: () =>
          h(TooltipProvider, () =>
            h(ClusterDetailsDialog, {
              modelValue: true,
              clusterId: 0,
              clusterColor: 'var(--source-1)',
              genes: [{ gene_id: 6735, hgnc_id: 'HGNC:9008', symbol: 'PKD1', cluster_id: 0 }],
              hpoClassifications: {
                data: [{ gene_id: 6735, clinical_group: 'cyst_cilio', onset_group: 'adult' }]
              }
            })
          )
      },
      { global: { plugins: [router] }, attachTo: document.body }
    )
    await flushPromises()

    const link = document.querySelector('a[href*="genenames.org"]')
    expect(link?.textContent).toContain('PKD1')
    expect(link?.textContent).toContain('HGNC:9008')
    expect(document.body.textContent).not.toContain('6735')
    expect(document.body.innerHTML).not.toMatch(/color:\s*(#fff|white)/i)
    document.body.innerHTML = ''
  })
})
