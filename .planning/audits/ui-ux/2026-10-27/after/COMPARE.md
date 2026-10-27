# Re-audit after the Evidence Ledger redesign (2026-10-27)

Branch `design/evidence-ledger` (HEAD `e10d7fa`), dev server :5199, backend :8000 with the full dataset. 29 views at 1440×900 and 390×844, light and dark (116 full-page captures), plus admin logged in with every non-GET request blocked (0 blocked, 0 attempted). Same rubric as the baseline (README §2); interaction, accessibility and density/safety weigh 1.5×.

Scripts and PNGs: `/tmp/claude-1000/-home-bernt-popp-development-kidney-genetics-db/87ac1b24-b55e-47f3-98f3-cc37d8f59427/scratchpad/reaudit/` (`capture.mjs`, `results-*.json`, `sheet-*.png`, `grid-*.png`).

**Environment caveat.** The :8000 backend was started at 16:22, before `c61676a` (17:15, stats definitions). The Dashboard Overlaps crash, "0% of Genes with 2+ Sources" and "Literature 0 publications" on Data Sources come from that stale backend. With the missing field injected, the UpSet chart renders correctly. The Data Sources numbers were not re-verified. Restart the backend and re-check both views.

## Scores (overall)

| View | Baseline | After | Δ |
|---|---|---|---|
| `Shell` | 64 | 85 | +21 |
| `/` | 65 | 86 | +21 |
| `/genes` | 61 | 84 | +23 |
| `/genes/:symbol` | 53 | 85 | +32 |
| `/genes/:symbol/structure` | 60 | 81 | +21 |
| `Error states` | 73 | 85 | +12 |
| `/dashboard` | 61 | 79 | +18 |
| `/data-sources` | 62 | 84 | +22 |
| `/network-analysis` | 59 | 80 | +21 |
| `/curation/associations` | 64 | 83 | +19 |
| `/about` | 62 | 86 | +24 |
| `/faq` | 74 | 86 | +12 |
| `/mcp` | 70 | 85 | +15 |
| `/login` | 75 | 87 | +12 |
| `/forgot-password` | 69 | 86 | +17 |
| `/reset-password` | 72 | 86 | +14 |
| `/profile` | 70 | 84 | +14 |
| `/this-does-not-exist` | 77 | 85 | +8 |
| `/admin` | 56 | 85 | +29 |
| `/admin/users` | 64 | 83 | +19 |
| `/admin/cache` | 62 | 83 | +21 |
| `/admin/logs` | 61 | 80 | +19 |
| `/admin/pipeline` | 63 | 82 | +19 |
| `/admin/staging` | 56 | 82 | +26 |
| `/admin/annotations` | 55 | 81 | +26 |
| `/admin/releases` | 65 | 84 | +19 |
| `/admin/backups` | 65 | 84 | +19 |
| `/admin/settings` | 63 | 82 | +19 |
| `/admin/hybrid-sources` | 60 | 82 | +22 |
| **Mean** | **64.2** | **83.6** | **+19.4** |

## Automated checks (all 29 views × 4 configs)

| Check | Result |
|---|---|
| C1 cursor: interactive elements without `cursor: pointer` | 0 of 10–128 per view, all configs (base rule `assets/main.css:227-245`) |
| C2 header: bounding box across routes | x=0, logo x=104.5 in every frame of `/→/genes`, `/about→/genes`, `/→/dashboard`, `/genes→/about` (~150 rAF samples each) |
| C10 horizontal page overflow at 390 px | 0 on every view; wide tables scroll inside their container |
| Contrast scan (leaf text, effective background) | Only 10 px step badges on Network (3.7:1) and decorative "\|" separators on Structure (1.8:1) |
| Console errors | Only `POST /client-logs` 404 (`logService.ts:235` misses the `/api` prefix) |
| Dark theme tokens | `--background oklch(0.176 0.014 258.4)`, `--card 0.22`, `--muted 0.267`, `--border 0.33`, blue-grey hue 252–258 |

## Originally reported bugs

| Bug | Status | Evidence |
|---|---|---|
| Header shifts `/` → `/genes` (C2) | **Fixed** | `scrollbar-gutter: stable` plus no out-in transition (`App.vue:70`). The header x/width stayed the same in all sampled frames, with scrollbars visible. |
| Default cursor on buttons and cards (C1) | **Fixed** | 0 failures across all views. Share, Export, Copy and the evidence-card "Show details" toggles report `pointer`. Tooltip-only chips use `auto`, which is correct because they are not clickable. |
| One Evidence card anatomy on `/genes/HNF1B` (C5) | **Fixed** | All 6 cards share `EvidenceCard`: h3 16px/600, 12px 16px padding, 102px header, a classification chip where it applies, `Score n%` chip, summary, stat row and a "Last updated · View on …" footer (`hnf1b-evidence-*.png`). Diagnostic panels has no footer link (P3). |
| Chips have no hover info (C4) | **Fixed** | Hovering shows a tooltip on every chip tested: "Definitive: Gene-disease relationship replicated…" and "Source score (0–100%): percentile rank…". The chips are keyboard-focusable. |
| HPO card shows bare IDs (C3) | **Partly fixed** | 24 of 41 HNF1B terms now show "name + HP:ID". **17 are still bare IDs** (HP:0000069 … HP:0100542), see `HPOEvidence.vue:20-27` (P2). |
| MONDO section looks poor (C3/C11/C12) | **Fixed (component); unverified with data** | Local DB has no MONDO annotation for HNF1B. The empty state is `DataState` with an icon, a reason and Retry. The code renders a name-first `OntologyTerm`, deduped and sorted source IDs, source chips with tooltips, and release/licence attribution. The empty copy contradicts the MONDO IDs shown in the GenCC/ClinGen cards (P3). |
| Dark mode is near-black (C8) | **Fixed** | GitHub-like blue-grey: canvas ≈ #0d1117, sheet ≈ #161b22, borders ≈ #30363d (`crop-exp-d0.png`, `grid-admin-dark.png`). The strength ramp is reversed so the strongest step is lightest. |

Other baseline P1s confirmed fixed by inspection: shared status tokens, no violet secondary or red admin role, raw palette classes gone (Token-Only Rule), admin cards are links with live status, Data Sources headers are readable, the gene header shows the HGNC name and MANE transcript, ClinGen/GenCC summaries are no longer duplicated or truncated, gene-specific "View on …" links, About covers methodology/releases/citation, and the forgot-password copy is consistent.

## Top remaining issues (`after/findings.json`, 14 total: 0 P0, 0 P1, 3 P2, 11 P3)

1. **P2** `dash-upset-crashes-on-missing-field`: `UpSetChart.vue:224-227` has no guard and `ErrorBoundary.vue:71-72` shows the raw exception. `OverlapStatistics` (`backend/app/schemas/statistics.py:25-31`) lacks `single_source_genes`.
2. **P2** `gene-hpo-partial-bare-ids`: `HPOEvidence.vue:20-27`.
3. **P2** `dates-four-formats`: en-GB, en-CA, en-US and locale-default dates across Home, Data Sources, evidence and admin.
4. **P3** `client-logs-wrong-path`: `logService.ts:235`.
5. **P3** MONDO empty-state copy, 10 px chart/badge text (Network, Structure), HGNC link affordance, mobile table scroll cue, admin carry-overs (empty log columns, pipeline staleness, staging limited to 200), PanelApp raw inheritance strings, Diagnostic panels provider/footer.

Not covered: axe/Lighthouse runs, screen-reader output, admin confirmation dialogs (no state-changing clicks), and the network graph after Filter → Build → Cluster (only the empty state was reviewed).
