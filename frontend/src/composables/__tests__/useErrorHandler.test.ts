import { describe, it, expect, vi } from 'vitest'
import { useErrorHandler } from '../useErrorHandler'

// Mock window.logService
const mockLogService = { error: vi.fn() }
Object.defineProperty(window, 'logService', { value: mockLogService, writable: true })

describe('useErrorHandler', () => {
  it('starts with no error', () => {
    const { error, isError } = useErrorHandler()
    expect(error.value).toBeNull()
    expect(isError.value).toBe(false)
  })

  it('handles error with fallback message', () => {
    const { error, isError, handleError } = useErrorHandler()
    handleError(new Error('test'), 'fallback')
    expect(isError.value).toBe(true)
    expect(error.value?.message).toBe('fallback')
  })

  it('clears error', () => {
    const { error, isError, handleError, clearError } = useErrorHandler()
    handleError(new Error('test'), 'fail')
    clearError()
    expect(error.value).toBeNull()
    expect(isError.value).toBe(false)
  })

  it('extracts API error detail', () => {
    const { error, handleError } = useErrorHandler()
    handleError({ response: { data: { detail: 'Not Found' }, status: 404 } }, 'fallback')
    expect(error.value?.message).toBe('Not Found')
    expect(error.value?.code).toBe(404)
  })
})
