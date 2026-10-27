/**
 * Cytoscape parses only hex/rgb/hsl colours, so token colours (`var(--source-1)` resolving to
 * oklch, or a color-mix() of tokens) are rasterised to hex here. Every var() is resolved
 * against the document; colours must be opaque. Results are cached until clearCanvasColors() (call it on theme change).
 */
import { resolveCssColor } from '@/utils/sources'

const cache = new Map<string, string>()
const newContext = () =>
  document.createElement('canvas').getContext('2d', { willReadFrequently: true })
let ctx: ReturnType<typeof newContext> | undefined

export function clearCanvasColors(): void {
  cache.clear()
}

export function canvasColor(value: string): string {
  const hit = cache.get(value)
  if (hit) return hit
  const css = value.replace(/var\(--[\w-]+\)/g, v => resolveCssColor(v))
  if (ctx === undefined) ctx = newContext()
  if (!ctx) return css
  ctx.clearRect(0, 0, 1, 1)
  ctx.fillStyle = css
  ctx.fillRect(0, 0, 1, 1)
  const [r = 0, g = 0, b = 0] = ctx.getImageData(0, 0, 1, 1).data
  const hex = '#' + [r, g, b].map(c => c.toString(16).padStart(2, '0')).join('')
  cache.set(value, hex)
  return hex
}
