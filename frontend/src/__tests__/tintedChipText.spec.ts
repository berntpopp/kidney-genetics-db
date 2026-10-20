/**
 * A 500-shade hex as text on its own 8-12.5% tint ('15'/'20' alpha) is 1.9-3.2:1 and
 * fails WCAG AA (#320). Chips must use tintedChipStyle(hex), which darkens the text.
 */

import { describe, it, expect } from 'vitest'

const sources = import.meta.glob(['@/views/**/*.vue', '@/components/**/*.vue'], {
  query: '?raw',
  import: 'default',
  eager: true
}) as Record<string, string>

// Style objects bound in double-quoted attributes never contain a double quote.
const STYLE_OBJECT = /:style="\{([^"]*)\}"/g
const RAW_TINT =
  /backgroundColor:\s*(?:'(#[0-9a-fA-F]{6})[0-9a-fA-F]{2}'|([^,]+?)\s*\+\s*'[0-9a-fA-F]{2}')/

function rawTintedTextPairs(src: string): string[] {
  const hits: string[] = []
  for (const [, body] of src.matchAll(STYLE_OBJECT)) {
    const tint = body.replace(/\s+/g, ' ').match(RAW_TINT)
    if (!tint) continue
    const base = tint[1] ? `'${tint[1]}'` : tint[2].trim()
    const escaped = base.replace(/[.*+?^${}()|[\]\\]/g, '\\$&')
    if (new RegExp(`(^|[{,\\s])color:\\s*${escaped}\\s*(,|$)`).test(body.replace(/\s+/g, ' ')))
      hits.push(base)
  }
  return hits
}

describe('tinted chip text contrast', () => {
  it('detects a raw hex + alpha tint with the same hex as text', () => {
    expect(rawTintedTextPairs(`:style="{ backgroundColor: c + '20', color: c }"`)).toEqual(['c'])
    expect(
      rawTintedTextPairs(`:style="{ backgroundColor: '#6b728020', color: '#6b7280' }"`)
    ).toEqual(["'#6b7280'"])
    expect(rawTintedTextPairs(`:style="tintedChipStyle('#6b7280')"`)).toEqual([])
  })

  it('no component pairs a raw alpha tint with the same 500-shade text', () => {
    const offenders = Object.entries(sources)
      .filter(([, src]) => rawTintedTextPairs(src).length > 0)
      .map(([path]) => path)
    expect(offenders).toEqual([])
  })
})
