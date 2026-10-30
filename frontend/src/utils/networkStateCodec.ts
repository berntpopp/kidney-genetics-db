/**
 * Network State Codec
 *
 * Handles serialization and deserialization of network state
 * to/from URL query parameters. Supports both v1 (uncompressed)
 * and v2 (LZ-string compressed) formats.
 *
 * @module utils/networkStateCodec
 */

import { compressState, decompressState } from './stateCompression'

/** Decoded network analysis state */
export interface NetworkState {
  geneIds?: number[]
  filteredGenes?: Array<{ id: number; [key: string]: unknown }>
  selectedTiers?: string[]
  minScore?: number
  maxGenes?: number
  minStringScore?: number
  clusterAlgorithm?: string
  removeIsolated?: boolean
  minDegree?: number
  minClusterSize?: number
  largestComponentOnly?: boolean
  nodeColorMode?: string
  enrichmentType?: string
  /** 'reference' (default) or 'network' */
  enrichmentBackground?: string
  fdrThreshold?: number
  selectedClusters?: number[]
  highlightedCluster?: number | null
  isClustered?: boolean
  [key: string]: unknown
}

/** URL query parameters object */
export type QueryParams = Record<string, string>

/** Result of state validation */
export interface NetworkStateValidation {
  isValid: boolean
  missingFields: string[]
}

/**
 * Encode network state to URL query parameters
 * Defaults to v2 (compressed) for production use
 *
 * @param state - Network analysis state
 * @param version - Schema version (1=uncompressed, 2=compressed)
 * @returns Query parameters object
 */
export function encodeNetworkState(state: NetworkState, version = 2): QueryParams {
  if (version === 2) {
    return encodeNetworkStateV2(state)
  } else if (version === 1) {
    return encodeNetworkStateV1(state)
  } else {
    if (window.logService) {
      // Fix (Rule 1 - Bug): was logService.warning() which does not exist; correct method is warn()
      window.logService.warn(`[NetworkStateCodec] Unsupported version ${version}, using v2`)
    }
    return encodeNetworkStateV2(state)
  }
}

/**
 * Encodes the network analysis state into v2 (compressed) format for use in URL query parameters.
 * Uses LZ-string compression via `compressState`. If compression fails, falls back to v1 (uncompressed) format.
 *
 * @param state - The network analysis state to encode.
 * @returns Query parameters object containing the compressed state (`v: '2', c: <compressed>`).
 *
 * @private
 */
function encodeNetworkStateV2(state: NetworkState): QueryParams {
  try {
    const { compressed, originalSize, compressedSize, ratio } = compressState(
      state as Record<string, unknown>
    )

    if (window.logService) {
      window.logService.info('[NetworkStateCodec] Encoded to v2 (compressed)', {
        originalSize,
        compressedSize,
        compressionRatio: `${(ratio * 100).toFixed(0)}%`,
        geneCount: state.geneIds?.length ?? 0
      })
    }

    return {
      v: '2',
      c: compressed
    }
  } catch (error) {
    if (window.logService) {
      window.logService.error('[NetworkStateCodec] v2 encoding failed, falling back to v1:', error)
    }
    // Fallback to v1 if compression fails
    return encodeNetworkStateV1(state)
  }
}

/**
 * Encode network state to v1 (uncompressed) format
 * Used for debugging and as fallback
 *
 * @param state - Network analysis state
 * @returns Query parameters object
 */
