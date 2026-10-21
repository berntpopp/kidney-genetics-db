/**
 * Tier colours must stay apart under deuteranopia and keep tinted chips at WCAG AA (#325).
 * Deuteranopia: Machado et al. 2009, severity 1. Distance: Euclidean in OKLab.
 * Chip text: tintedChipStyle mixes the hex 55% toward --foreground in OKLab on a 0x20 tint.
 */
import { describe, it, expect } from 'vitest'
import { TIER_CONFIG } from '@/utils/evidenceTiers'

type RGB = number[]
const toLin = (c: number) => (c <= 0.04045 ? c / 12.92 : ((c + 0.055) / 1.055) ** 2.4)
const toSrgb = (c: number) => (c <= 0.0031308 ? 12.92 * c : 1.055 * c ** (1 / 2.4) - 0.055)
const clamp = (c: number) => Math.min(1, Math.max(0, c))
const mul = (m: number[][], v: RGB) => m.map(r => r[0]! * v[0]! + r[1]! * v[1]! + r[2]! * v[2]!)
const hexLin = (h: string) => [1, 3, 5].map(i => toLin(parseInt(h.slice(i, i + 2), 16) / 255))

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
// Theme tokens from src/assets/main.css: oklch(0.985 0 0) and oklch(0.141 0.005 285.823)
const near = fromOklab([0.985, 0, 0])
const ink = fromOklab([0.141, 0.005 * Math.cos(4.989), 0.005 * Math.sin(4.989)])

const tiers = Object.entries(TIER_CONFIG)

describe('tier palette under deuteranopia (#325)', () => {
  it.each(
    tiers.flatMap(([a, ca], i) => tiers.slice(i + 1).map(([b, cb]) => [a, b, ca.color, cb.color]))
  )('%s and %s stay distinguishable', (_a, _b, ca, cb) => {
    const sim = (h: string) => oklab(mul(DEUTERANOPIA, hexLin(h)).map(clamp))
    const [x, y] = [sim(ca!), sim(cb!)]
    expect(Math.hypot(...x.map((v, i) => v - y[i]!))).toBeGreaterThan(0.15)
  })
})

describe('tier chip contrast (#325)', () => {
  it.each(
    tiers.flatMap(([t, c]) => [
      [t, c.color, near, ink],
      [t, c.color, ink, near]
    ])
  )('%s chip text is >= 4.5:1', (_t, hex, bg, fg) => {
    const color = hexLin(hex as string)
    const [c, f] = [oklab(color), oklab(fg as RGB)]
    const text = fromOklab(c.map((v, i) => v * 0.55 + f[i]! * 0.45))
    const alpha = 0x20 / 255
    // Browsers composite alpha in sRGB, not linear light
    const tint = color.map((v, i) =>
      toLin(toSrgb(v) * alpha + toSrgb((bg as RGB)[i]!) * (1 - alpha))
    )
    expect(contrast(text, tint)).toBeGreaterThanOrEqual(4.5)
  })
})
