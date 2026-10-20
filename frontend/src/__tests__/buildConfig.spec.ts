// @vitest-environment node
/**
 * Production build config regressions.
 * #312: precompressed HTML is written before vite-ssg prerenders, so nginx gzip_static
 * would serve a stale SPA shell. #313: async-swapped critical CSS shifts the layout.
 * #328: the vendor-tanstack chunk dragged the Vue runtime into every route.
 */
import { describe, it, expect } from 'vitest'
import type { Plugin } from 'vite'
import config from '../../vite.config'

type Bundle = Record<string, { type: 'asset'; source: string }>

/** Runs the compression plugin against a fake bundle and returns the emitted file names. */
async function compressedNames(files: string[]) {
  const plugin = (config.plugins as Plugin[])
    .flat()
    .find(p => p?.name === 'vite-plugin-compression') as Plugin & Record<string, any>
  // the plugin hooks into this Vite-internal plugin's generateBundle
  const analysis: Record<string, any> = { name: 'vite:build-import-analysis', generateBundle() {} }
  await plugin.configResolved.call(
    {},
    {
      root: process.cwd(),
      build: { outDir: 'dist' },
      publicDir: '',
      plugins: [analysis],
      logger: { info() {} }
    }
  )
  const bundle: Bundle = Object.fromEntries(
    files.map(f => [f, { type: 'asset', source: 'x'.repeat(5000) }])
  )
  const emitted: string[] = []
  await analysis.generateBundle.call(
    {
      emitFile: (f: { fileName: string }) => emitted.push(f.fileName),
      error: (e: unknown) => {
        throw e
      }
    },
    {},
    bundle
  )
  return emitted.sort()
}

describe('production build config', () => {
  it('precompresses assets but never HTML (#312)', async () => {
    expect(await compressedNames(['index.html', 'assets/app.js', 'assets/app.css'])).toEqual([
      'assets/app.css.br',
      'assets/app.css.gz',
      'assets/app.js.br',
      'assets/app.js.gz'
    ])
  })

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
