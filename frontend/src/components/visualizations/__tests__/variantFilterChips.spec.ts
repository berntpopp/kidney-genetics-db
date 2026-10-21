/**
 * Variant filter chips on /genes/:symbol/structure failed WCAG AA (#320): raw 500-700
 * hex text at opacity 0.7, and white text on yellow/orange fills. They must use
 * tintedChipStyle, which mixes the text toward the theme foreground.
 */
import { describe, it, expect } from 'vitest'
import structureSrc from '../GeneStructureVisualization.vue?raw'
import domainSrc from '../ProteinDomainVisualization.vue?raw'

// Each toggle chip is a <Badge ... :aria-pressed ...> element.
const chips = (src: string) => [...src.matchAll(/<Badge\b[^>]*:aria-pressed[^>]*>/g)].map(m => m[0])

describe.each([
  ['GeneStructureVisualization', structureSrc],
  ['ProteinDomainVisualization', domainSrc]
])('%s filter chips (#320)', (_name, src) => {
  it('has toggle chips', () => {
    expect(chips(src).length).toBeGreaterThanOrEqual(2)
  })

  it.each([0, 1])('chip %i derives text colour from tintedChipStyle', i => {
    const chip = chips(src)[i]
    expect(chip).toContain('tintedChipStyle(')
    expect(chip).not.toMatch(/opacity/)
    expect(chip).not.toMatch(/color:\s*'white'/)
  })
})
