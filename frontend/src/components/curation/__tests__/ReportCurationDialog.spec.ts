/* global HTMLTextAreaElement, HTMLInputElement */
import { afterEach, describe, expect, it, vi } from 'vitest'
import { flushPromises, mount, type VueWrapper } from '@vue/test-utils'
import ReportCurationDialog from '@/components/curation/ReportCurationDialog.vue'

vi.mock('@/api/curationReports', () => ({ curationReportsApi: { submit: vi.fn() } }))
import { curationReportsApi } from '@/api/curationReports'

const submit = vi.mocked(curationReportsApi.submit)
let wrapper: VueWrapper | undefined
afterEach(() => {
  wrapper?.unmount()
  document.body.innerHTML = ''
  vi.clearAllMocks()
})

async function openAndFill() {
  wrapper = mount(ReportCurationDialog, { props: { symbol: 'CLDN10' }, attachTo: document.body })
  await wrapper.find('button').trigger('click')
  await flushPromises()
  const message = document.body.querySelector('#report-message') as HTMLTextAreaElement
  message.value = 'The inheritance is wrong.'
  message.dispatchEvent(new Event('input'))
  await flushPromises()
}

const sendForm = async () => {
  document.body.querySelector('form')!.dispatchEvent(new Event('submit'))
  await flushPromises()
}

describe('ReportCurationDialog', () => {
  it('keeps the honeypot hidden and sends it empty', async () => {
    submit.mockResolvedValue()
    await openAndFill()
    const honeypot = document.body.querySelector('input[name="website"]') as HTMLInputElement
    expect(honeypot.closest('[aria-hidden="true"]')?.classList.contains('hidden')).toBe(true)
    await sendForm()
    expect(submit).toHaveBeenCalledWith(
      expect.objectContaining({ gene_symbol: 'CLDN10', kind: 'problem', website: '' })
    )
    expect(document.body.textContent).toContain('Thanks — the curators will review it.')
  })

  it('shows the rate-limit message on 429', async () => {
    submit.mockRejectedValue({ isAxiosError: true, response: { status: 429 } })
    await openAndFill()
    await sendForm()
    expect(document.body.querySelector('[role="alert"]')?.textContent).toBe(
      'Too many reports, try later'
    )
  })
})
