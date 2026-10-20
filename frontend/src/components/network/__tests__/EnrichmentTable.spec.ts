import { describe, it, expect, vi } from 'vitest'
import { mount } from '@vue/test-utils'
import EnrichmentTable from '@/components/network/EnrichmentTable.vue'

vi.stubGlobal('logService', { info: vi.fn(), warn: vi.fn(), error: vi.fn(), debug: vi.fn() })

describe('EnrichmentTable', () => {
  it('says how many genes the HPO test excluded', () => {
    const wrapper = mount(EnrichmentTable, { props: { excludedGenes: [11, 12, 13] } })
    expect(wrapper.text()).toContain('3 genes excluded (no HPO annotation / outside background)')
  })

  it('stays quiet when no genes were excluded', () => {
    const wrapper = mount(EnrichmentTable, { props: { excludedGenes: [] } })
    expect(wrapper.text()).not.toContain('excluded')
  })
})
