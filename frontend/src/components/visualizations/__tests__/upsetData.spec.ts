import { describe, it, expect } from 'vitest'
import { buildUpSetCombinations, UPSET_COMBINATION_LIMIT } from '../upsetData'

const cardinalityOf = (combinations: { sets: Set<{ name: string }>; cardinality: number }[]) =>
  Object.fromEntries(
    combinations.map(c => [
      [...c.sets]
        .map(s => s.name)
        .sort()
        .join('&'),
      c.cardinality
    ])
  )

describe('buildUpSetCombinations (#315)', () => {
  it('reports the exclusive API counts, not inclusive intersections', () => {
    // Inclusive counting would give A=5 and B=3; the API counts A-only=3, A&B=2, B-only=1
    const { combinations } = buildUpSetCombinations([
      { sets: ['A'], size: 3 },
      { sets: ['A', 'B'], size: 2 },
      { sets: ['B'], size: 1 }
    ])
    expect(cardinalityOf(combinations as never)).toEqual({ A: 3, 'A&B': 2, B: 1 })
  })

  it('keeps only the largest combinations so bar labels do not overlap', () => {
    const intersections = Array.from({ length: UPSET_COMBINATION_LIMIT + 5 }, (_, i) => ({
      sets: [`S${i}`],
      size: i + 1
    }))
    const { combinations } = buildUpSetCombinations(intersections)
    expect(combinations).toHaveLength(UPSET_COMBINATION_LIMIT)
    expect(combinations[0]?.cardinality).toBe(UPSET_COMBINATION_LIMIT + 5)
  })
})
