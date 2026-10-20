import { describe, it, expect, beforeEach, vi } from 'vitest'
import indexHtml from '../../index.html?raw'
import { readFileSync } from 'node:fs'

// CSS ?raw imports are emptied by Vitest; read from disk (cwd = frontend/).
const mainCss = readFileSync('src/assets/main.css', 'utf8')

// The pre-paint theme script in index.html must agree with useAppTheme (kgdb-color-mode).
const script = indexHtml.match(/<script>([\s\S]*?)<\/script>/)?.[1] ?? ''

function run(stored: string | null, osDark: boolean) {
  localStorage.clear()
  if (stored !== null) localStorage.setItem('kgdb-color-mode', stored)
  vi.stubGlobal(
    'matchMedia',
    vi.fn(() => ({ matches: osDark }))
  )
  new Function(script)()
  const scheme = document.querySelector('meta[name="color-scheme"]')?.getAttribute('content')
  return { dark: document.documentElement.classList.contains('dark'), scheme }
}

describe('index.html pre-paint theme script', () => {
  beforeEach(() => {
    document.documentElement.className = ''
    document.head.innerHTML = '<meta name="color-scheme" content="light dark">'
  })

  it('is inlined in <head>', () => {
    const head = indexHtml.split('</head>')[0] ?? ''
    expect(script).toContain('kgdb-color-mode')
    expect(head).toContain('<meta name="color-scheme" content="light dark">')
    expect(head.indexOf('<script>')).toBeGreaterThan(-1)
  })

  it.each([
    ['dark', false, true],
    ['light', true, false],
    ['auto', true, true],
    ['auto', false, false],
    [null, true, true],
    [null, false, false]
  ])('stored=%s osDark=%s -> dark=%s', (stored, osDark, expected) => {
    expect(run(stored, osDark)).toEqual({ dark: expected, scheme: expected ? 'dark' : 'light' })
  })

  it('removes a stale dark class when the stored mode is light', () => {
    document.documentElement.classList.add('dark')
    expect(run('light', true).dark).toBe(false)
  })
})

describe('main.css dark variant', () => {
  it('binds dark: to the .dark class instead of prefers-color-scheme', () => {
    expect(mainCss).toContain('@custom-variant dark (&:is(.dark *));')
  })
})