function encodeNetworkStateV1(state: NetworkState): QueryParams {
  const params: QueryParams = {
    v: '1'
  }

  // Gene selection - handle both geneIds (new) and filteredGenes (legacy)
  if (state.geneIds && state.geneIds.length > 0) {
    params.genes = state.geneIds.join(',')
  } else if (state.filteredGenes && state.filteredGenes.length > 0) {
    // Backward compatibility: filteredGenes with objects
    params.genes = state.filteredGenes.map(g => g.id).join(',')
  }

  if (state.selectedTiers && state.selectedTiers.length > 0) {
    params.tiers = state.selectedTiers.join(',')
  }

  // minScore/minDegree/minCluster are always written: their UI defaults (20/2/3) differ from
  // the legacy "absent" meaning (0/0/1), so omitting them would not round-trip
  if (state.minScore !== undefined) {
    params.minScore = state.minScore.toString()
  }

  if (state.maxGenes !== undefined) {
    params.maxGenes = state.maxGenes.toString()
  }

  // Network construction
  if (state.minStringScore !== undefined && state.minStringScore !== 400) {
    params.stringScore = state.minStringScore.toString()
  }

  if (state.clusterAlgorithm && state.clusterAlgorithm !== 'leiden') {
    params.cluster = state.clusterAlgorithm
  }

  // Network filtering
  if (state.removeIsolated) {
    params.isolated = '1'
  }

  if (state.minDegree !== undefined) {
    params.minDegree = state.minDegree.toString()
  }

  if (state.minClusterSize !== undefined) {
    params.minCluster = state.minClusterSize.toString()
  }

  if (state.largestComponentOnly) {
    params.largestComp = '1'
  }

  // Node coloring
  if (state.nodeColorMode && state.nodeColorMode !== 'cluster') {
    params.colorMode = state.nodeColorMode
  }

  // Enrichment analysis
  if (state.enrichmentType && state.enrichmentType !== 'go') {
    params.enrichType = state.enrichmentType
  }

  if (state.enrichmentBackground === 'network') {
    params.bg = 'network'
  }

  if (state.fdrThreshold !== undefined && state.fdrThreshold !== 0.05) {
    params.fdr = state.fdrThreshold.toString()
  }

  if (state.selectedClusters && state.selectedClusters.length > 0) {
    params.selected = state.selectedClusters.join(',')
  }

  // Optional highlight
  if (state.highlightedCluster !== undefined && state.highlightedCluster !== null) {
    params.highlight = state.highlightedCluster.toString()
  }

  // Cluster state - track whether clustering has been performed
  if (state.isClustered) {
    params.clustered = '1'
  }

  return params
}

/**
 * Decode URL query parameters to network state
 * Automatically detects version and routes to appropriate decoder
 *
 * @param query - URL query parameters
 * @returns Decoded network state
 */
export function decodeNetworkState(query: QueryParams): NetworkState {
  const version = parseInt(query['v'] ?? '1') || 1

  if (version === 2) {
    return sanitizeNetworkState(decodeNetworkStateV2(query))
  } else if (version === 1) {
    return sanitizeNetworkState(decodeNetworkStateV1(query))
  } else {
    if (window.logService) {
      // Fix (Rule 1 - Bug): was logService.warning() which does not exist; correct method is warn()
      window.logService.warn(`[NetworkStateCodec] Unsupported schema version: ${version}, using v1`)
    }
    return sanitizeNetworkState(decodeNetworkStateV1(query))
  }
}

const isNumber = (v: unknown): boolean => typeof v === 'number' && Number.isFinite(v)
const isBoolean = (v: unknown): boolean => typeof v === 'boolean'
const isIntList = (v: unknown): boolean => Array.isArray(v) && v.every(n => Number.isInteger(n))
const oneOf =
  (...allowed: string[]) =>
  (v: unknown): boolean =>
    typeof v === 'string' && allowed.includes(v)

/** Accepted type per field; URL state is untrusted, so anything else is dropped */
const STATE_FIELDS: Record<string, (_v: unknown) => boolean> = {
  geneIds: v => isIntList(v) && (v as number[]).every(n => n > 0),
  selectedTiers: v => Array.isArray(v) && v.every(t => typeof t === 'string'),
  minScore: isNumber,
  maxGenes: isNumber,
  minStringScore: isNumber,
  clusterAlgorithm: oneOf('leiden', 'louvain', 'walktrap'),
  removeIsolated: isBoolean,
  minDegree: isNumber,
  minClusterSize: isNumber,
  largestComponentOnly: isBoolean,
  nodeColorMode: oneOf('cluster', 'clinical_group', 'onset_group', 'syndromic'),
  enrichmentType: oneOf('go', 'hpo'),
  enrichmentBackground: oneOf('reference', 'network'),
  fdrThreshold: isNumber,
  selectedClusters: isIntList,
  highlightedCluster: v => v === null || isNumber(v),
  isClustered: isBoolean
}

/**
 * Keep only known fields with the expected type. Invalid fields are dropped (the view then
 * uses its defaults); a non-object payload yields an empty state, which fails validation.
 */
