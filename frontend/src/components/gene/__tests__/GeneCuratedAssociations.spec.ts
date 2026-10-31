import { describe, it, expect, vi } from 'vitest'
import { flushPromises, mount } from '@vue/test-utils'
import { createRouter, createMemoryHistory } from 'vue-router'
import { h } from 'vue'
import { TooltipProvider } from '@/components/ui/tooltip'

vi.stubGlobal('logService', { info: vi.fn(), warn: vi.fn(), error: vi.fn(), debug: vi.fn() })
import type { Association } from '@/api/curation'
import GeneCuratedAssociations from '@/components/gene/GeneCuratedAssociations.vue'

const RECORD = {
  id: 1,
  gene_id: 1,
  gene_symbol: 'PKD1',
  disease_id: 'MONDO:0008263',
  disease_name: 'polycystic kidney disease 1',
  evidence_strength: 'Definitive',
  citations: ['PMID:8004675'],
  evidence_summary: 'Segregation in many families.',
  status: 'published',
  curator_id: 1,
  reviewer_id: 2,
  created_at: '2026-10-01T00:00:00Z',
  updated_at: '2026-10-02T00:00:00Z',
  submitted_at: '2026-10-01T00:00:00Z',
  reviewed_at: '2026-10-02T00:00:00Z',
  published_at: '2026-10-02T00:00:00Z'
} as Association

async function mountFor(records: Association[]) {
  const router = createRouter({
    history: createMemoryHistory(),
    routes: [{ path: '/:rest(.*)', component: { render: () => null } }]
  })
  const w = mount(
    { render: () => h(TooltipProvider, () => h(GeneCuratedAssociations, { records })) },
    { global: { plugins: [router] } }
  )
  await flushPromises()
  return w
}

describe('GeneCuratedAssociations', () => {
  it("lists the gene's published records with outbound links", async () => {
    const w = await mountFor([RECORD])

    expect(w.text()).toContain('Definitive')
    expect(w.text()).toContain('Segregation in many families.')
    const hrefs = w.findAll('a').map(a => a.attributes('href'))
    expect(hrefs).toContain('https://monarchinitiative.org/MONDO:0008263')
    expect(hrefs).toContain('https://pubmed.ncbi.nlm.nih.gov/8004675/')
  })

  it('lists susceptibility records separately and never as a Mendelian strength', async () => {
    const risk = {
      ...RECORD,
      id: 2,
      relationship_type: 'susceptibility',
      evidence_strength: 'Likely association'
    } as Association
    const w = await mountFor([{ ...RECORD, relationship_type: 'mendelian' } as Association, risk])
    const mendelian = w.find('[data-testid="gda-mendelian"]')
    const susceptibility = w.find('[data-testid="gda-susceptibility"]')
    expect(mendelian.text()).toContain('Definitive')
    expect(mendelian.text()).not.toContain('Likely association')
    expect(susceptibility.text()).toContain('Susceptibility')
    expect(susceptibility.text()).toContain('Likely association')
  })

  it('renders a refuted association muted with a cross icon, not as a risk', async () => {
    const refuted = {
      ...RECORD,
      relationship_type: 'susceptibility',
      evidence_strength: 'Refuted association'
    } as Association
    const w = await mountFor([refuted])
    const chip = w.findAll('[data-slot="chip"]').find(c => c.text() === 'Refuted association')!
    expect(chip.classes()).toEqual(
      expect.arrayContaining(['text-muted-foreground', 'line-through'])
    )
    expect(chip.find('svg').exists()).toBe(true)
  })

  // A failed request is GeneDetail's concern now (it fetches the records): see GeneDetail.spec.ts
  it('renders nothing without records', async () => {
    expect((await mountFor([])).html()).not.toContain('Expert-reviewed')
  })
})
