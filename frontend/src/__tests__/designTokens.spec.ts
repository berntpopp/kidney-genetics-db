/**
 * The Token-Only Rule (DESIGN.md): no raw Tailwind palette classes, hex/rgb()/hsl() colour
 * literals or hsl(var(--token)) in components. Existing offenders are frozen in
 * design-token-baseline.json; a file whose count goes up, or a new offending file, fails.
 * After migrating a file, lower the baseline:
 *   UPDATE_DESIGN_TOKEN_BASELINE=1 npx vitest run src/__tests__/designTokens.spec.ts
 */
import { readdirSync, readFileSync, writeFileSync } from 'node:fs'
import { describe, it, expect } from 'vitest'

const BASELINE_PATH = 'src/__tests__/design-token-baseline.json' // cwd = frontend/

const PATTERNS = {
  palette:
    /\b(?:bg|text|border|ring|fill|stroke|from|via|to|outline|decoration|divide|placeholder|accent|caret|shadow)-(?:red|orange|amber|yellow|lime|green|emerald|teal|cyan|sky|blue|indigo|violet|purple|fuchsia|pink|rose|slate|gray|zinc|neutral|stone)-\d{2,3}\b/g,
  hex: /(?<![\w&/])#(?:[0-9a-fA-F]{8}|[0-9a-fA-F]{6}|[0-9a-fA-F]{3,4})\b/g,
  colorFn: /\b(?:rgba?|hsla?)\(/g,
  hslVar: /hsl\(\s*var\(--/g
} as const
type Kind = keyof typeof PATTERNS
type Counts = Partial<Record<Kind, number>>

// The config modules are where colours are defined
const EXCLUDED = new Set([
  'src/utils/evidenceTiers.ts',
  'src/utils/sources.ts',
  'src/utils/status.ts'
])

/**
 * Files exempt because a library needs literal colour input. Each entry needs a reason;
 * prefer resolveCssColor() from utils/sources.ts over adding one.
 */
const ALLOWLIST: Record<string, string> = {}

function countViolations(src: string): Counts {
  const counts: Counts = {}
  for (const [kind, re] of Object.entries(PATTERNS) as [Kind, RegExp][]) {
    const n = src.match(re)?.length ?? 0
    if (n) counts[kind] = n
  }
  return counts
}

function scan(): Record<string, Counts> {
  const result: Record<string, Counts> = {}
  const files = readdirSync('src', { recursive: true, encoding: 'utf8' })
    .map(f => `src/${f.replaceAll('\\', '/')}`)
    .filter(f => /\.(vue|ts)$/.test(f) && !/(__tests__\/|\.spec\.ts$|\.test\.ts$|\.d\.ts$)/.test(f))
    .filter(f => !EXCLUDED.has(f) && !(f in ALLOWLIST))
    .sort()
  for (const file of files) {
    const counts = countViolations(readFileSync(file, 'utf8'))
    if (Object.keys(counts).length) result[file] = counts
  }
  return result
}

describe('design tokens (Token-Only Rule)', () => {
  it('detects each kind of raw colour', () => {
    expect(
      countViolations(
        `class="bg-red-500 hover:text-gray-600/50" :style="{ color: '#16a34a' }" fill="rgb(1,2,3)" style="color: hsl(var(--primary))"`
      )
    ).toEqual({ palette: 2, hex: 1, colorFn: 2, hslVar: 1 })
    expect(
      countViolations(`class="bg-strength-5 text-success" href="#!/hgnc_id" '&#123;' url/#abc`)
    ).toEqual({})
  })

  it('no file adds raw colours beyond the baseline', () => {
    const current = scan()
    if (process.env.UPDATE_DESIGN_TOKEN_BASELINE) {
      writeFileSync(BASELINE_PATH, JSON.stringify(current, null, 2) + '\n')
    }
    const baseline = JSON.parse(readFileSync(BASELINE_PATH, 'utf8')) as Record<string, Counts>
    const regressions: string[] = []
    for (const [file, counts] of Object.entries(current)) {
      for (const [kind, n] of Object.entries(counts) as [Kind, number][]) {
        const allowed = baseline[file]?.[kind] ?? 0
        if (n > allowed) regressions.push(`${file}: ${kind} ${allowed} -> ${n}`)
      }
    }
    expect(regressions, 'Use tokens (DESIGN.md Token-Only Rule)').toEqual([])
  })
})
