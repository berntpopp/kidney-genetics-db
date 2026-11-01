import { describe, expect, it, vi } from 'vitest'
import { flushPromises, mount } from '@vue/test-utils'
import NotificationPrefsCard from '@/components/auth/NotificationPrefsCard.vue'

vi.mock('@/api/curationReports', () => ({
  notificationPrefsApi: { list: vi.fn(), update: vi.fn() }
}))
import { notificationPrefsApi } from '@/api/curationReports'

const api = vi.mocked(notificationPrefsApi)
const pref = (enabled: boolean) => [{ event: 'curation_report', label: 'Reports', enabled }]

describe('NotificationPrefsCard', () => {
  it('lists events and saves a toggle', async () => {
    api.list.mockResolvedValue(pref(true))
    api.update.mockResolvedValue(pref(false))
    const wrapper = mount(NotificationPrefsCard)
    await flushPromises()
    const sw = wrapper.find('button[role="switch"]')
    expect(sw.attributes('aria-checked')).toBe('true')

    await sw.trigger('click')
    await flushPromises()
    expect(api.update).toHaveBeenCalledWith({ curation_report: false })
    expect(wrapper.find('button[role="switch"]').attributes('aria-checked')).toBe('false')
  })
})