export function sanitizeNetworkState(raw: unknown): NetworkState {
  if (!raw || typeof raw !== 'object' || Array.isArray(raw)) return {}
  const state: NetworkState = {}
  for (const [key, isValid] of Object.entries(STATE_FIELDS)) {
    const value = (raw as Record<string, unknown>)[key]
    if (value !== undefined && isValid(value)) state[key] = value
  }
  return state
}

/**
 * Decode v2 (compressed) format to network state
 *
 * @param query - URL query parameters with 'c' (compressed) field
 * @returns Decoded network state
 */
function decodeNetworkStateV2(query: QueryParams): NetworkState {
  try {
    if (!query.c) {
      throw new Error('Missing compressed state parameter "c"')
    }

    const state = decompressState(query.c!) as NetworkState
    if (!state || typeof state !== 'object' || Array.isArray(state)) {
      throw new Error('Compressed state is not an object')
    }

    if (window.logService) {
      window.logService.info('[NetworkStateCodec] Decoded from v2 (compressed)', {
        compressedSize: query.c.length,
        geneCount: state.geneIds?.length ?? 0,
        maxGenes: state.maxGenes,
        minClusterSize: state.minClusterSize,
        isClustered: state.isClustered
      })
    }

    return state
  } catch (error) {
    if (window.logService) {
      window.logService.error('[NetworkStateCodec] v2 decoding failed:', error)
    }
    throw new Error(`Failed to decode compressed URL state: ${(error as Error).message}`, {
      cause: error
    })
  }
}

/**
 * Decode v1 (uncompressed) format to network state
 *
 * @param query - URL query parameters
 * @returns Decoded network state
 */
function decodeNetworkStateV1(query: QueryParams): NetworkState {
  const state: NetworkState = {}

  // Gene selection
  if (query.genes) {
    state.geneIds = query.genes
      .split(',')
      .map(id => parseInt(id, 10))
      .filter(id => !isNaN(id))
  }

  if (query.tiers) {
    state.selectedTiers = query.tiers.split(',')
  }

  // Legacy v1 links omitted these when 0/0/1; absence keeps that meaning
  state.minScore = parseInt(query.minScore ?? '', 10) || 0

  if (query.maxGenes) {
    state.maxGenes = parseInt(query.maxGenes, 10) || 200
  }

  // Network construction
  if (query.stringScore) {
    state.minStringScore = parseInt(query.stringScore, 10) || 400
  }

  if (query.cluster) {
    state.clusterAlgorithm = query.cluster
  }

  // Network filtering
  state.removeIsolated = query.isolated === '1'

  state.minDegree = parseInt(query.minDegree ?? '', 10) || 0
  state.minClusterSize = parseInt(query.minCluster ?? '', 10) || 1

  state.largestComponentOnly = query.largestComp === '1'

  // Node coloring
  if (query.colorMode) {
    state.nodeColorMode = query.colorMode
  }

  // Enrichment analysis
  if (query.enrichType) {
    state.enrichmentType = query.enrichType
  }

  if (query.bg === 'network') {
    state.enrichmentBackground = 'network'
  }

  if (query.fdr) {
    state.fdrThreshold = parseFloat(query.fdr) || 0.05
  }

  if (query.selected) {
    state.selectedClusters = query.selected
      .split(',')
      .map(id => parseInt(id, 10))
      .filter(id => !isNaN(id))
  }

  // Optional highlight
  if (query.highlight) {
    state.highlightedCluster = parseInt(query.highlight, 10)
  }

  // Cluster state - whether clustering has been performed
  state.isClustered = query.clustered === '1'

  return state
}

/**
 * Validate state object completeness
 *
 * @param state - Network state
 * @returns Validation result { isValid, missingFields }
 */
export function validateNetworkState(state: NetworkState): NetworkStateValidation {
  const requiredFields: (keyof NetworkState)[] = ['geneIds']
  const missingFields = requiredFields.filter(
    field => !state[field] || (state[field] as unknown[]).length === 0
  )

  return {
    isValid: missingFields.length === 0,
    missingFields: missingFields as string[]
  }
}

export default {
  encodeNetworkState,
  decodeNetworkState,
  validateNetworkState,
  sanitizeNetworkState
}
