import { describe, it, expect } from 'vitest'
import { toCsv } from '../useShareExport'

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
