/**
 * Evidence tier configuration and utility functions
 * Used for displaying tier badges and managing tier-related UI
 */

import type { Component } from 'vue'
import {
  CircleCheck,
  CircleCheckBig,
  Check,
  CircleAlert,
  Info,
  Star,
  CircleHelp
} from 'lucide-vue-next'

/** Union of all valid tier name strings */
export type TierName =
  | 'comprehensive_support'
  | 'multi_source_support'
  | 'established_support'
  | 'preliminary_evidence'
  | 'minimal_evidence'

/** Union of all valid group name strings */
export type GroupName = 'well_supported' | 'emerging_evidence'

/** Configuration object for a single evidence tier */
export interface TierConfig {
  label: string
  color: string
  icon: Component
  description: string
}

/** Configuration object for an evidence group */
export interface GroupConfig {
  label: string
  color: string
  icon: Component
  description: string
}

/** Configuration object for a score range */
export interface ScoreRangeConfig {
  threshold: number
  label: string
  description: string
  color: string
  tierAlignment: TierName
}

/**
 * Configuration for evidence tiers
 */
export const TIER_CONFIG: Record<TierName, TierConfig> = {
  comprehensive_support: {
    label: 'Comprehensive Support',
    color: 'success',
    icon: CircleCheck,
    description: '4+ sources with robust evidence (score ≥50%)'
  },
  multi_source_support: {
    label: 'Multi-Source Support',
    color: 'info',
    icon: CircleCheckBig,
    description: '3+ sources with emerging evidence (score ≥35%)'
  },
  established_support: {
    label: 'Established Support',
    color: 'primary',
    icon: Check,
    description: '2+ sources with moderate evidence (score ≥20%)'
  },
  preliminary_evidence: {
    label: 'Preliminary Evidence',
    color: 'warning',
    icon: CircleAlert,
    description: 'Initial evidence requiring validation (score ≥10%)'
  },
  minimal_evidence: {
    label: 'Minimal Evidence',
    color: 'grey',
    icon: Info,
    description: 'Limited early-stage evidence (score <10%)'
  }
}

/**
 * Configuration for evidence groups
 */
export const GROUP_CONFIG: Record<GroupName, GroupConfig> = {
  well_supported: {
    label: 'Well-Supported',
    color: 'success',
    icon: Star,
    description: '2+ sources with strong evidence scores'
  },
  emerging_evidence: {
    label: 'Emerging Evidence',
    color: 'warning',
    icon: Star,
    description: 'Initial evidence, needs further validation'
  }
}

/**
 * Get tier configuration by tier name
 * @param tier - Tier name
 * @returns Tier configuration object
 */
export function getTierConfig(tier: string | null | undefined): TierConfig {
  if (!tier || !(tier in TIER_CONFIG)) {
    return {
      label: 'No Classification',
      color: 'grey-lighten-2',
      icon: CircleHelp,
      description: 'No evidence tier assigned'
    }
  }
  return TIER_CONFIG[tier as TierName]
}

/**
 * Get group configuration by group name
 * @param group - Group name
 * @returns Group configuration object
 */
export function getGroupConfig(group: string | null | undefined): GroupConfig {
  if (!group || !(group in GROUP_CONFIG)) {
    return {
      label: 'Unclassified',
      color: 'grey-lighten-2',
      icon: CircleHelp,
      description: 'No evidence group assigned'
    }
  }
  return GROUP_CONFIG[group as GroupName]
}

/**
 * Get sort order for tier (lower is better)
 * @param tier - Tier name
 * @returns Sort order
 */
export function getTierSortOrder(tier: string | null | undefined): number {
  const order: Record<TierName, number> = {
    comprehensive_support: 1,
    multi_source_support: 2,
    established_support: 3,
    preliminary_evidence: 4,
    minimal_evidence: 5
  }
  return tier && tier in order ? order[tier as TierName] : 999
}

/**
 * List of all valid tier values
 */
export const VALID_TIERS: TierName[] = Object.keys(TIER_CONFIG) as TierName[]

/**
 * List of all valid group values
 */
export const VALID_GROUPS: GroupName[] = Object.keys(GROUP_CONFIG) as GroupName[]

/**
 * Configuration for evidence score ranges and their interpretations
 * Aligned with tier thresholds: 50% (comprehensive), 35% (multi-source), 20% (established), 10% (preliminary)
 * Ordered from highest to lowest threshold
 */
export const SCORE_RANGES: ScoreRangeConfig[] = [
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
 * @param score - Evidence score (0-100)
 * @returns Score range configuration or null if score is invalid
 */
export function getScoreRangeConfig(score: number | null | undefined): ScoreRangeConfig | null {
  if (!score && score !== 0) return null

  for (const range of SCORE_RANGES) {
    if (score >= range.threshold) {
      return range
    }
  }

  return SCORE_RANGES[SCORE_RANGES.length - 1] ?? null
}

/**
 * Generate a contextual explanation for an evidence score
 * @param score - Evidence score (0-100)
 * @param sourceCount - Number of sources
 * @returns Formatted explanation
 */
export function getScoreExplanation(
  score: number | null | undefined,
  sourceCount: number | null | undefined
): string {
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
