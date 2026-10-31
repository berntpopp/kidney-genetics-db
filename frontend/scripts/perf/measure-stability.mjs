// Layout-stability + flicker harness; protocol: .planning/specs/2026-10-31-page-stability-protocol.md
// usage (from frontend/): node scripts/perf/measure-stability.mjs <label> <url> [runs=3]
// Per run: fresh context (cold cache), 4x CPU throttle + Fast-4G-ish network via CDP; records every
// layout shift with its sources, session-window CLS (web-vitals rules), LCP and its element, FCP,
// long tasks, and for run 1 a filmstrip (a frame every 100 ms for 4 s) to catch content swaps,
// which flicker without counting as a shift. Output: perf-runs/<label>/ (git-ignored).
// CHROME_PATH=/usr/bin/google-chrome uses an installed Chrome instead of Playwright's download.
/* global PerformanceObserver, performance -- used inside page-evaluated functions */
import { chromium } from 'playwright'
import { mkdirSync, writeFileSync } from 'fs'

const [label, url, runsArg] = process.argv.slice(2)
if (!label || !url) {
  console.error('usage: node scripts/perf/measure-stability.mjs <label> <url> [runs=3]')
  process.exit(2)
}
const runs = Number(runsArg ?? 3)
const outDir = `perf-runs/${label}`
mkdirSync(outDir, { recursive: true })

// Runs in the page before any script: buffered observers see the whole load
const observer = () => {
  window.__perf = { shifts: [], lcp: [], long: [], paints: [] }
  const desc = n => {
    if (!n || !n.tagName) return String(n?.nodeName ?? 'null')
    const id = n.id ? `#${n.id}` : ''
    const cls =
      typeof n.className === 'string'
        ? '.' + n.className.trim().split(/\s+/).slice(0, 3).join('.')
        : ''
    const testid = n.getAttribute?.('data-testid')
      ? `[data-testid=${n.getAttribute('data-testid')}]`
      : ''
    const text = (n.textContent || '').trim().replace(/\s+/g, ' ').slice(0, 40)
    return `${n.tagName.toLowerCase()}${id}${testid}${cls} "${text}"`
  }
  const rect = r => r && [Math.round(r.y), Math.round(r.height)]
  const observe = (type, fn) =>
    new PerformanceObserver(l => l.getEntries().forEach(fn)).observe({ type, buffered: true })
  observe('layout-shift', e =>
    window.__perf.shifts.push({
      t: Math.round(e.startTime),
      v: e.value,
      input: e.hadRecentInput,
      src: (e.sources || []).map(s => ({
        node: desc(s.node),
        from: rect(s.previousRect),
        to: rect(s.currentRect)
      }))
    })
  )
  observe('largest-contentful-paint', e =>
    window.__perf.lcp.push({ t: Math.round(e.startTime), node: desc(e.element), size: e.size })
  )
  observe('longtask', e =>
    window.__perf.long.push({ t: Math.round(e.startTime), d: Math.round(e.duration) })
  )
  observe('paint', e => window.__perf.paints.push({ n: e.name, t: Math.round(e.startTime) }))
}

// web-vitals CLS: largest session window (gaps < 1 s, window <= 5 s), input-driven shifts excluded
const sessionCls = shifts => {
  let max = 0
  let cur = 0
  let start = 0
  let last = -Infinity
  for (const s of shifts.filter(s => !s.input)) {
    if (s.t - last > 1000 || s.t - start > 5000) {
      cur = 0
      start = s.t
    }
    cur += s.v
    last = s.t
    max = Math.max(max, cur)
  }
  return max
}
console.assert(
  sessionCls([
    { t: 0, v: 0.1 },
    { t: 500, v: 0.1 },
    { t: 3000, v: 0.15 }
  ]) === 0.2
)

const browser = await chromium.launch({ headless: true, executablePath: process.env.CHROME_PATH })
const results = []
for (let r = 1; r <= runs; r++) {
  const ctx = await browser.newContext({
    viewport: { width: 1350, height: 940 },
    deviceScaleFactor: 1
  })
  const page = await ctx.newPage()
  const cdp = await ctx.newCDPSession(page)
  await cdp.send('Emulation.setCPUThrottlingRate', { rate: 4 })
  await cdp.send('Network.enable')
  await cdp.send('Network.emulateNetworkConditions', {
    offline: false,
    latency: 150,
    downloadThroughput: (1.6 * 1024 * 1024) / 8,
    uploadThroughput: (750 * 1024) / 8
  })
  await page.addInitScript(observer)
  const frames = []
  const t0 = Date.now()
  await page.goto(url, { waitUntil: 'commit' })
  if (r === 1) {
    for (let i = 0; i < 40; i++) {
      frames.push(await page.screenshot({ type: 'jpeg', quality: 50 }).catch(() => null))
      await page.waitForTimeout(100)
    }
  }
  await page.waitForLoadState('networkidle').catch(() => {})
  await page.waitForTimeout(3000)
  const perf = await page.evaluate(() => window.__perf)
  const nav = await page.evaluate(() => {
    const n = performance.getEntriesByType('navigation')[0]
    return {
      ttfb: Math.round(n.responseStart),
      dcl: Math.round(n.domContentLoadedEventEnd),
      load: Math.round(n.loadEventEnd)
    }
  })
  results.push({
    run: r,
    ...nav,
    fcp: perf.paints.find(p => p.n === 'first-contentful-paint')?.t,
    lcp: perf.lcp.at(-1),
    cls: +sessionCls(perf.shifts).toFixed(4),
    shifts: perf.shifts,
    tbtApprox: perf.long.reduce((a, l) => a + Math.max(0, l.d - 50), 0),
    longTasks: perf.long.length,
    wall: Date.now() - t0
  })
  if (r === 1)
    frames.forEach(
      (f, i) => f && writeFileSync(`${outDir}/frame_${String(i).padStart(2, '0')}.jpg`, f)
    )
  await page.screenshot({ path: `${outDir}/final_run${r}.png`, fullPage: true })
  await ctx.close()
}
await browser.close()
writeFileSync(`${outDir}/results.json`, JSON.stringify(results, null, 2))

const median = key => {
  const v = results
    .map(x => (typeof x[key] === 'object' ? x[key]?.t : x[key]))
    .filter(v => v != null)
    .sort((a, b) => a - b)
  return v[Math.floor(v.length / 2)]
}
console.log(
  JSON.stringify(
    {
      label,
      url,
      runs,
      median: {
        ttfb: median('ttfb'),
        fcp: median('fcp'),
        lcp: median('lcp'),
        cls: median('cls'),
        tbtApprox: median('tbtApprox')
      },
      lcpNode: results[0].lcp?.node
    },
    null,
    1
  )
)
for (const s of results[0].shifts.filter(s => s.v > 0.001))
  console.log(
    `  shift t=${s.t} v=${s.v.toFixed(4)} :: ${s.src.map(x => `${x.node} y${x.from}->${x.to}`).join(' | ')}`
  )
