/**
 * Evidence tier configuration and utility functions
 * Used for displaying tier badges and managing tier-related UI
 */

/**
 * Configuration for evidence tiers
 * @type {Object.<string, Object>}
 */
export const TIER_CONFIG = {
  comprehensive_support: {
    label: 'Comprehensive Support',
    color: 'success',
    icon: 'mdi-check-circle',
    description: '4+ sources with robust evidence (score ≥50%)'
  },
  multi_source_support: {
    label: 'Multi-Source Support',
    color: 'info',
    icon: 'mdi-check-circle-outline',
    description: '3+ sources with emerging evidence (score ≥35%)'
  },
  established_support: {
    label: 'Established Support',
    color: 'primary',
    icon: 'mdi-check',
    description: '2+ sources with moderate evidence (score ≥20%)'
  },
  preliminary_evidence: {
    label: 'Preliminary Evidence',
    color: 'warning',
    icon: 'mdi-alert-circle-outline',
    description: 'Initial evidence requiring validation (score ≥10%)'
  },
  minimal_evidence: {
    label: 'Minimal Evidence',
    color: 'grey',
    icon: 'mdi-information-outline',
    description: 'Limited early-stage evidence (score <10%)'
  }
}

/**
 * Configuration for evidence groups
 * @type {Object.<string, Object>}
 */
export const GROUP_CONFIG = {
  well_supported: {
    label: 'Well-Supported',
    color: 'success',
    icon: 'mdi-star',
    description: '2+ sources with strong evidence scores'
  },
  emerging_evidence: {
    label: 'Emerging Evidence',
    color: 'warning',
    icon: 'mdi-star-outline',
    description: 'Initial evidence, needs further validation'
  }
}

/**
 * Get tier configuration by tier name
 * @param {string|null} tier - Tier name
 * @returns {Object} Tier configuration object
 */
export function getTierConfig(tier) {
  if (!tier || !TIER_CONFIG[tier]) {
    return {
      label: 'No Classification',
      color: 'grey-lighten-2',
      icon: 'mdi-help-circle-outline',
      description: 'No evidence tier assigned'
    }
  }
  return TIER_CONFIG[tier]
}

/**
 * Get group configuration by group name
 * @param {string|null} group - Group name
 * @returns {Object} Group configuration object
 */
export function getGroupConfig(group) {
  if (!group || !GROUP_CONFIG[group]) {
    return {
      label: 'Unclassified',
      color: 'grey-lighten-2',
      icon: 'mdi-help-circle-outline',
      description: 'No evidence group assigned'
    }
  }
  return GROUP_CONFIG[group]
}

/**
 * Get sort order for tier (lower is better)
 * @param {string|null} tier - Tier name
 * @returns {number} Sort order
 */
export function getTierSortOrder(tier) {
  const order = {
    comprehensive_support: 1,
    multi_source_support: 2,
    established_support: 3,
    preliminary_evidence: 4,
    minimal_evidence: 5
  }
  return tier ? order[tier] || 999 : 999
}

/**
 * List of all valid tier values
 * @type {string[]}
 */
export const VALID_TIERS = Object.keys(TIER_CONFIG)

/**
 * List of all valid group values
 * @type {string[]}
 */
export const VALID_GROUPS = Object.keys(GROUP_CONFIG)

/**
 * Configuration for evidence score ranges and their interpretations
 * Aligned with tier thresholds: 50% (comprehensive), 35% (multi-source), 20% (established), 10% (preliminary)
 * Ordered from highest to lowest threshold
 * @type {Array.<Object>}
 */
export const SCORE_RANGES = [
  {
    threshold: 95,
    label: 'Exceptional',
    description: 'comprehensive support with definitive multi-source evidence',
    color: 'success',
    tierAlignment: 'comprehensive_support'
  },
  {
    threshold: 80,
    label: 'Very Strong',
    description: 'comprehensive support, well-established disease gene',
    color: 'success',
    tierAlignment: 'comprehensive_support'
  },
  {
    threshold: 50,
    label: 'Strong',
    description: 'comprehensive support with robust evidence',
    color: 'success',
    tierAlignment: 'comprehensive_support'
  },
  {
    threshold: 35,
    label: 'Good',
    description: 'multi-source support with emerging evidence',
    color: 'info',
    tierAlignment: 'multi_source_support'
  },
  {
    threshold: 20,
    label: 'Moderate',
    description: 'established support from independent sources',
    color: 'primary',
    tierAlignment: 'established_support'
  },
  {
    threshold: 10,
    label: 'Preliminary',
    description: 'initial evidence requiring validation',
    color: 'warning',
    tierAlignment: 'preliminary_evidence'
  },
  {
    threshold: 0,
    label: 'Minimal',
    description: 'limited early-stage evidence',
    color: 'grey',
    tierAlignment: 'minimal_evidence'
  }
]

/**
 * Get score range configuration for a given score
 * @param {number} score - Evidence score (0-100)
 * @returns {Object} Score range configuration
 */
export function getScoreRangeConfig(score) {
  if (!score && score !== 0) return null

  for (const range of SCORE_RANGES) {
    if (score >= range.threshold) {
      return range
    }
  }

  return SCORE_RANGES[SCORE_RANGES.length - 1]
}

/**
 * Generate a contextual explanation for an evidence score
 * @param {number} score - Evidence score (0-100)
 * @param {number} sourceCount - Number of sources
 * @returns {string} Formatted explanation
 */
export function getScoreExplanation(score, sourceCount) {
  if (!score && score !== 0) return 'No evidence score available'
  if (!sourceCount || sourceCount === 0) return `Score: ${score.toFixed(1)}%`

  const sources = sourceCount === 1 ? 'source' : 'sources'
  const config = getScoreRangeConfig(score)

  if (!config) return `Score: ${score.toFixed(1)}%`

  // Special case for exceptional scores (no source count needed in message)
  if (config.threshold >= 95) {
    return `${score.toFixed(1)}% — ${config.label} (${config.description})`
  }

  // All other scores include source count
  return `${score.toFixed(1)}% — ${config.label} from ${sourceCount} ${sources} (${config.description})`
}
