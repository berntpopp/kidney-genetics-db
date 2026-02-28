/**
 * Debounce Utility
 *
 * Delays function execution until after a specified wait time has elapsed
 * since the last time it was invoked. Critical for preventing excessive
 * URL updates and browser history pollution.
 *
 * @module utils/debounce
 */

export interface DebouncedFunction<T extends (...args: any[]) => any> {
  (...args: Parameters<T>): void
  cancel(): void
  flush(...args: Parameters<T>): void
}

/**
 * Create a debounced function that delays invoking the provided function
 * until after the specified delay has elapsed since the last invocation.
 *
 * @param fn - The function to debounce
 * @param delay - The delay in milliseconds
 * @returns Debounced function with cancel and flush methods
 *
 * @example
 * const debouncedUpdate = debounce((value) => {
 *   console.log('Updated:', value)
 * }, 800)
 *
 * // These will be collapsed into a single call
 * debouncedUpdate('foo')
 * debouncedUpdate('bar')
 * debouncedUpdate('baz')  // Only this one will execute after 800ms
 *
 * // Cancel pending execution
 * debouncedUpdate.cancel()
 */
export function debounce<T extends (...args: any[]) => any>(
  fn: T,
  delay: number
): DebouncedFunction<T> {
  let timeoutId: ReturnType<typeof setTimeout> | null = null
  let lastArgs: Parameters<T> | null = null
  let lastThis: any = null

  const debounced = function (this: unknown, ...args: Parameters<T>): void {
    // Store the latest args and context
    lastArgs = args
    lastThis = this

    // Clear previous timeout
    if (timeoutId !== null) {
      clearTimeout(timeoutId)
    }

    // Schedule new execution
    timeoutId = setTimeout(() => {
      timeoutId = null
      fn.apply(lastThis, lastArgs!)
    }, delay)
  }

  // Add cancel method to debounced function
  debounced.cancel = function (): void {
    if (timeoutId !== null) {
      clearTimeout(timeoutId)
      timeoutId = null
    }
    lastArgs = null
    lastThis = null
  }

  // Add flush method to immediately execute with last stored args
  // Note: passed args are accepted for type compatibility but lastArgs are used internally
  debounced.flush = function (..._args: Parameters<T>): void {
    if (timeoutId !== null) {
      clearTimeout(timeoutId)
      timeoutId = null
    }
    // Execute with last stored args even if no timeout was pending
    if (lastArgs !== null) {
      fn.apply(lastThis, lastArgs)
      lastArgs = null
      lastThis = null
    }
  }

  return debounced as DebouncedFunction<T>
}

/**
 * Create a throttled function that only invokes the provided function
 * at most once per specified delay period.
 *
 * @param fn - The function to throttle
 * @param delay - The delay in milliseconds
 * @returns Throttled function
 *
 * @example
 * const throttledScroll = throttle(() => {
 *   console.log('Scroll event')
 * }, 100)
 *
 * window.addEventListener('scroll', throttledScroll)
 */
export function throttle<T extends (...args: any[]) => any>(
  fn: T,
  delay: number
): (...args: Parameters<T>) => void {
  let lastCall = 0

  return function (this: unknown, ...args: Parameters<T>): void {
    const now = Date.now()

    if (now - lastCall >= delay) {
      lastCall = now
      fn.apply(this, args)
    }
  }
}

export default {
  debounce,
  throttle
}
