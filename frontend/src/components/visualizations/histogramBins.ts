/**
 * Count-per-gene histograms (panels, providers, publications): every integer bin is
 * shown, including empty ones, so the x axis is honest. Long tails (PubTator reaches
 * >1000 publications per gene) switch to 1-2-5 widening bins after 5.
 * Rows whose categories are not plain integers (e.g. HPO "1-5" ranges) pass through.
 */
export interface CountRow {
  category: string
  gene_count: number
}

const MAX_SINGLE_BINS = 25

export function binCounts(rows: CountRow[]): CountRow[] {
  if (rows.length === 0 || !rows.every(r => /^\d+$/.test(r.category))) return rows
  const counts = rows.map(r => [Number(r.category), r.gene_count] as const)
  const maxN = Math.max(...counts.map(([n]) => n))
  const start = Math.min(1, ...counts.map(([n]) => n))

  const bins: [number, number][] = []
  const singlesTo = maxN <= MAX_SINGLE_BINS ? maxN : 5
  for (let i = start; i <= singlesTo; i++) bins.push([i, i])
  for (let lo = singlesTo + 1, k = 0; lo <= maxN; k++) {
    const hi = [10, 20, 50][k % 3]! * 10 ** Math.floor(k / 3)
    bins.push([lo, hi])
    lo = hi + 1
  }

  return bins.map(([lo, hi]) => ({
    category: lo === hi ? String(lo) : `${lo}–${hi}`,
    gene_count: counts.reduce((sum, [n, c]) => (n >= lo && n <= hi ? sum + c : sum), 0)
  }))
}
