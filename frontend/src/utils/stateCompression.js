/**
 * State Compression Utilities
 *
 * Handles compression and decompression of network state for URL encoding.
 * Uses LZ-string library for optimal URL-safe compression.
 *
 * @module utils/stateCompression
 */

import LZString from 'lz-string'

/**
 * Compress network state to URI-safe string
 *
 * @param {Object} state - Network analysis state
 * @returns {Object} { compressed, originalSize, compressedSize, ratio }
 * @throws {Error} If compression fails
 *
 * @example
 * const result = compressState({ geneIds: [1,2,3], filters: {...} })
 * // Returns: { compressed: "eJy...", originalSize: 450, compressedSize: 120, ratio: 0.73 }
 */
export function compressState(state) {
  try {
    // Serialize to JSON
    const json = JSON.stringify(state)
    const originalSize = json.length

    // Compress using LZ-string (URI-safe encoding)
    const compressed = LZString.compressToEncodedURIComponent(json)
    const compressedSize = compressed.length

    // Calculate compression ratio
    const ratio = ((originalSize - compressedSize) / originalSize).toFixed(2)

    if (window.logService) {
      window.logService.debug('[StateCompression] Compression successful', {
        originalSize,
        compressedSize,
        ratio: `${(ratio * 100).toFixed(0)}%`,
        geneCount: state.filteredGenes?.length || 0
      })
    }

    return {
      compressed,
      originalSize,
      compressedSize,
      ratio: parseFloat(ratio)
    }
  } catch (error) {
    if (window.logService) {
      window.logService.error('[StateCompression] Compression failed:', error)
    }
    throw new Error(`Failed to compress state: ${error.message}`)
  }
}

/**
 * Decompress URI-safe string to network state
 *
 * @param {string} compressed - Compressed state string
 * @returns {Object} Decompressed network state
 * @throws {Error} If decompression fails
 *
 * @example
 * const state = decompressState("eJy...")
 * // Returns: { geneIds: [1,2,3], filters: {...} }
 */
export function decompressState(compressed) {
  try {
    // Decompress from URI-safe encoding
    const json = LZString.decompressFromEncodedURIComponent(compressed)

    if (!json) {
      throw new Error('Decompression returned null - invalid compressed data')
    }

    // Parse JSON
    const state = JSON.parse(json)

    if (window.logService) {
      window.logService.debug('[StateCompression] Decompression successful', {
        compressedSize: compressed.length,
        geneCount: state.geneIds?.length || 0
      })
    }

    return state
  } catch (error) {
    if (window.logService) {
      window.logService.error('[StateCompression] Decompression failed:', error, {
        compressedLength: compressed?.length || 0,
        firstChars: compressed?.substring(0, 20) || 'null'
      })
    }
    throw new Error(`Failed to decompress state: ${error.message}`)
  }
}

/**
 * Check if compressed string is valid LZ-string format
 *
 * @param {string} compressed - String to validate
 * @returns {boolean} True if valid
 */
export function isValidCompressed(compressed) {
  if (!compressed || typeof compressed !== 'string') {
    return false
  }

  try {
    const decompressed = LZString.decompressFromEncodedURIComponent(compressed)
    return decompressed !== null && decompressed !== ''
  } catch {
    return false
  }
}

/**
 * Estimate compressed size without actually compressing
 * Useful for warning users about extremely large states
 *
 * @param {Object} state - Network state to estimate
 * @returns {number} Estimated compressed size in characters
 */
export function estimateCompressedSize(state) {
  const json = JSON.stringify(state)
  // Use empirical compression ratio of 74%
  return Math.ceil(json.length * 0.26)
}

export default {
  compressState,
  decompressState,
  isValidCompressed,
  estimateCompressedSize
}
