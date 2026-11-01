/* global HTMLButtonElement, HTMLInputElement */
import { afterEach, describe, expect, it, vi } from 'vitest'
import { flushPromises, mount, type VueWrapper } from '@vue/test-utils'
import AdminVolunteerApplications from '@/views/admin/AdminVolunteerApplications.vue'

const row = {
  id: 7,
  gene_symbol: 'CLDN10',
  name: 'Ada Expert',
  email: 'ada@example.org',
  affiliation: 'Charite',
  orcid: '0000-0002-1825-009X',
  motivation: 'I study this gene.',
  status: 'pending',
  decided_by: null,
  decided_at: null,
  decision_note: null,
  user_id: null,
  created_at: '2026-11-01T10:00:00Z'
}

vi.mock('@/api/volunteerApplications', () => ({
  volunteerApplicationsApi: {
    list: vi.fn(async () => ({
      data: [row],
      meta: { total: 1, limit: 100, offset: 0, pending_count: 1 }
    })),
    decide: vi.fn(async () => ({
      ...row,
      status: 'approved',
      invite_url: 'https://kgdb.example/reset-password?token=abc'
    }))
  }
}))
import { volunteerApplicationsApi } from '@/api/volunteerApplications'

vi.stubGlobal('logService', { info: vi.fn(), warn: vi.fn(), error: vi.fn(), debug: vi.fn() })

let wrapper: VueWrapper | undefined
afterEach(() => {
  wrapper?.unmount()
  document.body.innerHTML = ''
  vi.clearAllMocks()
})

describe('AdminVolunteerApplications', () => {
  it('renders the application with an ORCID link and decides after confirmation', async () => {
    wrapper = mount(AdminVolunteerApplications, {
      attachTo: document.body,
      global: { stubs: { RouterLink: { template: '<a><slot /></a>' } } }
    })
    await flushPromises()
    expect(wrapper.text()).toContain('Ada Expert')
    expect(wrapper.text()).toContain('Charite')
    expect(wrapper.find('a[href="https://orcid.org/0000-0002-1825-009X"]').exists()).toBe(true)

    const approve = wrapper.findAll('button').find(b => b.text() === 'Approve')!
    await approve.trigger('click')
    await flushPromises()
    expect(volunteerApplicationsApi.decide).not.toHaveBeenCalled()

    const confirmBtn = [...document.body.querySelectorAll('[role="alertdialog"] button')].find(
      b => b.textContent?.trim() === 'Approve'
    ) as HTMLButtonElement
    confirmBtn.click()
    await flushPromises()
    expect(volunteerApplicationsApi.decide).toHaveBeenCalledWith(7, {
      decision: 'approved',
      note: undefined,
      role: 'curator'
    })
    expect(document.body.textContent).toContain('Email is not configured')
    expect(
      (document.body.querySelector('input[aria-label="Invite link"]') as HTMLInputElement).value
    ).toContain('/reset-password?token=abc')
  })
})
