// @vitest-environment node
/**
 * Production build config regressions. The #312 guard against precompressed HTML is a
 * built-bundle check in CI (.github/workflows/ci.yml). #313: async-swapped critical CSS shifts the layout.
 * #328: the vendor-tanstack chunk dragged the Vue runtime into every route.
 */
import { describe, it, expect } from 'vitest'
import config from '../../vite.config'

describe('production build config', () => {
  it('does not swap in the stylesheet asynchronously (#313)', () => {
    expect(
      (config as { ssgOptions?: { beastiesOptions?: unknown } }).ssgOptions?.beastiesOptions
    ).toBe(false)
  })

  it('has no vendor-tanstack chunk (#328)', () => {
    const output = config.build?.rollupOptions?.output as {
      manualChunks: (_id: string) => string | undefined
    }
    expect(
      output.manualChunks('/x/node_modules/@tanstack/vue-table/dist/index.mjs')
    ).toBeUndefined()
  })
})
