/**
 * PanelApp inheritance reads as words, not API strings (#423). Diagnostic panels are
 * covered in DiagnosticPanelsEvidence.spec.ts.
 */

import { describe, it, expect } from 'vitest'
import { mount } from '@vue/test-utils'
import { h, type Component } from 'vue'
import { TooltipProvider } from '@/components/ui/tooltip'
import PanelAppEvidence from '@/components/evidence/PanelAppEvidence.vue'

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
