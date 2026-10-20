// Diff two audit JSON files (run.mjs output or manual scores.json) and print a Markdown table.
// usage: node .planning/audits/ui-ux/tools/compare.mjs <before.json> <after.json> [--all]
// Exits 1 when any metric regressed, so it can gate a fix PR.
import fs from 'node:fs'

const [beforeFile, afterFile] = process.argv.slice(2)
const showAll = process.argv.includes('--all')
const load = f => JSON.parse(fs.readFileSync(f, 'utf8'))

// Flatten nested objects to "a › b › metric" -> number; arrays (top shifts) are context, not metrics.
const flatten = (obj, prefix = [], acc = {}) => {
  for (const [k, v] of Object.entries(obj)) {
    if (typeof v === 'number') acc[[...prefix, k].join(' › ')] = v
    else if (v && typeof v === 'object' && !Array.isArray(v)) flatten(v, [...prefix, k], acc)
  }
  return acc
}
const LOWER_IS_BETTER = /(cls|overflowPx|themeFlash|consoleErrors|Ms|Violations)$/
const pick = o => ({
  meanOverall: o.meanOverall,
  checks: o.checks,
  pages: o.pages,
  lighthouse: o.lighthouse,
  scores: o.scores
})

const [a, b] = [load(beforeFile), load(afterFile)]
const [fa, fb] = [flatten(pick(a)), flatten(pick(b))]
// Below these deltas a change is measurement noise.
const noise = k => (/cls$/.test(k) ? 0.01 : /Ms$/.test(k) ? 100 : /performance$/.test(k) ? 5 : 0)

const rows = []
let worse = 0
let better = 0
for (const k of Object.keys({ ...fa, ...fb })) {
  const [x, y] = [fa[k], fb[k]]
  if (x === undefined || y === undefined) {
    rows.push([k, x ?? '—', y ?? '—', '', 'new/removed'])
    continue
  }
  const d = y - x
  const sign = LOWER_IS_BETTER.test(k) ? -1 : 1
  const verdict = Math.abs(d) <= noise(k) ? 'same' : d * sign > 0 ? 'better' : 'WORSE'
  if (verdict === 'WORSE') worse++
  if (verdict === 'better') better++
  if (showAll || verdict !== 'same')
    rows.push([k, x, y, (d > 0 ? '+' : '') + Number(d.toFixed(3)), verdict])
}

console.log(`## ${a.label} → ${b.label}\n`)
console.log(
  `${better} better · ${worse} worse · ${rows.length} rows shown${showAll ? '' : ' (unchanged hidden; --all shows them)'}\n`
)
console.log('| Metric | Before | After | Δ | |\n|---|---|---|---|---|')
for (const r of rows.sort((p, q) => (p[4] === 'WORSE' ? -1 : 0) - (q[4] === 'WORSE' ? -1 : 0))) {
  console.log(`| ${r.join(' | ')} |`)
}
process.exit(worse ? 1 : 0)
