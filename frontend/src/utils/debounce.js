/**
 * Debounce Utility
 *
 * Delays function execution until after a specified wait time has elapsed
 * since the last time it was invoked. Critical for preventing excessive
 * URL updates and browser history pollution.
 *
 * @module utils/debounce
 */

/**
 * Create a debounced function that delays invoking the provided function
 * until after the specified delay has elapsed since the last invocation.
 *
 * @param {Function} fn - The function to debounce
 * @param {number} delay - The delay in milliseconds
 * @returns {Function} Debounced function with cancel method
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
export function debounce(fn, delay) {
  let timeoutId = null
  let lastArgs = null
  let lastThis = null

  const debounced = function (...args) {
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
      fn.apply(lastThis, lastArgs)
    }, delay)
  }

  // Add cancel method to debounced function
  debounced.cancel = function () {
    if (timeoutId !== null) {
      clearTimeout(timeoutId)
      timeoutId = null
    }
    lastArgs = null
    lastThis = null
  }

  // Add flush method to immediately execute with last stored args
  debounced.flush = function () {
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

  return debounced
}

/**
 * Create a throttled function that only invokes the provided function
 * at most once per specified delay period.
 *
 * @param {Function} fn - The function to throttle
 * @param {number} delay - The delay in milliseconds
 * @returns {Function} Throttled function
 *
 * @example
 * const throttledScroll = throttle(() => {
 *   console.log('Scroll event')
 * }, 100)
 *
 * window.addEventListener('scroll', throttledScroll)
 */
export function throttle(fn, delay) {
  let lastCall = 0

  return function (...args) {
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
