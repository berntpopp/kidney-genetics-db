import { extractCombinations } from '@upsetjs/bundle'

/** One exclusive intersection as returned by /api/statistics/source-overlaps */
export interface OverlapIntersection {
  sets: string[]
  size: number
}

/** Bars drawn; more than this makes the bar labels overlap at desktop widths */
export const UPSET_COMBINATION_LIMIT = 30

/**
 * Build UpSet.js sets and combinations from the API's exclusive intersections.
 * The API counts each gene once, under exactly its sources, so the chart must use
 * distinct intersections to show the same numbers as the API and the mobile table (#315).
 */
export function buildUpSetCombinations(intersections: OverlapIntersection[]) {
  // The API has counts, not gene lists: one placeholder element per gene
  const elements = intersections.flatMap(({ sets, size }) =>
    Array.from({ length: size || 0 }, () => ({ sets: [...sets] }))
  )
  return extractCombinations(elements, {
    type: 'distinctIntersection',
    setOrder: 'cardinality:desc',
    combinationOrder: 'cardinality:desc',
    combinationLimit: UPSET_COMBINATION_LIMIT
  })
}
