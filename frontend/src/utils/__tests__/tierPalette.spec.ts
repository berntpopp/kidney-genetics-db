/**
 * The evidence-strength ramp must stay apart under deuteranopia and keep tinted chips at
 * WCAG AA in both themes (#325). Tier colours are var(--strength-N); the values are read
 * from src/assets/main.css. Deuteranopia: Machado et al. 2009, severity 1. Distance:
 * Euclidean in OKLab. Chip text: tintedChipStyle mixes the colour 55% toward --foreground
 * in OKLab on a 12.5% tint.
 */
import { readFileSync } from 'node:fs'
import { describe, it, expect } from 'vitest'
import { TIER_CONFIG, tintedChipStyle } from '@/utils/evidenceTiers'

type RGB = number[]
const toLin = (c: number) => (c <= 0.04045 ? c / 12.92 : ((c + 0.055) / 1.055) ** 2.4)
const toSrgb = (c: number) => (c <= 0.0031308 ? 12.92 * c : 1.055 * c ** (1 / 2.4) - 0.055)
const clamp = (c: number) => Math.min(1, Math.max(0, c))
const mul = (m: number[][], v: RGB) => m.map(r => r[0]! * v[0]! + r[1]! * v[1]! + r[2]! * v[2]!)

const LMS = [
  [0.4122214708, 0.5363325363, 0.0514459929],
  [0.2119034982, 0.6806995451, 0.1073969566],
  [0.0883024619, 0.2817188376, 0.6299787005]
]
const LAB = [
  [0.2104542553, 0.793617785, -0.0040720468],
  [1.9779984951, -2.428592205, 0.4505937099],
  [0.0259040371, 0.7827717662, -0.808675766]
]
const LAB_INV = [
  [1, 0.3963377774, 0.2158037573],
  [1, -0.1055613458, -0.0638541728],
  [1, -0.0894841775, -1.291485548]
]
const LMS_INV = [
  [4.0767416621, -3.3077115913, 0.2309699292],
  [-1.2684380046, 2.6097574011, -0.3413193965],
  [-0.0041960863, -0.7034186147, 1.707614701]
]
const DEUTERANOPIA = [
  [0.367322, 0.860646, -0.227968],
  [0.280085, 0.672501, 0.047413],
  [-0.01182, 0.04294, 0.968881]
]
const oklab = (lin: RGB) => mul(LAB, mul(LMS, lin).map(Math.cbrt))
const fromOklab = (lab: RGB) =>
  mul(
    LMS_INV,
    mul(LAB_INV, lab).map(c => c ** 3)
  ).map(c => toLin(toSrgb(clamp(c))))
const luminance = (lin: RGB) => 0.2126 * lin[0]! + 0.7152 * lin[1]! + 0.0722 * lin[2]!
const contrast = (a: RGB, b: RGB) => {
  const [hi, lo] = [luminance(a), luminance(b)].sort((x, y) => y - x)
  return (hi! + 0.05) / (lo! + 0.05)
}

// cwd = frontend/; the first block is :root (light), the second .dark
const [lightCss = '', darkCss = ''] = readFileSync('src/assets/main.css', 'utf8').split('.dark {')
function token(css: string, name: string): RGB {
  const m = css.match(new RegExp(`--${name}: oklch\\(([\\d.]+) ([\\d.]+) ([\\d.]+)\\)`))
  if (!m) throw new Error(`--${name} not found`)
  const [L = 0, C = 0, h = 0] = m.slice(1).map(Number)
  return fromOklab([L, C * Math.cos((h * Math.PI) / 180), C * Math.sin((h * Math.PI) / 180)])
}

const themes = [
  { name: 'light', css: lightCss },
  { name: 'dark', css: darkCss }
]
const steps = [1, 2, 3, 4, 5]

it('tiers use the strength tokens and chips accept CSS variables', () => {
  expect(Object.values(TIER_CONFIG).map(t => t.color)).toEqual(
    [5, 4, 3, 2, 1].map(n => `var(--strength-${n})`)
  )
  // no hex-alpha concatenation such as "var(--x)20"
  expect(Object.values(tintedChipStyle('var(--strength-5)')).join()).not.toMatch(/\)[0-9a-f]{2}/)
})

describe.each(themes)('$name strength ramp under deuteranopia (#325)', ({ css }) => {
  it.each(steps.flatMap((a, i) => steps.slice(i + 1).map(b => [a, b])))(
    'strength-%i and strength-%i stay distinguishable',
    (a, b) => {
      const sim = (n: number) => oklab(mul(DEUTERANOPIA, token(css, `strength-${n}`)).map(clamp))
      const [x, y] = [sim(a!), sim(b!)]
      expect(Math.hypot(...x.map((v, i) => v - y[i]!))).toBeGreaterThan(0.15)
    }
  )
})

describe.each(themes)('$name strength chip contrast (#325)', ({ css }) => {
  it.each(steps.flatMap(n => ['background', 'card'].map(c => [n, c])))(
    'strength-%i chip text on --%s is >= 4.5:1',
    (n, canvas) => {
      const color = token(css, `strength-${n}`)
      const bg = token(css, canvas as string)
      const [c, f] = [oklab(color), oklab(token(css, 'foreground'))]
      const text = fromOklab(c.map((v, i) => v * 0.55 + f[i]! * 0.45))
      const alpha = 0.125
      // color-mix(in srgb, ..., transparent) composites in sRGB, not linear light
      const tint = color.map((v, i) => toLin(toSrgb(v) * alpha + toSrgb(bg[i]!) * (1 - alpha)))
      expect(contrast(text, tint)).toBeGreaterThanOrEqual(4.5)
    }
  )
})
