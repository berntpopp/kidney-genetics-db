import { describe, it, expect } from 'vitest'
import LZString from 'lz-string'
import { encodeNetworkState, decodeNetworkState } from '@/utils/networkStateCodec'

const v2 = (payload: unknown) => ({
  v: '2',
  c: LZString.compressToEncodedURIComponent(JSON.stringify(payload))
})

describe('networkStateCodec', () => {
  it('v1 round-trips zero / minimum values instead of dropping them', () => {
    const state = { geneIds: [1, 2], minScore: 0, minDegree: 0, minClusterSize: 1 }
    const decoded = decodeNetworkState(encodeNetworkState(state, 1))
    expect(decoded).toMatchObject(state)
  })

  it('legacy v1 links without those params keep their old meaning (0/0/1)', () => {
    const decoded = decodeNetworkState({ v: '1', genes: '1,2' })
    expect(decoded).toMatchObject({ minScore: 0, minDegree: 0, minClusterSize: 1 })
  })

  it('v2 round-trips a full state', () => {
    const state = {
      geneIds: [3, 4],
      minScore: 0,
      minDegree: 0,
      minClusterSize: 1,
      clusterAlgorithm: 'walktrap',
      isClustered: true,
      selectedClusters: [0, 2],
      highlightedCluster: null
    }
    expect(decodeNetworkState(encodeNetworkState(state))).toEqual(state)
  })

  it('v2 drops fields with the wrong type or unknown values', () => {
    const decoded = decodeNetworkState(
      v2({
        geneIds: [1, 2],
        minScore: '20',
        clusterAlgorithm: 'evil',
        selectedClusters: 'x',
        isClustered: 1,
        unknownField: 1
      })
    )
    expect(decoded).toEqual({ geneIds: [1, 2] })
  })

  it('v2 with invalid gene ids yields no geneIds (restore then fails validation)', () => {
    expect(decodeNetworkState(v2({ geneIds: [1, -2] })).geneIds).toBeUndefined()
    expect(decodeNetworkState(v2({ geneIds: 5 })).geneIds).toBeUndefined()
  })

  it('v2 payload that is not an object throws instead of crashing later', () => {
    expect(() => decodeNetworkState(v2([1, 2]))).toThrow()
    expect(() => decodeNetworkState(v2(5))).toThrow()
    expect(() => decodeNetworkState({ v: '2', c: 'not-lz' })).toThrow()
  })
})
