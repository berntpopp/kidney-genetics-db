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

/**
 * Configuration for evidence tiers
 */
export const TIER_CONFIG: Record<TierName, TierConfig> = {
  comprehensive_support: {
    label: 'Comprehensive Support',
    color: '#22c55e',
    icon: CircleCheck,
    description: '4+ sources with robust evidence (score ≥50%)'
  },
  multi_source_support: {
    label: 'Multi-Source Support',
    color: '#3b82f6',
    icon: CircleCheckBig,
    description: '3+ sources with emerging evidence (score ≥35%)'
  },
  established_support: {
    label: 'Established Support',
    color: '#0ea5e9',
    icon: Check,
    description: '2+ sources with moderate evidence (score ≥20%)'
  },
  preliminary_evidence: {
    label: 'Preliminary Evidence',
    color: '#f59e0b',
    icon: CircleAlert,
    description: 'Initial evidence requiring validation (score ≥10%)'
  },
  minimal_evidence: {
    label: 'Minimal Evidence',
    color: '#6b7280',
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
    color: '#22c55e',
    icon: Star,
    description: '2+ sources with strong evidence scores'
  },
  emerging_evidence: {
    label: 'Emerging Evidence',
    color: '#f59e0b',
    icon: Star,
    description: 'Initial evidence, needs further validation'
  }
}

/**
 * Inline style for a chip tinted with `color` (hex). The text is mixed toward the
 * theme foreground so it stays WCAG AA on the tint in light and dark mode (#320).
 */
export function tintedChipStyle(color: string): Record<string, string> {
  return {
    backgroundColor: color + '20',
    color: `color-mix(in oklab, ${color} 55%, var(--foreground))`,
    borderColor: color + '40'
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
      color: '#9ca3af',
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
      color: '#9ca3af',
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
 * Explain an evidence score with the backend evidence tier
 * @param score - Evidence score (0-100)
 * @param sourceCount - Number of sources
 * @param tier - Backend evidence_tier
 * @returns Formatted explanation
 */
export function getScoreExplanation(
  score: number | null | undefined,
  sourceCount: number | null | undefined,
  tier: string | null | undefined
): string {
  if (!score && score !== 0) return 'No evidence score available'
  if (!tier) return `Score: ${score.toFixed(1)}%`
  const label = getTierConfig(tier).label
  if (!sourceCount) return `${score.toFixed(1)}% — ${label}`
  return `${score.toFixed(1)}% — ${label} from ${sourceCount} ${sourceCount === 1 ? 'source' : 'sources'}`
}
