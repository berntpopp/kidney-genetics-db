/* global HTMLTextAreaElement, HTMLInputElement, HTMLButtonElement */
import { afterEach, describe, expect, it, vi } from 'vitest'
import { flushPromises, mount, type VueWrapper } from '@vue/test-utils'
import VolunteerDialog from '@/components/curation/VolunteerDialog.vue'

vi.mock('@/api/volunteerApplications', () => ({ volunteerApplicationsApi: { submit: vi.fn() } }))
import { volunteerApplicationsApi } from '@/api/volunteerApplications'

const submit = vi.mocked(volunteerApplicationsApi.submit)
let wrapper: VueWrapper | undefined
afterEach(() => {
  wrapper?.unmount()
  document.body.innerHTML = ''
  vi.clearAllMocks()
})

function fill(selector: string, value: string) {
  const el = document.body.querySelector(selector) as HTMLInputElement | HTMLTextAreaElement
  el.value = value
  el.dispatchEvent(new Event('input'))
}

async function openAndFill(consent: boolean) {
  wrapper = mount(VolunteerDialog, { props: { symbol: 'CLDN10' }, attachTo: document.body })
  await wrapper.find('button').trigger('click')
  await flushPromises()
  fill('#vol-name', 'Ada Expert')
  fill('#vol-email', 'ada@example.org')
  fill('#vol-motivation', 'I study this gene.')
  if (consent) (document.body.querySelector('#vol-consent') as HTMLInputElement).click()
  await flushPromises()
}

const sendButton = () => document.body.querySelector('button[type="submit"]') as HTMLButtonElement

describe('VolunteerDialog', () => {
  it('cannot be sent without consent', async () => {
    await openAndFill(false)
    expect(sendButton().disabled).toBe(true)
  })

  it('keeps the honeypot hidden, sends it empty and confirms', async () => {
    submit.mockResolvedValue()
    await openAndFill(true)
    const honeypot = document.body.querySelector('input[name="website"]') as HTMLInputElement
    expect(honeypot.closest('[aria-hidden="true"]')?.classList.contains('hidden')).toBe(true)
    expect(sendButton().disabled).toBe(false)
    document.body.querySelector('form')!.dispatchEvent(new Event('submit'))
    await flushPromises()
    expect(submit).toHaveBeenCalledWith(
      expect.objectContaining({ gene_symbol: 'CLDN10', email: 'ada@example.org', website: '' })
    )
    expect(document.body.textContent).toContain('an admin will review your application')
  })

  it('shows the rate-limit message on 429', async () => {
    submit.mockRejectedValue({ isAxiosError: true, response: { status: 429 } })
    await openAndFill(true)
    document.body.querySelector('form')!.dispatchEvent(new Event('submit'))
    await flushPromises()
    expect(document.body.querySelector('[role="alert"]')?.textContent).toBe(
      'Too many applications, try later'
    )
  })
})
