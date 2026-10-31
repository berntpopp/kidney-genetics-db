import { describe, expect, it } from 'vitest'
import { mount } from '@vue/test-utils'
import { ref, shallowRef } from 'vue'
import PositionStatistics from '../PositionStatistics.vue'
import type { usePositionStats } from '@/composables/usePositionStats'
import type { DomainResult, ScanResult, VariantSetSummary } from '@/types/positionStats'

type State = ReturnType<typeof usePositionStats>
const CAVEAT =
  'Statistical support for an ACMG/AMP PM1 assessment, not a classification. Population variants are not benign variants. Research use.'

const dom = (o: Partial<DomainResult>): DomainResult => ({
  key: 'a',
  label: 'Disordered',
  type: 'Region',
  start: 1,
  end: 50,
  caseIn: 2,
  ctrlIn: 30,
  caseOut: 48,
  ctrlOut: 300,
  p: 0.5,
  or: 0.7,
  lo: 0.1,
  hi: 3,
  q: 0.6,
  ...o
})
const scan: ScanResult = {
  windows: [],
  regions: [{ start: 122, end: 179, cases: 40, ctrls: 6, benign: 0, adjP: 1 / 10001 }],
  B: 10000,
  seed: 20261031,
  w: 15
}
const set: VariantSetSummary = {
  cases: 84,
  controls: 607,
  benign: 6,
  dropped: { clinvar: 0, gnomad: 12 },
  checked: { clinvar: 120, gnomad: 645 }
}

function state(status: string, message = '', linear: State['linear']['value'] = null): State {
  return {
    status: ref(status),
    message: ref(message),
    variantSet: shallowRef(set),
    linear: shallowRef(linear),
    spatial: shallowRef(null),
    spatialMessage: ref(''),
    minStars: ref(1),
    retry: () => {}
  } as unknown as State
}

const ready = () =>
  state('ready', '', {
    domains: [
      dom({}),
      dom({
        key: 'pou',
        label: 'POU-specific atypical',
        type: 'Domain',
        start: 93,
        end: 188,
        caseIn: 60,
        ctrlIn: 40,
        caseOut: 20,
        ctrlOut: 600,
        or: 7.06,
        lo: 4.17,
        hi: 11.96,
        p: 1e-14,
        q: 3.8e-13
      }),
      dom({ key: 'z', label: 'Zinc', type: 'Motif', or: 0, lo: 0, hi: Infinity, q: 1, p: 1 })
    ],
    scan
  })

describe('PositionStatistics', () => {
  it('sorts rows by q and marks significant rows', () => {
    const w = mount(PositionStatistics, { props: { state: ready() } })
    const rows = w.findAll('tbody tr').slice(0, 3)
    expect(rows.map(r => r.attributes('data-significant'))).toEqual(['true', 'false', 'false'])
    expect(rows[0].text()).toContain('POU-specific atypical')
    expect(w.get('[data-testid="domain-sentence"]').text()).toContain('7.1× more likely')
    expect(w.findAll('[data-arrow]').length).toBe(2) // 0 and ∞ bounds of the Zinc row
  })

  it('shows the 2×2 counts on row focus', async () => {
    const w = mount(PositionStatistics, { props: { state: ready() } })
    await w.findAll('tbody tr')[0].trigger('focus')
    expect(w.get('[data-testid="domain-detail"]').text()).toBe(
      'POU-specific atypical domain (93–188): inside 60 P/LP and 40 gnomAD; outside 20 P/LP and 600 gnomAD.'
    )
  })

  it('renders the hotspot-region twin and the caveat verbatim', () => {
    const w = mount(PositionStatistics, { props: { state: ready() } })
    expect(w.text()).toContain('122–179')
    expect(w.text()).toContain('< 0.0001')
    expect(w.text().replace(/\s+/g, ' ')).toContain(CAVEAT)
  })

  it('limits long feature lists to 10 rows until expanded', async () => {
    const many = Array.from({ length: 14 }, (_, i) => dom({ key: `r${i}`, start: i + 1 }))
    const w = mount(PositionStatistics, {
      props: { state: state('ready', '', { domains: many, scan }) }
    })
    const rows = () => w.findAll('tbody tr[data-significant]').length
    expect(rows()).toBe(10)
    await w
      .findAll('button')
      .find(b => b.text() === 'Show all 14 features')!
      .trigger('click')
    expect(rows()).toBe(14)
  })

  it.each([
    ['withheld', 'More than 10% of gnomAD variants did not match the UniProt sequence.'],
    ['too-few', 'Too few P/LP missense variants for a meaningful test.'],
    ['error', 'gnomAD request failed (HTTP 429)']
  ])('%s state shows its message and no table', (status, message) => {
    const w = mount(PositionStatistics, { props: { state: state(status, message) } })
    expect(w.text()).toContain(message)
    expect(w.find('table').exists()).toBe(false)
    expect(w.text().replace(/\s+/g, ' ')).toContain(CAVEAT)
  })

  it('shows the caveat while loading and labels focusable rows with their counts', () => {
    expect(mount(PositionStatistics, { props: { state: state('loading') } }).text()).toContain(
      CAVEAT
    )
    const row = mount(PositionStatistics, { props: { state: ready() } }).get('tbody tr')
    expect(row.attributes('aria-label')).toContain('inside 60 P/LP and 40 gnomAD')
    expect(row.attributes('aria-label')).toContain('Odds ratio 7.1 (95% CI 4.2 to 12), q < 0.001')
  })
})
