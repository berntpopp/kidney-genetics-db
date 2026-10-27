# UI/UX audit: repeatable runs

The first audit ran on 2026-10-20 against `2c6bfe9` (v0.5.2). Findings are in
[REPORT-2026-10-20.md](REPORT-2026-10-20.md) and tracked by the issues it links.
Re-run this after fixes and compare against the baseline.

| File | What it is |
|---|---|
| `runs/2026-10-20-baseline.json` | Measured baseline: per-route CLS, overflow, theme flash, console errors, regression checks, Lighthouse |
| `scores-2026-10-20.json` | Expert 0–100 scores per view and dimension (rubric below) |
| `tools/run.mjs` | Measures a run and writes `runs/<label>.json` |
| `tools/compare.mjs` | Diffs two runs or two score files; exits 1 on any regression |

The tools live here rather than in `frontend/`, so the app code is unchanged. They reuse the frontend's installed Playwright and pin Lighthouse through `npx`.

## 1. Measure

```bash
make hybrid-up && make backend          # API on :8000 with the full gene set
cd frontend && npm ci && cd ..          # once: provides Playwright and vite-ssg
node .planning/audits/ui-ux/tools/run.mjs --label after-fixes --runs 2
node .planning/audits/ui-ux/tools/compare.mjs .planning/audits/ui-ux/runs/2026-10-20-baseline.json \
  .planning/audits/ui-ux/runs/after-fixes.json
```

`run.mjs` builds the production bundle into the OS temp dir, so `frontend/dist`
is untouched. It serves the bundle with `tools/serve.mjs`, which mirrors
`nginx.prod.conf`, including `gzip_static`. The run takes about 15 minutes.
Lighthouse runs one route at a time. Close other CPU-heavy work first, because
performance scores vary by about 5 points; `compare.mjs` treats smaller changes
as noise. Load-timing probes are also noisy: `/data-sources` CLS varied from 0.33 to 0.085 between two runs of the same commit, and `themeFlash` on very fast pages can flip. Re-run before trusting a single changed row. Flags: `--skip-build` reuses the last bundle, `--no-lighthouse` runs
probes only (about 5 minutes), and `--port` changes the default 5181.

What it measures, per route × desktop (1440×900) / mobile (390×844) × light/dark (stored preference):

- `cls`: summed layout shift without user input, from load through a full scroll. `topShifts` names the elements that moved.
- `overflowPx`: horizontal page overflow (should be 0).
- `themeFlash`: 1 if the first frame is not dark when dark is stored (should be 0).
- `consoleErrors`: console errors plus uncaught page errors.
- `axe`: axe-core WCAG 2.2 A/AA violations, rule id → failing elements (`axeDetails` names impact and sample targets). `compare.mjs` treats more failing elements, or a rule newly failing on a page the baseline also scanned, as a regression.
- `lighthouse`: category scores, LCP/CLS/TBT, failing accessibility items (axe), contrast items.
- `checks`: 1 = pass, 0 = fail.
  - `prerenderedHtmlForGzipClients`
  - `envConfigForGzipClients`
  - `tierFilterChangesUrl`
  - `adminDirectLoadNotBlank`

Not measured automatically: authenticated admin views, interaction flicker,
screen-reader output, and anything that needs judgment. Those belong to step 2.

## 2. Re-score (expert review)

Score every view 0–100 per dimension and save the result as
`scores-<date>.json` with the same shape as `scores-2026-10-20.json`. Then run
`compare.mjs` on the two score files.

| Dimension | 100 means |
|---|---|
| hierarchy | The primary task and the most important data are obvious within 3 seconds |
| typography | One type scale, readable sizes (≥ 12 px data, ≥ 14 px body), tabular numbers in tables |
| color | WCAG AA in both themes; color only carries meaning, matching the tier/score semantics |
| layout | Consistent spacing rhythm, no orphan gaps or misalignment |
| consistency | Uses the shared shadcn-vue components and tokens; the same pattern behaves the same everywhere |
| interaction | Every control works and gives visible feedback for loading, success, error and empty states |
| ia | Users can find the view and know where they are; labels match how geneticists talk |
| density / dataViz | Scannable at research density; charts are legible, labelled, colorblind-safe and true to the API counts |
| accessibility | 0 axe violations; full keyboard path with visible focus; named controls |
| responsive | Works at 390 px without horizontal scroll; touch targets ≥ 24 px |
| perceivedPerformance / safety | No layout shift or flash; skeletons match the final layout. (Admin: destructive actions confirm and name their effect) |
| copy | Plain, specific, truthful wording; errors say what happened and what to do |
| overall | Weighted mean; interaction, accessibility and density/dataViz/safety count 1.5× |

Method: the Impeccable `critique` and `audit` references (`/impeccable critique <view>`).
Look at screenshots of each view at both viewports and in both themes. Every
score needs one line of evidence: a screenshot or `file:line`. Run three
parallel reviewers on disjoint view groups:

- core: shell, `/`, `/genes`, gene detail, structure, error states
- analytics and info: dashboard, network, data sources, about, FAQ, MCP, 404
- auth and admin: read-only; log in as admin from `backend/.env` without printing the password

Rules for re-runs:

- Score against the rubric, not against the previous number.
- Use the same three-reviewer split.
- Note which issues were fixed since the baseline.
