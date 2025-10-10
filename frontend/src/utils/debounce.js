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

  const debounced = function (...args) {
    // Clear previous timeout
    if (timeoutId !== null) {
      clearTimeout(timeoutId)
    }

    // Schedule new execution
    timeoutId = setTimeout(() => {
      timeoutId = null
      fn.apply(this, args)
    }, delay)
  }

  // Add cancel method to debounced function
  debounced.cancel = function () {
    if (timeoutId !== null) {
      clearTimeout(timeoutId)
      timeoutId = null
    }
  }

  // Add flush method to immediately execute pending call
  debounced.flush = function (...args) {
    if (timeoutId !== null) {
      clearTimeout(timeoutId)
      timeoutId = null
      fn.apply(this, args)
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
