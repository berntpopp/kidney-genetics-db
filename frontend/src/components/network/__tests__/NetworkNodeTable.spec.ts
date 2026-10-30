import { describe, it, expect } from 'vitest'
import { mount } from '@vue/test-utils'
import NetworkNodeTable, { type NodeRow } from '../NetworkNodeTable.vue'

const row = (gene_id: number, label: string, clusterRank: number, degree: number): NodeRow => ({
  gene_id,
  label,
  hgnc_id: `HGNC:${gene_id}`,
  cluster_id: clusterRank,
  clusterName: `Cluster ${clusterRank + 1}`,
  clusterRank,
  color: '#000',
  outline: '#000',
  degree
})

const symbols = (wrapper: ReturnType<typeof mount>) =>
  wrapper.findAll('tbody tr').map(r => r.find('button').text())

describe('NetworkNodeTable', () => {
  const rows = [row(1, 'PKD2', 1, 3), row(2, 'ACTN4', 0, 1), row(3, 'PKD1', 0, 7)]

  it('sorts by degree first, then by the column a header button picks', async () => {
    const wrapper = mount(NetworkNodeTable, { props: { rows } })
    expect(symbols(wrapper)).toEqual(['PKD1', 'PKD2', 'ACTN4'])
    expect(wrapper.find('th[aria-sort="descending"]').text()).toContain('Degree')

    const header = (name: string) => wrapper.findAll('th button').find(b => b.text() === name)!
    await header('Gene').trigger('click')
    expect(symbols(wrapper)).toEqual(['ACTN4', 'PKD1', 'PKD2'])
    await header('Gene').trigger('click')
    expect(symbols(wrapper)).toEqual(['PKD2', 'PKD1', 'ACTN4'])
    await header('Cluster').trigger('click')
    expect(symbols(wrapper)).toEqual(['ACTN4', 'PKD1', 'PKD2'])
  })

  it('emits the node payload when a gene is activated with Enter', async () => {
    const wrapper = mount(NetworkNodeTable, { props: { rows } })
    await wrapper.find('tbody button').trigger('keydown', { key: 'Enter' })
    expect(wrapper.emitted('select')).toEqual([[{ label: 'PKD1', gene_id: 3, cluster_id: 0 }]])
  })

  it('pages long lists', async () => {
    const many = Array.from({ length: 60 }, (_, i) => row(i + 1, `G${i + 1}`, 0, i))
    const wrapper = mount(NetworkNodeTable, { props: { rows: many } })
    expect(wrapper.findAll('tbody tr').length).toBe(25)
    await wrapper
      .findAll('button')
      .find(b => b.text() === 'Next')!
      .trigger('click')
    expect(wrapper.text()).toContain('26–50 of 60')
  })
})
