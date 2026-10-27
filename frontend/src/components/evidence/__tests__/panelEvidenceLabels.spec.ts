/**
 * PanelApp inheritance reads as words, not API strings, and diagnostic panels name
 * their laboratories (#423).
 */

import { describe, it, expect } from 'vitest'
import { mount } from '@vue/test-utils'
import { h, type Component } from 'vue'
import { TooltipProvider } from '@/components/ui/tooltip'
import PanelAppEvidence from '@/components/evidence/PanelAppEvidence.vue'
import DiagnosticPanelsEvidence from '@/components/evidence/DiagnosticPanelsEvidence.vue'

const render = (component: Component, evidenceData: object) =>
  mount({ render: () => h(TooltipProvider, () => h(component, { evidenceData })) })

describe('PanelApp mode of inheritance', () => {
  it('maps PanelApp values to readable labels and keeps the raw value as the tooltip', () => {
    const raw = [
      'MONOALLELIC, autosomal or pseudoautosomal, NOT imprinted',
      'BIALLELIC, autosomal or pseudoautosomal',
      'X-LINKED: hemizygous mutation in males, biallelic mutations in females',
      'Something new from PanelApp'
    ]
    const items = render(PanelAppEvidence, { modes_of_inheritance: raw }).findAll('section li')
    expect(items.map(li => li.text())).toEqual([
      'Autosomal dominant (monoallelic)',
      'Autosomal recessive (biallelic)',
      'X-linked recessive',
      'Something new from PanelApp'
    ])
    expect(items.map(li => li.attributes('title'))).toEqual(raw)
  })
})

describe('Diagnostic panels laboratories', () => {
  const headings = (data: object) =>
    render(DiagnosticPanelsEvidence, data)
      .findAll('[data-slot="evidence-list"]')
      .map(
        s =>
          s.find('h4').text() +
          ': ' +
          s
            .findAll('li')
            .map(li => li.text())
            .join(', ')
      )

  it('names the labs beside the panels and hides ingestion labels', () => {
    expect(
      headings({
        panels: ['Renasight', 'CentoNephro'],
        providers: ['Natera', 'Seeded from 9 files', 'Centogene_AG']
      })
    ).toEqual(['Panels: CentoNephro, Renasight', 'Laboratories: Centogene AG, Natera'])
  })

  it('uses the singular and omits the list when there is no real lab', () => {
    expect(headings({ panels: ['A'], providers: ['Natera'] })).toEqual([
      'Panels: A',
      'Laboratory: Natera'
    ])
    expect(headings({ panels: ['A'], providers: ['Seeded from 9 files'] })).toEqual(['Panels: A'])
  })
})
