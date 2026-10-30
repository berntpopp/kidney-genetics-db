/**
 * Cluster colours for the network graph, its legend and the cluster dialog. Okabe-Ito
 * (--source-1..7) has only 7 hues, so a 22-cluster run left 15 clusters the same grey. This
 * uses Paul Tol's colour-blind-considerate "muted" scheme (9 hues) plus orange, blue and pear
 * from his vibrant/bright/light schemes: 12 hues by size rank (0 = largest). Ranks 12-23 reuse
 * the hues with a diamond node shape, so every cluster keeps its own colour+shape pair; only
 * clusters below the minimum cluster size are neutral grey. Light fills keep >= 3:1 against
 * the canvas through markOutline() (chartMarks.ts). Resolve with canvasColor() for Cytoscape.
 * Written in oklch like the main.css tokens; the comments give Tol's published sRGB values.
 */
import { OTHER_CLUSTER_COLOR } from '@/config/networkAnalysis'

// ponytail: same values in both themes; move to main.css tokens if dark mode needs its own
export const CLUSTER_PALETTE = [
  'oklch(0.635 0.13 11)', // rose CC6677
  'oklch(0.347 0.159 281.8)', // indigo 332288
  'oklch(0.841 0.108 98.3)', // sand DDCC77
  'oklch(0.499 0.135 148.6)', // green 117733
  'oklch(0.812 0.084 230.8)', // cyan 88CCEE
  'oklch(0.432 0.145 354.5)', // wine 882255
  'oklch(0.674 0.098 180.4)', // teal 44AA99
  'oklch(0.663 0.123 109.3)', // olive 999933
  'oklch(0.553 0.167 334.6)', // purple AA4499
  'oklch(0.697 0.167 47)', // orange EE7733
  'oklch(0.556 0.097 250)', // blue 4477AA
  'oklch(0.806 0.168 115.9)' // pear BBCC33
] as const

export type ClusterShape = 'ellipse' | 'round-diamond'

export interface ClusterStyle {
  color: string
  shape: ClusterShape
}

export const SMALL_CLUSTER_STYLE: ClusterStyle = { color: OTHER_CLUSTER_COLOR, shape: 'ellipse' }

export function clusterStyle(rank: number, size: number, minSize = 1): ClusterStyle {
  if (size < minSize || rank < 0) return SMALL_CLUSTER_STYLE
  const n = CLUSTER_PALETTE.length
  // ponytail: beyond 24 clusters colour+shape pairs repeat; add a third shape if that happens
  return {
    color: CLUSTER_PALETTE[rank % n]!,
    shape: Math.floor(rank / n) % 2 === 0 ? 'ellipse' : 'round-diamond'
  }
}
