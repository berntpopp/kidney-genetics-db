const dateFmt = new Intl.DateTimeFormat('en-GB', {
  day: 'numeric',
  month: 'short',
  year: 'numeric'
})
const dateTimeFmt = new Intl.DateTimeFormat('en-GB', {
  day: 'numeric',
  month: 'short',
  year: 'numeric',
  hour: '2-digit',
  minute: '2-digit'
})

function parse(iso: string | number | Date | null | undefined): Date | null {
  if (iso === null || iso === undefined || iso === '') return null
  const d = new Date(iso)
  return Number.isNaN(d.getTime()) ? null : d
}

/** "15 Mar 2026"; '' for missing or invalid input. */
export function formatDate(iso: string | number | Date | null | undefined): string {
  const d = parse(iso)
  return d ? dateFmt.format(d) : ''
}

/** "15 Mar 2026, 14:05"; '' for missing or invalid input. */
export function formatDateTime(iso: string | number | Date | null | undefined): string {
  const d = parse(iso)
  return d ? dateTimeFmt.format(d) : ''
}
