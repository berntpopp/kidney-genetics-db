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

describe('EnrichmentTable identifiers and status', () => {
  const result = (term_id: string) => ({
    term_id,
    term_name: 'A very long term name that the table truncates with CSS only',
    p_value: 0.00012,
    fdr: 0.034,
    enrichment_score: 2,
    odds_ratio: 3,
    gene_count: 2,
    cluster_size: 10,
    background_count: 40,
    genes: ['PKD1', 'PKD2']
  })

  it('links HPO and GO term IDs and keeps the full name', () => {
    const wrapper = mount(EnrichmentTable, {
      props: { results: [result('HP:0000107'), result('GO:0001822'), result('KEGG_1')] }
    })
    const hrefs = wrapper.findAll('a').map(a => a.attributes('href'))
    expect(hrefs).toContain('https://hpo.jax.org/browse/term/HP:0000107')
    expect(hrefs).toContain('https://amigo.geneontology.org/amigo/term/GO:0001822')
    expect(wrapper.text()).toContain('KEGG_1')
    const name = wrapper.find('span[title^="A very long"]')
    expect(name.text()).toBe(result('x').term_name)
    expect(wrapper.text()).toContain('1.20e-4')
    expect(wrapper.text()).toContain('3.40e-2')
  })

  it('does not show the previous count while a new run is loading', () => {
    const wrapper = mount(EnrichmentTable, {
      props: { results: [result('HP:0000107')], loading: true }
    })
    expect(wrapper.text()).toContain('Running enrichment analysis')
    expect(wrapper.text()).not.toContain('significant term')
  })
})
