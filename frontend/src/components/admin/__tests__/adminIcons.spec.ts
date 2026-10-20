/**
 * Admin headers and stat cards take lucide components; Vuetify `mdi-*` names
 * render nothing in the shadcn header and left a 36 px gap (#321).
 */

import { describe, it, expect } from 'vitest'
import { mount } from '@vue/test-utils'
import { Database } from 'lucide-vue-next'
import AdminStatsCard from '@/components/admin/AdminStatsCard.vue'

const adminSources = import.meta.glob(['@/views/admin/*.vue', '@/components/admin/**/*.vue'], {
  query: '?raw',
  import: 'default',
  eager: true
}) as Record<string, string>

describe('admin icons', () => {
  it('no admin view or component passes an mdi-* icon name', () => {
    const offenders = Object.entries(adminSources)
      .filter(([, src]) => src.includes('mdi-'))
      .map(([path]) => path)
    expect(offenders).toEqual([])
  })

  it('AdminStatsCard renders the lucide component it is given', () => {
    const wrapper = mount(AdminStatsCard, { props: { title: 'Rows', value: 3, icon: Database } })
    expect(wrapper.find('svg.lucide-database-icon, svg.lucide').exists()).toBe(true)
  })
})
