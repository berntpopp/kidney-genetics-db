import { describe, it, expect, vi } from 'vitest'
import { LogService } from '@/services/logService'
import { config } from '@/config'

describe('logService backend reporting', () => {
  it('posts errors to the backend /api/client-logs endpoint', () => {
    vi.useFakeTimers()
    const beacon = vi.fn(() => true)
    Object.defineProperty(navigator, 'sendBeacon', { value: beacon, configurable: true })

    new LogService().error('boom')
    vi.runAllTimers()

    expect(beacon).toHaveBeenCalledWith(`${config.apiBaseUrl}/api/client-logs`, expect.any(Blob))
    vi.useRealTimers()
  })
})
