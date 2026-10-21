// Repeatable UX audit: production build -> nginx-like server -> Playwright probes + Lighthouse -> one JSON file.
// usage (from the repo root): node .planning/audits/ui-ux/tools/run.mjs --label after-fixes [--skip-build] [--no-lighthouse] [--runs 2]
// Needs the API on :8000 with data (make hybrid-up && make backend). Compare runs with compare.mjs.
import { execFileSync, spawn } from 'node:child_process'
import fs from 'node:fs'
import os from 'node:os'
import path from 'node:path'
import { fileURLToPath } from 'node:url'
import { createRequire } from 'node:module'

const here = path.dirname(fileURLToPath(import.meta.url))
const repo = path.resolve(here, '../../../..')
const frontend = path.join(repo, 'frontend')
// audit tooling lives outside frontend/, so borrow its installed Playwright
const { chromium } = createRequire(path.join(frontend, 'package.json'))('playwright')
const arg = (name, fallback) => {
  const i = process.argv.indexOf(`--${name}`)
  return i === -1 ? fallback : process.argv[i + 1]
}
const flag = name => process.argv.includes(`--${name}`)

const label = arg('label', new Date().toISOString().slice(0, 10))
const out = path.resolve(
  arg('out', path.join(here, '../runs', `${label}.json`))
)
const port = Number(arg('port', 5181))
const runs = Number(arg('runs', 1))
const work = path.join(os.tmpdir(), 'kgdb-ux-audit')
const dist = path.join(work, 'dist')
const base = `http://127.0.0.1:${port}`

export const ROUTES = [
  '/',
  '/genes',
  '/genes/PKD1',
  '/genes/HNF1B',
  '/genes/PKD1/structure',
  '/dashboard',
  '/network-analysis',
  '/data-sources',
  '/about',
  '/faq',
  '/mcp',
  '/login',
  '/forgot-password',
  '/this-does-not-exist'
]
const VIEWPORTS = { desktop: { width: 1440, height: 900 }, mobile: { width: 390, height: 844 } }
const THEMES = ['light', 'dark']

const git = (...a) => execFileSync('git', a, { cwd: repo, encoding: 'utf8' }).trim()
const median = xs => [...xs].sort((a, b) => a - b)[Math.floor(xs.length / 2)]
const round = (x, d = 3) => (x == null ? null : Number(x.toFixed(d)))

if (!flag('skip-build')) {
  console.log('building production bundle into', dist)
  execFileSync('npx', ['vite-ssg', 'build', '--config', path.join(here, 'vite.audit.config.mjs')], {
    cwd: frontend,
    stdio: 'inherit',
    // same-origin /api like production; the audit server proxies it
    env: { ...process.env, UX_AUDIT_DIST: dist, VITE_API_BASE_URL: '' }
  })
}

// Mirror frontend/docker-entrypoint.sh (its defaults): production writes env-config.js and tags every prerendered page at container start.
fs.writeFileSync(
  path.join(dist, 'env-config.js'),
  'window._env_ = { API_BASE_URL: "", WS_URL: "/ws", MCP_BASE_URL: "", ENVIRONMENT: "production", VERSION: "0.2.0" };\n'
)
for (const f of fs.readdirSync(dist, { recursive: true }).filter(f => path.basename(f) === 'index.html')) {
  const file = path.join(dist, f)
  const html = fs.readFileSync(file, 'utf8')
  if (!html.includes('env-config.js')) {
    fs.writeFileSync(file, html.replace('</head>', '  <script src="/env-config.js"></script>\n  </head>'))
  }
}

const server = spawn('node', [path.join(here, 'serve.mjs'), dist, String(port)], {
  stdio: 'inherit'
})
process.on('exit', () => server.kill())
await new Promise(r => setTimeout(r, 800))

// Page probes: layout shift without user input, horizontal overflow, theme at first frame, console errors.
const INIT = `
  window.__cls = 0; window.__shifts = [];
  new PerformanceObserver((l) => { for (const e of l.getEntries()) if (!e.hadRecentInput) {
    window.__cls += e.value;
    const n = e.sources?.[0]?.node;
    window.__shifts.push({ v: e.value, t: Math.round(e.startTime), el: n ? (n.id ? '#' + n.id : n.nodeName + '.' + String(n.className || '').split(' ').slice(0, 3).join('.')) : null });
  } }).observe({ type: 'layout-shift', buffered: true });
  requestAnimationFrame(() => { window.__firstFrameDark = document.documentElement.classList.contains('dark'); });
`
const browser = await chromium.launch()
const pages = {}
for (const route of ROUTES) {
  for (const [vp, viewport] of Object.entries(VIEWPORTS)) {
    for (const theme of THEMES) {
      const ctx = await browser.newContext({ viewport, colorScheme: theme })
      // a stored preference exercises the path the toggle uses, not only the OS setting
      await ctx.addInitScript(t => localStorage.setItem('kgdb-color-mode', t), theme)
      await ctx.addInitScript(INIT)
      const page = await ctx.newPage()
      let errors = 0
      page.on('console', m => m.type() === 'error' && errors++)
      page.on('pageerror', () => errors++)
      await page.goto(base + route, { waitUntil: 'networkidle', timeout: 30000 }).catch(() => {})
      await page.waitForTimeout(1500)
      await page.evaluate(async () => {
        for (let y = 0; y < document.body.scrollHeight; y += 400) {
          window.scrollTo(0, y)
          await new Promise(r => setTimeout(r, 60))
        }
      })
      await page.waitForTimeout(500)
      const m = await page.evaluate(() => ({
        cls: window.__cls,
        shifts: window.__shifts.filter(s => s.v > 0.005).slice(0, 5),
        overflowPx: Math.max(0, document.documentElement.scrollWidth - window.innerWidth),
        firstFrameDark: window.__firstFrameDark
      }))
      pages[`${route} ${vp} ${theme}`] = {
        cls: round(m.cls),
        overflowPx: m.overflowPx,
        ...(theme === 'dark' && { themeFlash: m.firstFrameDark ? 0 : 1 }),
        consoleErrors: errors,
        topShifts: m.shifts
      }
      await ctx.close()
    }
  }
  console.log('probed', route)
}

