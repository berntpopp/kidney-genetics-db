/**
 * RFC 4180 CSV with a spreadsheet formula-injection guard (OWASP CSV injection), plus a
 * browser download helper that always revokes its object URL.
 */

// Text a spreadsheet would evaluate as a formula; numbers are never prefixed (keeps -0.5 numeric)
const FORMULA_START = /^[=+\-@\t\r]/

export function csvCell(value: unknown): string {
  if (value === null || value === undefined) return ''
  let text = String(value)
  if (typeof value === 'string' && FORMULA_START.test(text)) text = `'${text}`
  return /[",\r\n]/.test(text) ? `"${text.replace(/"/g, '""')}"` : text
}

export const toCsv = (headers: string[], rows: unknown[][]): string =>
  [headers, ...rows].map(row => row.map(csvCell).join(',')).join('\r\n')

export function downloadFile(content: string | Blob, filename: string, type: string): void {
  const blob = content instanceof Blob ? content : new Blob([content], { type })
  const url = URL.createObjectURL(blob)
  const link = document.createElement('a')
  link.href = url
  link.download = filename
  link.click()
  setTimeout(() => URL.revokeObjectURL(url))
}

/** Lower-case, filesystem-safe filename part: "Cluster 3" -> "cluster_3" */
export const fileSlug = (text: string): string =>
  text
    .toLowerCase()
    .replace(/[^a-z0-9]+/g, '_')
    .replace(/^_|_$/g, '')

/** YYYY-MM-DD in local time, for export filenames */
export const isoDate = (date = new Date()): string =>
  `${date.getFullYear()}-${String(date.getMonth() + 1).padStart(2, '0')}-${String(date.getDate()).padStart(2, '0')}`
