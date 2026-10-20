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
| W1 build/perf | #312 #313 #328 | vite.config.ts, nginx.prod.conf, App.vue (LogViewer) | — | in progress | | | | |
| W2 theme/base | #319 #321(base) #320(tokens) | index.html, assets/main.css, main.ts, useAppTheme.ts, ui/sonner/** | — | in progress | | | | #320 designer sign-off |
| W3 data/charts | #314 #315 #325 #324(UpSet) #320(chips) | utils/evidenceTiers.ts, ScoreBreakdown.vue, EvidenceTierBadge.vue, gene/GeneInformationCard.vue, views/About.vue, components/visualizations/**, network/NetworkGraph.vue, views/Dashboard.vue | — | in progress | | | | |
| W4 genes/sources | #316 #323 #324(DataSources) #318(GeneTable/Profile) #320(green) | GeneTable.vue, ui/data-table/**, GeneDetail.vue, DataSources.vue, Profile.vue, ui/HoverPopover.vue | — | queued | | | | |
| W5 admin | #317 #327 #326 #318(admin) #321(mdi) | views/admin/**, components/admin/**, Login.vue, DataSourceProgress.vue, useBackupFormatters.ts | — | queued | | | | |
| W6 a11y/polish | #322 #329 | cross-cutting | W1–W5 integrated | queued | | | | |
| W7 backend | network cache key (new issue), #332, #331(seed) | enrichment_service.py, network_analysis.py, network_analysis_service.py, schemas/tests, mcp/contract | — | queued | | | | |

Deferred: #330 #333 #254 #255 #282 (scientific definition), #291 remainder, #208 #250 #289 #249 #1 #26 #28.

## Log
- Pre-fix audit run `runs/pre-ce75cee.json` (2 runs, full DB, 3245 genes). vs 2026-10-20 baseline: `tierFilterChangesUrl` and `adminDirectLoadNotBlank` already pass at ce75cee (fixed by #335); `/about`, `/mcp` desktop CLS 0.39/0.55 → 0 in probes; mobile LCP/TBT +180–290 ms on unrelated routes = noise. Gzip prerender checks still 0.
- Filed #336 (network `@cache` key includes Request object address) for W7.