// Functional regressions found by the 2026-10-20 audit. 1 = pass, 0 = fail.
const checks = {}
{
  // prerendered HTML must reach gzip clients (nginx gzip_static serves index.html.gz)
  const gz = await fetch(base + '/', { headers: { 'accept-encoding': 'gzip' } })
  const html = await gz.text()
  checks.prerenderedHtmlForGzipClients = /<div id="app"[^>]*>\s*<\/div>/.test(html) ? 0 : 1
  checks.envConfigForGzipClients = html.includes('env-config.js') ? 1 : 0

  const ctx = await browser.newContext({ viewport: VIEWPORTS.desktop })
  const page = await ctx.newPage()
  await page.goto(base + '/genes', { waitUntil: 'networkidle' })
  await page.getByRole('button', { name: /^Tiers/ }).click()
  await page.locator('[id^="tier-"]').first().click()
  await page.waitForTimeout(1500)
  checks.tierFilterChangesUrl = page.url().includes('tier=') ? 1 : 0

  await page.goto(base + '/admin/users', { waitUntil: 'networkidle' }).catch(() => {})
  await page.waitForTimeout(3000)
  const text = await page.evaluate(() => document.body.innerText.trim().length)
  checks.adminDirectLoadNotBlank = page.url().includes('/login') || text > 100 ? 1 : 0
  await ctx.close()
}
await browser.close()

// Lighthouse, sequential so runs don't compete for CPU.
const lighthouse = {}
if (!flag('no-lighthouse')) {
  const lhDir = path.join(work, 'lighthouse', label)
  fs.mkdirSync(lhDir, { recursive: true })
  for (const route of ROUTES) {
    for (const form of ['desktop', 'mobile']) {
      const reports = []
      for (let i = 0; i < runs; i++) {
        const file = path.join(lhDir, `${route.replace(/\W+/g, '_') || 'home'}_${form}_${i}.json`)
        execFileSync(
          'npx',
          [
            '-y',
            'lighthouse@12.8.2',
            base + route,
            ...(form === 'desktop' ? ['--preset=desktop'] : []),
            '--chrome-flags=--headless=new --no-sandbox',
            '--output=json',
            `--output-path=${file}`,
            '--quiet'
          ],
          {
            env: {
              ...process.env,
              CHROME_PATH: process.env.CHROME_PATH || '/usr/bin/google-chrome'
            },
            stdio: 'ignore'
          }
        )
        reports.push(JSON.parse(fs.readFileSync(file, 'utf8')))
      }
      const pick = f => median(reports.map(f))
      const failedA11y = r =>
        r.categories.accessibility.auditRefs.map(a => r.audits[a.id]).filter(a => a.score === 0)
      lighthouse[`${route} ${form}`] = {
        performance: pick(r => Math.round(r.categories.performance.score * 100)),
        accessibility: pick(r => Math.round(r.categories.accessibility.score * 100)),
        bestPractices: pick(r => Math.round(r.categories['best-practices'].score * 100)),
        seo: pick(r => Math.round(r.categories.seo.score * 100)),
        lcpMs: pick(r => Math.round(r.audits['largest-contentful-paint'].numericValue)),
        fcpMs: pick(r => Math.round(r.audits['first-contentful-paint'].numericValue)),
        cls: round(pick(r => r.audits['cumulative-layout-shift'].numericValue)),
        tbtMs: pick(r => Math.round(r.audits['total-blocking-time'].numericValue)),
        a11yViolations: pick(r =>
          failedA11y(r).reduce((n, a) => n + (a.details?.items?.length || 1), 0)
        ),
        contrastViolations: pick(r => r.audits['color-contrast'].details?.items?.length || 0)
      }
      console.log('lighthouse', route, form, lighthouse[`${route} ${form}`].performance)
    }
  }
}

fs.mkdirSync(path.dirname(out), { recursive: true })
fs.writeFileSync(
  out,
  JSON.stringify(
    {
      label,
      date: new Date().toISOString(),
      commit: git('rev-parse', '--short', 'HEAD'),
      dirty:
        git('status', '--porcelain', '--', 'frontend').length > 0,
      lighthouseRuns: runs,
      checks,
      pages,
      lighthouse
    },
    null,
    2
  ) + '\n'
)
console.log('wrote', out)
process.exit(0)
