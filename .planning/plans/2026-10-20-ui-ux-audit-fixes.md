# UI/UX audit fixes — execution record (2026-10-20)

Integration branch `fix/ui-ux-audit-2026-10` (worktree `../kgdb-wt/ui`), base `ce75cee` (v0.5.3).
Source: open issues from the 2026-10-20 UI/UX audit (#312–#329, #334) plus backend #331, #332.
Audit harness: `.planning/audits/ui-ux/`. Rules for agents: no `git stash`, own worktree, owned paths only,
disposable DBs, fail-before/pass-after tests, one Conventional Commit per issue.

Measurement note: the local API on :8000 was started from `main` @ ce75cee with `AUTO_UPDATE_ENABLED=false`
(the default startup resumes a paused annotation pipeline that writes to the dev DB; it was stopped after
~15 s and the pipeline status returned to `paused`).

## Streams

| WS | Issues | Owned paths | Deps | Status | Commits | Review | Tests | Blocker |
|---|---|---|---|---|---|---|---|---|
| W1 build/perf | #312 #313 #328 | vite.config.ts, nginx.prod.conf, App.vue (LogViewer) | — | merged ea509de | 1f28df0 3eaa0f3 0116b67 | Ship (should-fix: beasties dep, CI guard → fixed; rechecked) | vitest 150/150 on int; guard fail-before/pass-after | Lighthouse CLS/FCP pending audit |
| W2 theme/base | #319 #321(base) #320(tokens) | index.html, assets/main.css, main.ts, useAppTheme.ts, ui/sonner/** | — | in progress | | | | #320 designer sign-off |
| W3 data/charts | #314 #315 #325 #324(UpSet) #320(chips) | utils/evidenceTiers.ts, ScoreBreakdown.vue, EvidenceTierBadge.vue, gene/GeneInformationCard.vue, views/About.vue, components/visualizations/**, network/NetworkGraph.vue, views/Dashboard.vue | — | in progress | | | | |
| W4 genes/sources | #316 #323 #324(DataSources) #318(GeneTable/Profile) #320(green) #321(EvidenceCard mdi) | GeneTable.vue, ui/data-table/**, GeneDetail.vue, DataSources.vue, Profile.vue, ui/HoverPopover.vue, EvidenceCard.vue | — | in progress | | | | |
| W5 admin | #317 #327 #326 #318(admin) #321(mdi) | views/admin/**, components/admin/**, Login.vue, DataSourceProgress.vue, useBackupFormatters.ts | — | queued | | | | |
| W6 a11y/polish | #322 #329 | cross-cutting | W1–W5 integrated | queued | | | | |
| W7 backend | network cache key (new issue), #332, #331(seed) | enrichment_service.py, network_analysis.py, network_analysis_service.py, schemas/tests, mcp/contract | — | queued | | | | |

Deferred: #330 #333 #254 #255 #282 (scientific definition), #291 remainder, #208 #250 #289 #249 #1 #26 #28.

## Log
- Pre-fix audit run `runs/pre-ce75cee.json` (2 runs, full DB, 3245 genes). vs 2026-10-20 baseline: `tierFilterChangesUrl` and `adminDirectLoadNotBlank` already pass at ce75cee (fixed by #335); `/about`, `/mcp` desktop CLS 0.39/0.55 → 0 in probes; mobile LCP/TBT +180–290 ms on unrelated routes = noise. Gzip prerender checks still 0.
- Filed #336 (network `@cache` key includes Request object address) for W7.
- W1 merged (ea509de). W3 review: must-fix UpSet set-click count + FAQ/Home vocabulary drift (scope expansion FAQ/Home/NetworkAnalysis approved). W2 review: must-fix dark toasts; follow-up: light `--destructive` 3.65:1 (designer call, not in #320 list).
- W2 merged (3f3eae3; review Ship after toast-theme fix, rechecked). W3 merged (f895ec5; review must-fixes 1–2 + should-fixes 3–5 applied, rechecked Ship). Integration vitest 184/184, lint/format clean.
- Coordinator build on f895ec5: exit 0; no `*.html.gz|br`; inline theme script exactly once in all 8 prerendered pages. FAQ JSON-LD is not in prerendered HTML (also absent at ce75cee; pre-existing, out of scope).
- W5 (admin) and W7 (backend: #336, #332, #331 seed) started.
- W4 merged (a7fc999; review must-fix: skeleton 6→7 sources, fixed, rechecked Ship). Integration vitest 197/197. icons.ts mdi map reassigned to W5.
