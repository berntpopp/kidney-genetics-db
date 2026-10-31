import { describe, expect, it } from 'vitest'
import { mount } from '@vue/test-utils'
import { ref, shallowRef } from 'vue'
import SpatialStatistics from '../SpatialStatistics.vue'
import type { usePositionStats } from '@/composables/usePositionStats'
import type { ClusterResult } from '@/types/positionStats'

type State = ReturnType<typeof usePositionStats>
type Spatial = NonNullable<State['spatial']['value']>
const NO_MODEL = 'No full-length AlphaFold model for this protein, so no 3D statistics.'
const CAVEAT = 'Statistical support for an ACMG/AMP PM1 assessment'

const cluster: ClusterResult = {
  observed: 23.4,
  nullMean: 28.8,
  nullLo: 26.7,
  nullHi: 30.9,
  p: 1 / 10001,
  histogram: [
    { x0: 25, x1: 26, n: 3 },
    { x0: 26, x1: 27, n: 0 },
    { x0: 27, x1: 28, n: 40 },
    { x0: 28, x1: 29, n: 60 }
  ],
  nCaseResidues: 46,
  B: 10000,
  seed: 20261031
}
const spatial: Spatial = {
  cluster,
  hotspots: {
    clusters: [
      {
        residues: [140, 141, 142, 159],
        residueAdjP: [0.01, 0.01, 0.01, 0.02],
        cases: 30,
        ctrls: 4,
        adjP: 0.0005
      }
    ],
    B: 2000,
    seed: 20261031,
    radius: 10
  }
}

function state(status = 'ready', sp: Spatial | null = spatial): State {
  return {
    status: ref(status),
    message: ref(''),
    variantSet: shallowRef({
      dropped: { clinvar: 0, gnomad: 0 },
      checked: { clinvar: 1, gnomad: 1 }
    }),
    linear: shallowRef(null),
    spatial: shallowRef(sp),
    spatialMessage: ref(''),
    minStars: ref(1),
    retry: () => {}
  } as unknown as State
}
const full = { uniprotStart: 1, uniprotEnd: 557, label: 'AF-P35680-F1 v6' }
const mk = (o: Record<string, unknown> = {}) =>
  mount(SpatialStatistics, {
    props: { state: state(), modelStatus: 'ready', model: full, length: 557, ...o }
  })

describe('SpatialStatistics', () => {
  it('states the clustering result with observed and null numbers', () => {
    const t = mk().get('[data-testid="cluster-sentence"]').text()
    expect(t).toContain('23.4 Å')
    expect(t).toContain('28.8 Å')
    expect(t).toContain('p < 0.0001')
  })

  it('draws one bar per non-empty bin and one labelled observed line', () => {
    const svg = mk().get('svg[role="img"]')
    expect(svg.findAll('rect:not([data-testid])')).toHaveLength(3)
    const lines = svg.findAll('line[aria-label]')
    expect(lines).toHaveLength(1)
    expect(lines[0]!.attributes('aria-label')).toContain('23.4')
    for (const r of svg.findAll('rect:not([data-testid])')) {
      expect(Number(r.attributes('width'))).toBeLessThanOrEqual(24)
    }
  })

  it('emits the residues of a clicked hotspot cluster', async () => {
    const w = mk()
    await w.get('[data-testid="hotspot-cluster"]').trigger('click')
    expect(w.emitted('select-cluster')).toEqual([[[140, 141, 142, 159]]])
    expect(w.text()).toContain('140–142, 159')
  })

  it.each([[{ uniprotStart: 2, uniprotEnd: 557 }], [{ uniprotStart: 1, uniprotEnd: 400 }]])(
    'a partial model gets the no-3D-statistics message (%o)',
    model => {
      const w = mk({ model })
      expect(w.get('[data-testid="spatial-notice"]').text()).toBe(NO_MODEL)
      expect(w.find('svg[role="img"]').exists()).toBe(false)
      expect(w.text()).toContain(CAVEAT)
    }
  )

  it('no model at all gets the same message', () => {
    expect(mk({ modelStatus: 'empty', model: null }).text()).toContain(NO_MODEL)
  })

  it('reserves the result layout while computing and still shows the caveat once', () => {
    const w = mk({ state: state('loading', null) })
    expect(w.find('[aria-busy="true"]').exists()).toBe(true)
    expect(w.text().split(CAVEAT)).toHaveLength(2)
  })

  it('marks the selected hotspot pressed and explains the count difference', () => {
    const w = mk({ selected: [140, 141, 142, 159] })
    expect(w.get('[data-testid="hotspot-cluster"]').attributes('aria-pressed')).toBe('true')
    expect(w.text()).toContain('differs from these sphere counts')
  })

  it('shows spatialMessage as a notice when the 3D part is unavailable', () => {
    const s = state('ready', null)
    s.spatialMessage.value = '3D statistics unavailable: AlphaFold responded 503'
    const w = mk({ state: s })
    expect(w.get('[data-testid="spatial-notice"]').text()).toBe(
      '3D statistics unavailable: AlphaFold responded 503'
    )
  })

  it('says plainly when too few residues are eligible for clustering', () => {
    const w = mk({ state: state('ready', { ...spatial, cluster: null }) })
    expect(w.get('[data-testid="cluster-sentence"]').text()).toContain('too few')
  })
})
