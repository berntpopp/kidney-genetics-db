import { describe, it, expect, vi } from 'vitest'
import { flushPromises, mount } from '@vue/test-utils'
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

describe('EnrichmentTable client-side sorting and paging', () => {
  const terms = 'kidney liver heart lung brain bone skin eye ear gut nerve blood'.split(' ')
  const results = terms.map((name, i) => ({
    term_id: `T${i}`,
    term_name: name,
    p_value: 0.001,
    fdr: 0.01,
    enrichment_score: 2,
    odds_ratio: 3,
    gene_count: 1,
    background_count: 10,
    genes: []
  }))
  const firstCells = () =>
    [...document.querySelectorAll('tbody tr')].map(r => r.children[0].textContent)

  it('sorts by a column and pages through the sorted rows', async () => {
    const wrapper = mount(EnrichmentTable, { props: { results }, attachTo: document.body })
    expect(wrapper.text()).toContain('Page 1 of 2')
    expect(firstCells()).toEqual(terms.slice(0, 10))

    const termButton = wrapper.findAll('button').find(b => b.text() === 'Term')!
    await termButton.trigger('keydown', { key: 'Enter' })
    await flushPromises()
    const asc = [...document.querySelectorAll('[role="menuitem"]')].find(
      e => e.textContent?.trim() === 'Asc'
    ) as HTMLElement
    asc.click()
    await flushPromises()

    const sorted = [...terms].sort()
    expect(firstCells()).toEqual(sorted.slice(0, 10))
    await wrapper.get('button[aria-label="Go to next page"]').trigger('click')
    expect(firstCells()).toEqual(sorted.slice(10))
    expect(wrapper.text()).toContain('Page 2 of 2')
    wrapper.unmount()
    document.body.innerHTML = ''
  })
})
