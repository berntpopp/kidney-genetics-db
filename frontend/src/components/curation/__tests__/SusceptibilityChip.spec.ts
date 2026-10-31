import { describe, it, expect } from 'vitest'
import { mount } from '@vue/test-utils'
import { h } from 'vue'
import { TooltipProvider } from '@/components/ui/tooltip'
import { Chip } from '@/components/shared'
import SusceptibilityChip from '@/components/curation/SusceptibilityChip.vue'

describe('SusceptibilityChip', () => {
  it('follows the strength when a record changes in place (#473)', async () => {
    // TooltipProvider wraps the chip; setProps on the wrapper reaches the same chip instance
    const w = mount(
      (props: { strength: string }) => h(TooltipProvider, () => h(SusceptibilityChip, props)),
      { props: { strength: 'Likely association' } }
    )
    const state = () => {
      const chip = w.find('[data-slot="chip"]')
      return {
        label: chip.text(),
        struck: chip.classes().includes('line-through'),
        icon: chip.find('svg').exists(),
        tooltip: w.findComponent(Chip).props('tooltip') as string
      }
    }
    const likely = {
      label: 'Likely association',
      struck: false,
      icon: false,
      tooltip: expect.stringContaining('not a Mendelian validity class')
    }
    expect(state()).toEqual(likely)

    await w.setProps({ strength: 'Refuted association' })
    expect(state()).toEqual({
      label: 'Refuted association',
      struck: true,
      icon: true,
      tooltip: expect.stringContaining('not a risk allele')
    })

    await w.setProps({ strength: 'Likely association' })
    expect(state()).toEqual(likely)
  })
})
