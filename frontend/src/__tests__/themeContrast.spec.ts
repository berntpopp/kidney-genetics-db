import { describe, it, expect } from 'vitest'
import { readFileSync } from 'node:fs'

// cwd = frontend/; the first block is :root (light), the second .dark
const [light = '', dark = ''] = readFileSync('src/assets/main.css', 'utf8').split('.dark {')

// Resolves var(--x) aliases; .dark inherits tokens it does not redefine from :root
function token(css: string, name: string): number[] {
  const m =
    css.match(new RegExp(`--${name}: ([^;]+);`)) ?? light.match(new RegExp(`--${name}: ([^;]+);`))
  if (!m) throw new Error(`--${name} not found`)
  const alias = m[1]!.match(/^var\(--([\w-]+)\)$/)
  if (alias) return token(css, alias[1]!)
  const v = m[1]!.match(/^oklch\(([\d.]+) ([\d.]+) ([\d.]+)\)$/)
  if (!v) throw new Error(`--${name} is not OKLCH: ${m[1]}`)
  return v.slice(1).map(Number)
}

// OKLCH -> linear sRGB (Björn Ottosson's matrices) -> WCAG relative luminance
function luminance([L = 0, C = 0, h = 0]: number[]): number {
  const a = C * Math.cos((h * Math.PI) / 180)
  const b = C * Math.sin((h * Math.PI) / 180)
  const l = (L + 0.3963377774 * a + 0.2158037573 * b) ** 3
  const m = (L - 0.1055613458 * a - 0.0638541728 * b) ** 3
  const s = (L - 0.0894841775 * a - 1.291485548 * b) ** 3
  const rgb = [
    4.0767416621 * l - 3.3077115913 * m + 0.2309699292 * s,
    -1.2684380046 * l + 2.6097574011 * m - 0.3413193965 * s,
    -0.0041960863 * l - 0.7034186147 * m + 1.707614701 * s
  ].map(v => Math.min(1, Math.max(0, v)))
  return 0.2126 * (rgb[0] ?? 0) + 0.7152 * (rgb[1] ?? 0) + 0.0722 * (rgb[2] ?? 0)
}

function contrast(css: string, x: string, y: string): number {
  const [hi = 0, lo = 0] = [luminance(token(css, x)), luminance(token(css, y))].sort(
    (p, q) => q - p
  )
  return (hi + 0.05) / (lo + 0.05)
}

const themes = [
  ['light', light],
  ['dark', dark]
] as const
const statuses = ['success', 'warning', 'danger', 'info']

describe.each(themes)('%s theme tokens meet WCAG AA (4.5:1)', (_name, css) => {
  it.each(['primary', 'secondary', 'destructive', ...statuses])(
    '%s vs its -foreground token',
    name => {
      expect(contrast(css, name, `${name}-foreground`)).toBeGreaterThanOrEqual(4.5)
    }
  )

  it.each(statuses.flatMap(s => ['background', 'card', `${s}-subtle`].map(bg => [s, bg])))(
    '%s as text on --%s',
    (name, bg) => {
      expect(contrast(css, name, bg)).toBeGreaterThanOrEqual(4.5)
    }
  )

  it('secondary is neutral (the same as muted)', () => {
    expect(token(css, 'secondary')).toEqual(token(css, 'muted'))
  })
})
