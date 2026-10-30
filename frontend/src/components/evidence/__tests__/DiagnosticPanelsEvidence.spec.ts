/**
 * Diagnostic panels card body: grouped by laboratory with scrape provenance from the
 * provider registry, which only enhances the card (loading/error/missing lab degrade to text).
 */

import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest'
import { flushPromises, mount } from '@vue/test-utils'
import { h } from 'vue'
import { createMemoryHistory, createRouter } from 'vue-router'
import { TooltipProvider } from '@/components/ui/tooltip'

vi.mock('@/api/datasources', () => ({
  datasourceApi: { getDiagnosticPanelsProviders: vi.fn() }
}))

import { datasourceApi, type DiagnosticPanelsProvider } from '@/api/datasources'
import DiagnosticPanelsEvidence from '@/components/evidence/DiagnosticPanelsEvidence.vue'
import EvidenceCard from '@/components/evidence/EvidenceCard.vue'

const getProviders = vi.mocked(datasourceApi.getDiagnosticPanelsProviders)

const provider = (
  provider_name: string,
  scraped_at: string | null,
  extra: Partial<DiagnosticPanelsProvider> = {}
): DiagnosticPanelsProvider => ({
  provider_name,
  main_url: `https://${provider_name.toLowerCase()}.example`,
  scraped_at,
  scraper_version: '1.4.0',
  panels: [],
  gene_count: null,
  uploaded_at: '2026-09-01T10:00:00Z',
  ...extra
})

const REGISTRY = [
  provider('Natera', '2026-08-24T00:00:00Z', {
    panels: [{ name: 'Renasight', url: 'https://natera.example/renasight', gene_count: 385 }]
  }),
  provider('Centogene_AG', '2025-08-24T00:00:00Z', {
    scraper_version: '1.3.2',
    uploaded_at: '2026-10-01T10:00:00Z'
  })
]

const router = () =>
  createRouter({
    history: createMemoryHistory(),
    routes: [{ path: '/data-sources', name: 'data-sources', component: { render: () => null } }]
  })

async function render(evidenceData: object) {
  const w = mount(
    { render: () => h(TooltipProvider, () => h(DiagnosticPanelsEvidence, { evidenceData })) },
    { global: { plugins: [router()] } }
  )
  await flushPromises()
  return w
}

type Wrapper = Awaited<ReturnType<typeof render>>
const labRows = (w: Wrapper) => w.findAll('[data-testid="lab"]')
// Visible words with element boundaries as spaces (wrapper.text() glues sibling elements)
const words = (w: { html: () => string }) =>
  w
    .html()
    .replace(/<!--[\s\S]*?-->/g, '')
    .replace(/<[^>]*>/g, ' ')
    .replace(/&amp;/g, '&')
    .replace(/\s+/g, ' ')
    .trim()

beforeEach(() => {
  vi.useFakeTimers({ toFake: ['Date'] })
  vi.setSystemTime(new Date('2026-08-24T12:00:00Z'))
  getProviders.mockReset().mockResolvedValue(REGISTRY)
})
afterEach(() => vi.useRealTimers())

