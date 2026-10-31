# Page stability and load protocol (gene pages)

How we measure layout shift, flicker and load speed, so before/after claims are comparable.
First used for `/genes/:symbol` and `/genes/:symbol/structure` (2026-10-31).

## Why two tools

- **Lighthouse** (lab) scores load metrics but stops at the load event and ranks the
  largest paint of whatever is on screen, even another page's content.
- **`frontend/scripts/perf/measure-stability.mjs`** records every `layout-shift` entry with
  its source nodes, session-window CLS (web-vitals rules: gaps under 1 s, windows up to 5 s,
  input-driven shifts excluded), the LCP element, and a filmstrip (a frame every 100 ms for
  4 s). The filmstrip catches content swaps: replaced nodes flicker without counting as a shift.

## Protocol

1. Measure the **production image** (`docker build` of `frontend/`), served by its own
   `nginx.prod.conf` with only the upstream and listen port swapped to a local backend with
   real data. The Vite dev server has no SPA fallback, gzip or CSP and is not representative.
2. Build **before** (`git archive HEAD:frontend`) and **after** images the same way; run them
   side by side.
3. Quiet machine: no builds or other agents running; run the variants one after the other.
4. Lighthouse 12, `--only-categories=performance`, 5 runs each for mobile (default throttling)
   and `--preset=desktop`; report the **median**.
5. Stability harness, 5 runs (fresh context, 4x CPU, ~1.6 Mbps / 150 ms):
   `CHROME_PATH=/usr/bin/google-chrome node scripts/perf/measure-stability.mjs <label> <url> 5`
   from `frontend/`. Output goes to `frontend/perf-runs/` (git-ignored). Report median CLS,
   the shift sources and the LCP element, and look at the filmstrip frames.
6. Verify the LCP element is the page's own content before reading the LCP number.

## Results 2026-10-31 (HNF1B, local production image, real data)

| Metric | Before | After |
|---|---|---|
| Gene page CLS, harness | 0.0602 | 0.0008 |
| Gene page CLS, Lighthouse desktop / mobile | 0.062 / 0.181 | 0.001 / 0.023 |
| Structure page CLS, harness / Lighthouse mobile | 0 / 0.019 | 0 / 0 |
| 3D view CLS, harness | n/a | 0 |
| Home page painted on a gene deep link | ~800 ms (4x CPU) | none |
| LCP element | Home logo text | gene evidence summary |

Root cause of the flicker: nginx answered every client-only route with the prerendered Home
page (`try_files ... /index.html`), which painted and was then replaced on mount. The fallback
is now `/app-shell/index.html` (header and footer, empty viewport-tall main). LCP numbers before
the fix timed the Home page, so they are not comparable with the after numbers.

## Open

- Gene page mobile CLS 0.023 (Lighthouse) not yet attributed.
- `/api/genes/{symbol}/evidence` takes ~470 ms in production: the `combined_evidence_scores`
  view recomputes normalisation over all genes per request. Candidate for a materialized view
  (schema change, needs an Alembic migration).
