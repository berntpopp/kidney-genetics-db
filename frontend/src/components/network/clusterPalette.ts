/**
 * Cluster colours for the network graph, its legend and the cluster dialog. Okabe-Ito
 * (--source-1..7) has only 7 hues, so a 22-cluster run left 15 clusters the same grey. This
 * uses Paul Tol's colour-blind-considerate "muted" scheme (9 hues) plus orange, blue and pear
 * from his vibrant/bright/light schemes: 12 hues by size rank (0 = largest). Ranks 12-23 reuse
 * the hues with a diamond node shape, so every cluster keeps its own colour+shape pair; only
 * clusters below the minimum cluster size are neutral grey. Light fills keep >= 3:1 against
 * the canvas through markOutline() (chartMarks.ts). Resolve with canvasColor() for Cytoscape.
 */
import { OTHER_CLUSTER_COLOR } from '@/config/networkAnalysis'

// Theme tokens (main.css --cluster-1..12): dark mode lifts the indigo and wine hues
export const CLUSTER_PALETTE = Array.from({ length: 12 }, (_, i) => `var(--cluster-${i + 1})`)

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