describe('DiagnosticPanelsEvidence grouped by laboratory', () => {
  const data = {
    provider_panels: {
      Natera: ['Renasight'],
      Centogene_AG: ['CentoNephro'],
      'Seeded from 9 files': ['X']
    }
  }

  it('lists labs by name with their panels, links and capture dates', async () => {
    const w = await render(data)
    const rows = labRows(w)
    expect(rows.map(r => r.find('a').text())).toEqual([
      'Centogene AG (opens in a new tab)',
      'Natera (opens in a new tab)'
    ])
    const natera = rows[1]!
    const labLink = natera.get('a[href="https://natera.example"]')
    expect(labLink.attributes('target')).toBe('_blank')
    expect(labLink.attributes('rel')).toBe('noopener noreferrer')
    expect(labLink.get('.sr-only').text()).toBe('(opens in a new tab)')
    expect(natera.get('time').attributes('datetime')).toBe('2026-08-24T00:00:00.000Z')
    expect(natera.get('time').text()).toBe('24 Aug 2026')
    expect(natera.get('a[href="https://natera.example/renasight"]').text()).toContain('Renasight')
    // No registry URL for this panel: plain text
    expect(rows[0]!.findAll('ul li a')).toHaveLength(0)
    expect(w.text()).not.toContain('Seeded from')
  })

  it('flags a capture more than 12 months old, not one exactly 12 months old', async () => {
    vi.setSystemTime(new Date('2026-08-24T00:00:00Z'))
    let rows = labRows(await render(data))
    expect(rows[0]!.text()).not.toContain('Over a year old')

    vi.setSystemTime(new Date('2026-08-24T00:00:01Z'))
    rows = labRows(await render(data))
    const chip = rows[0]!.get('[data-slot="chip"]')
    expect(chip.text()).toBe('Over a year old')
    expect(rows[1]!.find('[data-slot="chip"]').exists()).toBe(false)
  })

  it('collapses labs and panels beyond three with aria-expanded buttons', async () => {
    const many = Object.fromEntries(
      ['A', 'B', 'C', 'D', 'E'].map(l => [`Lab ${l}`, ['p1', 'p2', 'p3', 'p4', 'p5']])
    )
    const w = await render({ provider_panels: many })
    expect(labRows(w)).toHaveLength(3)
    const showLabs = w.findAll('button').find(b => b.text() === 'Show all 5 laboratories')!
    expect(showLabs.attributes('aria-expanded')).toBe('false')
    await showLabs.trigger('click')
    expect(labRows(w)).toHaveLength(5)
    expect(showLabs.attributes('aria-expanded')).toBe('true')
    expect(showLabs.text()).toBe('Show fewer')

    const more = labRows(w)[0]!.get('button')
    expect(labRows(w)[0]!.findAll('ul li')).toHaveLength(3)
    expect(more.text()).toBe('+2 more')
    expect(more.attributes('aria-expanded')).toBe('false')
    await more.trigger('click')
    expect(labRows(w)[0]!.findAll('ul li')).toHaveLength(5)
    expect(more.attributes('aria-expanded')).toBe('true')
    expect(more.text()).toBe('Show fewer')
  })

  it('shows provenance in the footer with a link to the method', async () => {
    const footer = (await render(data)).get('[data-testid="panels-provenance"]')
    expect(words(footer)).toBe(
      'Panel lists from laboratory test catalogues · KGDB import 1.3.2, 1.4.0 · uploaded 1 Oct 2026 Sources & method'
    )
    expect(footer.get('a').attributes('href')).toBe('/data-sources')
  })

  it('renders a lab missing from the registry as plain text without date or chip', async () => {
    const rows = labRows(await render({ provider_panels: { Unknown_Lab: ['P'] } }))
    expect(rows[0]!.find('a').exists()).toBe(false)
    expect(rows[0]!.find('time').exists()).toBe(false)
    expect(rows[0]!.find('[data-slot="chip"]').exists()).toBe(false)
    expect(words(rows[0]!)).toBe('Unknown Lab P')
  })

  it('renders labs and panels without links or dates while loading, reserving the date column', async () => {
    getProviders.mockReturnValue(new Promise(() => {}))
    const w = await render(data)
    expect(labRows(w)).toHaveLength(2)
    expect(w.findAll('[data-testid="lab"] a')).toHaveLength(0)
    expect(w.find('time').exists()).toBe(false)
    expect(w.findAll('[data-testid="lab"] .min-w-24')).toHaveLength(2)
  })

  it('degrades to plain text without an error message when the registry fails', async () => {
    getProviders.mockRejectedValue(new Error('offline'))
    const w = await render(data)
    expect(labRows(w).map(words)).toEqual(['Centogene AG CentoNephro', 'Natera Renasight'])
    expect(w.find('[data-testid="lab"] a').exists()).toBe(false)
    expect(w.text()).not.toMatch(/error|failed/i)
    expect(words(w.get('[data-testid="panels-provenance"]'))).toBe(
      'Panel lists from laboratory test catalogues Sources & method'
    )
  })
})

describe('DiagnosticPanelsEvidence legacy evidence', () => {
  const headings = async (data: object) =>
    (await render(data)).findAll('[data-slot="evidence-list"]').map(
      s =>
        s.find('h4').text() +
        ': ' +
        s
          .findAll('li')
          .map(li => li.text())
          .join(', ')
    )

  it('names the labs beside the panels and hides ingestion labels', async () => {
    expect(
      await headings({
        panels: ['Renasight', 'CentoNephro'],
        providers: ['Natera', 'Seeded from 9 files', 'Centogene_AG']
      })
    ).toEqual(['Panels: CentoNephro, Renasight', 'Laboratories: Centogene AG, Natera'])
  })

  it('uses the singular and omits the list when there is no real lab', async () => {
    expect(await headings({ panels: ['A'], providers: ['Natera'] })).toEqual([
      'Panels: A',
      'Laboratory: Natera'
    ])
    expect(await headings({ panels: ['A'], providers: ['Seeded from 9 files'] })).toEqual([
      'Panels: A'
    ])
  })

  it('keeps the footer provenance for labs found in the registry', async () => {
    const footer = (await render({ panels: ['A'], providers: ['Natera'] })).get(
      '[data-testid="panels-provenance"]'
    )
    expect(footer.text()).toContain('KGDB import 1.4.0')
  })
})

describe('EvidenceCard stat row for diagnostic panels', () => {
  const card = async (evidence_data: object) => {
    const w = mount(
      {
        render: () =>
          h(TooltipProvider, () =>
            h(EvidenceCard, {
              gene: { approved_symbol: 'PKD1' },
              evidence: { source_name: 'DiagnosticPanels', evidence_data }
            })
          )
      },
      { global: { plugins: [router()] } }
    )
    await flushPromises()
    return words(w.get('[data-testid="evidence-stats"]'))
  }

  it('shows labs, (lab, panel) pairs and the capture range', async () => {
    expect(
      await card({ provider_panels: { Natera: ['Renasight'], Centogene_AG: ['A', 'B'] } })
    ).toBe('2 laboratories 3 panels captured 24 Aug 2025 – 24 Aug 2026')
  })

  it('shows one date when captured the same day, and none without the registry', async () => {
    expect(await card({ provider_panels: { Natera: ['Renasight'] } })).toBe(
      '1 laboratory 1 panel captured 24 Aug 2026'
    )
    getProviders.mockRejectedValue(new Error('offline'))
    expect(await card({ provider_panels: { Natera: ['Renasight'] } })).toBe('1 laboratory 1 panel')
  })
})
