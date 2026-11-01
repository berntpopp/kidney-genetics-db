import { describe, it, expect, vi } from 'vitest'
import { toCsv, useShareExport } from '../useShareExport'

describe('toCsv', () => {
  it('quotes commas, quotes and newlines and blanks nullish cells', () => {
    expect(toCsv([['a', 'b,c', 'say "hi"', 'x\ny', null, undefined, 0]])).toBe(
      'a,"b,c","say ""hi""","x\ny",,,0'
    )
  })

  it('joins rows with a newline', () => {
    expect(
      toCsv([
        ['h1', 'h2'],
        [1, 2]
      ])
    ).toBe('h1,h2\n1,2')
  })
})

describe('printPdf', () => {
  it('prints under the export name and restores the title afterwards', () => {
    document.title = 'Page'
    const print = vi.spyOn(window, 'print').mockImplementation(() => {
      expect(document.title).toBe('COL4A5-curated-associations-2026-11-01')
    })
    useShareExport().printPdf('COL4A5-curated-associations-2026-11-01')
    expect(print).toHaveBeenCalledOnce()
    window.dispatchEvent(new Event('afterprint'))
    expect(document.title).toBe('Page')
  })
})
