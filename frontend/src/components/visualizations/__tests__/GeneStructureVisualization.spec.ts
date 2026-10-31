/**
 * Gene structure plot: reserved height (no layout shift), strand-aware exon numbering,
 * stacked lollipops with pathogenic on top, splice diamonds, and keyboard-reachable markers.
 */
import { describe, it, expect, vi, beforeAll, afterAll, afterEach } from 'vitest'
import { flushPromises, mount } from '@vue/test-utils'
import type { VueWrapper } from '@vue/test-utils'
import GeneStructureVisualization from '../GeneStructureVisualization.vue'

vi.stubGlobal(
  'ResizeObserver',
  class {
    observe() {}
    unobserve() {}
    disconnect() {}
  }
)

// jsdom has no layout; give the plot a real width so it draws
const width = Object.getOwnPropertyDescriptor(HTMLElement.prototype, 'clientWidth')
beforeAll(() => {
  Object.defineProperty(HTMLElement.prototype, 'clientWidth', {
    configurable: true,
    get: () => 1000
  })
})
afterAll(() => {
  if (width) Object.defineProperty(HTMLElement.prototype, 'clientWidth', width)
})

let wrapper: VueWrapper | undefined
afterEach(() => {
  wrapper?.unmount()
  wrapper = undefined
  document.body.innerHTML = ''
})

const ensembl = (strand: string) => ({
  chromosome: '17',
  start: 1000,
  end: 11000,
  strand,
  assembly: 'GRCh38',
  canonical_transcript: {
    transcript_id: 'ENST00000000001',
    display_name: 'GENE-201',
    exons: [
      { exon_id: 'E3', start: 9000, end: 11000, length: 2001 },
      { exon_id: 'E1', start: 1000, end: 1100, length: 101 },
      { exon_id: 'E2', start: 5000, end: 5050, length: 51 }
    ]
  }
})

const variant = (pos: number, category: string, extra = {}) => ({
  genomic_start: pos,
  category,
  classification: category,
  effect_category: 'missense',
  protein_change: `p.X${pos}`,
  molecular_consequences: ['missense variant'],
  ...extra
})

async function render(strand = '-', variants = [] as object[]) {
  wrapper = mount(GeneStructureVisualization, {
    props: {
      geneSymbol: 'GENE',
      ensemblData: ensembl(strand),
      clinvarData: variants.length ? { genomic_variants: variants } : null
    },
    attachTo: document.body
  })
  await flushPromises()
  return wrapper
}

const ty = (el: Element) =>
  Number(/translate\([^,]+,([^)]+)\)/.exec(el.getAttribute('transform')!)![1])

describe('GeneStructureVisualization', () => {
  it('reserves its final height before drawing and names the figure', async () => {
    const w = await render('-', [variant(5020, 'pathogenic')])
    const container = w.get('.chart-container').element as HTMLElement
    const svg = w.get('.chart-container svg')
    expect(container.style.height).toBe(`${svg.attributes('height')}px`)
    expect(svg.find('title').text()).toContain('GENE gene structure')
    expect(svg.find('desc').text()).toMatch(/3 exons on the reverse strand/)
    expect(svg.find('desc').text()).toMatch(/1 of 1 loaded ClinVar variants/)
  })

  it('numbers exons in transcript order, reversed on the minus strand', async () => {
    const labels = async (strand: string) => {
      const w = await render(strand)
      const out = w
        .findAll('text')
        .filter(t => /^\d+$/.test(t.text()) && t.element.closest('[clip-path]'))
        .map(t => [Number(t.attributes('x')), t.text()] as const)
        .sort((a, b) => a[0] - b[0])
        .map(([, label]) => label)
      w.unmount()
      return out
    }
    expect(await labels('-')).toEqual(['3', '2', '1'])
    expect(await labels('+')).toEqual(['1', '2', '3'])
  })

  it('stacks nearby markers, draws pathogenic last and shapes splice variants as diamonds', async () => {
    const w = await render('+', [
      variant(5010, 'pathogenic'),
      variant(5011, 'likely_pathogenic', {
        effect_category: 'truncating',
        molecular_consequences: ['splice donor variant']
      }),
      variant(9500, 'pathogenic')
    ])
    const markers = w.findAll('.variant-marker').map(m => m.element)
    expect(markers).toHaveLength(3)
    const near = markers.filter(m => /p\.X501[01]/.test(m.getAttribute('aria-label')!))
    expect(ty(near[0]!)).not.toBe(ty(near[1]!))
    expect(markers.at(-1)!.getAttribute('aria-label')).toMatch(/^p\.X(5010|9500), Pathogenic/)
    expect(w.findAll('.variant-marker.splice')).toHaveLength(1)
  })

  it('has one tab stop, moves with arrow keys and pins details on Enter', async () => {
    const w = await render('+', [variant(2000, 'pathogenic'), variant(8000, 'pathogenic')])
    const markers = w.findAll('.variant-marker')
    expect(markers.map(m => m.attributes('tabindex')).sort()).toEqual(['-1', '0'])
    const first = markers.find(m => m.attributes('tabindex') === '0')!
    expect(first.attributes('role')).toBe('button')

    first.element.dispatchEvent(new window.KeyboardEvent('keydown', { key: 'ArrowRight' }))
    expect(document.activeElement?.getAttribute('aria-label')).toMatch(/^p\.X8000/)

    document.activeElement!.dispatchEvent(new window.KeyboardEvent('keydown', { key: 'Enter' }))
    expect(document.querySelector('.visualization-tooltip')?.textContent).toContain('p.X8000')
  })
})
