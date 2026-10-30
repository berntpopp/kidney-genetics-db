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
  CircleHelp,
  CircleX,
  TriangleAlert
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
 * Configuration for evidence tiers. Colours are the --strength-N tokens in
 * assets/main.css, which keep OKLab distance > 0.15 under deuteranopia and tinted
 * chips >= 4.5:1 (tierPalette.spec.ts, #325); the icon is the non-colour cue.
 */
export const TIER_CONFIG: Record<TierName, TierConfig> = {
  comprehensive_support: {
    label: 'Comprehensive Support',
    color: 'var(--strength-5)',
    icon: CircleCheck,
    description: '4+ sources incl. a curated assertion (score ≥50%)'
  },
  multi_source_support: {
    label: 'Multi-Source Support',
    color: 'var(--strength-4)',
    icon: CircleCheckBig,
    description: '3+ sources incl. a curated assertion (score ≥35%)'
  },
  established_support: {
    label: 'Established Support',
    color: 'var(--strength-3)',
    icon: Check,
    description: '2+ sources incl. a curated assertion (score ≥20%)'
  },
  preliminary_evidence: {
    label: 'Preliminary Evidence',
    color: 'var(--strength-2)',
    icon: CircleAlert,
    description: 'Initial evidence requiring validation (score ≥10%)'
  },
  minimal_evidence: {
    label: 'Minimal Evidence',
    color: 'var(--strength-1)',
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
    color: 'var(--strength-4)',
    icon: Star,
    description: '2+ sources incl. a curated assertion (score ≥20%)'
  },
  emerging_evidence: {
    label: 'Emerging Evidence',
    color: 'var(--strength-2)',
    icon: Star,
    description: 'Initial evidence, needs further validation'
  }
}

/**
 * Inline style for a chip tinted with `color` (any CSS colour, including var(--token)).
 * The text is mixed toward the theme foreground so it stays WCAG AA on the tint in
 * light and dark mode (#320).
 */
export function tintedChipStyle(color: string): Record<string, string> {
  return {
    backgroundColor: `color-mix(in srgb, ${color} 12.5%, transparent)`,
    color: `color-mix(in oklab, ${color} 45%, var(--foreground))`,
    borderColor: `color-mix(in srgb, ${color} 25%, transparent)`
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
      color: 'var(--muted-foreground)',
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
      color: 'var(--muted-foreground)',
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

/** ClinGen / GenCC classification shown as a strength step, or as a warning/danger tone */
export interface ClassificationConfig {
  label: string
  /** Strength step 1-5; null for Disputed/Refuted/unknown, which are not strengths */
  strength: 1 | 2 | 3 | 4 | 5 | null
  tone: 'strength' | 'warning' | 'danger' | 'neutral'
  color: string
  /** Non-colour cue: the icon of the tier with the same strength step */
  icon: Component
  description: string
}

const STRENGTH_ICONS = [Info, CircleAlert, Check, CircleCheckBig, CircleCheck]

const classification = (
  label: string,
  strength: ClassificationConfig['strength'],
  description: string,
  tone: ClassificationConfig['tone'] = 'strength'
): ClassificationConfig => ({
  label,
  strength,
  tone,
  color: strength ? `var(--strength-${strength})` : `var(--${tone})`,
  icon: strength ? STRENGTH_ICONS[strength - 1]! : tone === 'danger' ? CircleX : TriangleAlert,
  description
})

/** Keys are lower-case with spaces; look up through getClassificationConfig() */
export const CLASSIFICATION_CONFIG: Record<string, ClassificationConfig> = {
  definitive: classification(
    'Definitive',
    5,
    'Gene-disease relationship replicated and upheld over time; the strongest classification'
  ),
  strong: classification(
    'Strong',
    4,
    'Strong genetic and experimental evidence, not yet replicated over time'
  ),
  moderate: classification(
    'Moderate',
    3,
    'Moderate evidence: several unrelated cases with supporting experimental data'
  ),
  limited: classification(
    'Limited',
    2,
    'Limited evidence: few cases or little experimental support; the relationship is unproven'
  ),
  supportive: classification(
    'Supportive',
    2,
    'Reported as supportive by a submitter without a full semiquantitative assessment'
  ),
  'no known disease relationship': classification(
    'No Known Disease Relationship',
    1,
    'No evidence of a gene-disease relationship has been reported'
  ),
  'animal model only': classification(
    'Animal Model Only',
    1,
    'Evidence comes from animal models only; no human cases reported'
  ),
  disputed: classification(
    'Disputed',
    null,
    'Conflicting evidence disputes the gene-disease relationship',
    'warning'
  ),
  refuted: classification(
    'Refuted',
    null,
    'Evidence refuting the relationship significantly outweighs any support',
    'danger'
  )
}

/**
 * Classification config for a ClinGen/GenCC label ("Definitive", "No Known Disease
 * Relationship", "disputed evidence", ...). Unknown labels render neutral.
 */
export function getClassificationConfig(label: string | null | undefined): ClassificationConfig {
  const key = (label ?? '')
    .toLowerCase()
    .replace(/[_-]+/g, ' ')
    .replace(/\s+evidence$/, '')
    .trim()
  return (
    CLASSIFICATION_CONFIG[key] ?? {
      label: label || 'No Classification',
      strength: null,
      tone: 'neutral',
      color: 'var(--muted-foreground)',
      icon: CircleHelp,
      description: 'No classification assigned'
    }
  )
}
