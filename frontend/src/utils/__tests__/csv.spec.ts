import { describe, it, expect } from 'vitest'
import { csvCell, fileSlug, toCsv } from '../csv'

describe('csvCell', () => {
  it('quotes and doubles embedded quotes, commas and newlines', () => {
    expect(csvCell('say "hi"')).toBe('"say ""hi"""')
    expect(csvCell('a,b')).toBe('"a,b"')
    expect(csvCell('line\nbreak')).toBe('"line\nbreak"')
    expect(csvCell('plain')).toBe('plain')
  })

  it('neutralises spreadsheet formulas', () => {
    expect(csvCell('=HYPERLINK("http://x")')).toBe(`"'=HYPERLINK(""http://x"")"`)
    expect(csvCell('+1')).toBe("'+1")
    expect(csvCell('-cmd')).toBe("'-cmd")
    expect(csvCell('@SUM(A1)')).toBe("'@SUM(A1)")
  })

  it('keeps numbers numeric and empties nullish values', () => {
    expect(csvCell(-0.5)).toBe('-0.5')
    expect(csvCell(1e-7)).toBe('1e-7')
    expect(csvCell(null)).toBe('')
    expect(csvCell(undefined)).toBe('')
  })
})

describe('toCsv', () => {
  it('joins header and rows with CRLF and keeps a row per record', () => {
    const csv = toCsv(['Term', 'Genes'], [['Abnormal "renal" cyst', 'PKD1; PKD2']])
    expect(csv).toBe('Term,Genes\r\n"Abnormal ""renal"" cyst",PKD1; PKD2')
    expect(csv.split('\r\n')).toHaveLength(2)
  })
})

describe('fileSlug', () => {
  it('makes filesystem-safe names', () => {
    expect(fileSlug('Cluster 12')).toBe('cluster_12')
    expect(fileSlug('GO_Biological_Process_2023')).toBe('go_biological_process_2023')
  })
})
