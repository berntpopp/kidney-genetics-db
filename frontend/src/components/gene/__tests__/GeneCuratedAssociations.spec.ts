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
    // Citations and the publication date are labelled rows alongside methodology and provenance
    const rows = Object.fromEntries(
      w.findAll('dt').map(dt => [dt.text(), dt.element.nextElementSibling?.textContent?.trim()])
    )
    expect(rows['Citations']).toContain('PMID:8004675')
    expect(rows['Published']).toBe('2026-10-02')
  })

  it('keeps summary paragraphs and leaves out an empty citation row', async () => {
    const summary =
      "Adopted the GCEP call.\n\nCurator's call overrides the point model (computed: Strong): x"
    const w = await mountFor([{ ...RECORD, citations: [], evidence_summary: summary }])
    const p = w.findAll('p').find(p => p.text().startsWith('Adopted the GCEP call.'))!
    expect(p.element.textContent?.trim()).toBe(summary)
    expect(p.classes()).toContain('whitespace-pre-line')
    expect(w.findAll('dt').map(dt => dt.text())).not.toContain('Citations')
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

  it('notes a modest effect next to a susceptibility class only when OR < 2 (#482)', async () => {
    const risk = (id: number, odds_ratio: number) =>
      ({
        ...RECORD,
        id,
        relationship_type: 'susceptibility',
        evidence_strength: 'Likely association',
        odds_ratio
      }) as Association
    const notes = async (r: Association) =>
      (await mountFor([r])).findAll('[data-testid="or-note"]').map(n => n.text())
    expect(await notes(risk(1, 1.6))).toEqual(['OR 1.6 < 2: modest effect'])
    expect(await notes(risk(2, 2.4))).toEqual([])
    expect(await notes({ ...RECORD, odds_ratio: 1.6 } as Association)).toEqual([])
  })

  describe('several associations (#539)', () => {
    const entity = (id: number, o: Partial<Association>) =>
      ({ ...RECORD, id, gene_symbol: 'CASR', relationship_type: 'mendelian', ...o }) as Association
    const ADH1 = entity(1, {
      disease_id: 'MONDO:0011013',
      disease_name: 'autosomal dominant hypocalcemia 1',
      moi: 'HP:0000006'
    })
    const FHH1 = entity(2, {
      disease_id: 'MONDO:0007791',
      disease_name: 'familial hypocalciuric hypercalcemia 1',
      moi: 'HP:0000006'
    })
    const NSHPT = entity(3, {
      disease_id: 'MONDO:0009397',
      disease_name: 'neonatal severe primary hyperparathyroidism',
      moi: 'HP:0000007',
      evidence_strength: 'Strong'
    })
    const overviewRows = (w: Awaited<ReturnType<typeof mountFor>>) =>
      w.findAll('[data-testid="gda-overview-row"]').map(r => r.text())

    it('keeps a single association without count or overview', async () => {
      const w = await mountFor([RECORD])
      expect(w.find('[data-testid="gda-count"]').exists()).toBe(false)
      expect(w.find('[data-testid="gda-overview"]').exists()).toBe(false)
      expect(w.find('h4').text()).toContain('polycystic kidney disease 1')
    })

    it('counts two associations and says different classes are not a conflict', async () => {
      const w = await mountFor([NSHPT, FHH1])
      expect(w.find('[data-testid="gda-count"]').text()).toBe('· 2')
      expect(w.find('caption').text()).toContain('not a conflict')
      // Strongest first, whatever order the API sent
      expect(overviewRows(w)[0]).toContain('familial hypocalciuric hypercalcemia 1')
      expect(overviewRows(w)[1]).toContain('Strong')
    })

    it('gives 3+ associations one overview row each, linked to a record headed by its disease', async () => {
      const w = await mountFor([NSHPT, FHH1, ADH1])
      expect(w.find('[data-testid="gda-count"]').text()).toBe('· 3')
      expect(overviewRows(w)).toHaveLength(3)
      // Same class: disease name decides the order, never the MONDO number
      expect(overviewRows(w)[0]).toContain('autosomal dominant hypocalcemia 1')
      for (const link of w.findAll('[data-testid="gda-overview-row"] a[href^="#gda-"]'))
        expect(w.find(link.attributes('href')!).find('h4').text()).toContain(link.text())
      expect(w.findAll('li h4').map(h => h.text().split('MONDO')[0])).toEqual([
        'autosomal dominant hypocalcemia 1',
        'familial hypocalciuric hypercalcemia 1',
        'neonatal severe primary hyperparathyroidism'
      ])
    })

    it('shows a Mendelian and a susceptibility association apart, with their type', async () => {
      const risk = entity(4, {
        gene_symbol: 'CFH',
        disease_id: 'MONDO:0016244',
        disease_name: 'atypical hemolytic-uremic syndrome',
        relationship_type: 'susceptibility',
        evidence_strength: 'Likely association',
        risk_allele: 'CFH-H3 haplotype'
      })
      const w = await mountFor([
        risk,
        { ...ADH1, disease_name: 'atypical hemolytic-uremic syndrome' }
      ])
      const rows = overviewRows(w)
      expect(rows[0]).toContain('Definitive')
      expect(rows[0]).toContain('Mendelian')
      expect(rows[1]).toContain('Likely association')
      expect(rows[1]).toContain('Susceptibility')
      expect(w.find('[data-testid="gda-mendelian"]').text()).not.toContain('Likely association')
      expect(w.find('[data-testid="gda-susceptibility"]').text()).toContain('CFH-H3 haplotype')
    })

    it('says when a risk allele is shared with another gene, so it is counted once', async () => {
      const cfhr3 = entity(5, {
        gene_symbol: 'CFHR3',
        relationship_type: 'susceptibility',
        evidence_strength: 'Uncertain association',
        risk_allele: 'CFHR3-CFHR1 deletion',
        shared_risk_allele_genes: ['CFHR1']
      })
      const w = await mountFor([cfhr3])
      const record = w.find('[data-testid="gda-susceptibility"]')
      expect(record.text()).toContain('shared evidence, count it once')
      expect(record.find('a[href="/curation/associations/CFHR1"]').text()).toBe('CFHR1')
    })
  })

  // A failed request is GeneDetail's concern now (it fetches the records): see GeneDetail.spec.ts
  it('renders nothing without records', async () => {
    expect((await mountFor([])).html()).not.toContain('Expert-reviewed')
  })
})
