# Audit 2026-10 bug fixes — execution record

Integration branch `fix/audit-2026-10-bugfixes`, base `dd3e43bb8bd7a4b3e9c4f48746db30be471df4d3` (= origin/main).
Baseline on disposable PostgreSQL 17.11: `pytest tests/` 691 passed / 10 skipped (data-dependent skips: empty gene table, missing statistics view).

| Issue | Stream/owner | Owned paths | Depends on | Status | Commits | Review | Tests | Blocker |
|---|---|---|---|---|---|---|---|---|
| #285 | A | middleware, main.py | – | integrated cd249a7 | a169b64 db80aa1 | approved after recheck | log-redaction tests | |
| #286 | A (+C UI, G snapshot) | genes/datasources/gene_staging endpoints, staging schema | – | integrated | 0254a13 ed2eb51 a80319d f4eda57 | approved | role tests | |
| #290 | A (+C UI) | auth.py, database_init.py, auth store | – | integrated | 55f1d5e 9deefd5 750fc4f | approved | revocation tests | |
| #293 | B | cache_service, conftest, gene_normalizer | – | integrated 6df734f | 277cce6 c2c4ac6 8451e42 142c1bb f230005 | approved | interleaved two-owner, thread, 1 s idle guard | |
| #292 | B | data_source_base, crud/gene | – | integrated | fdace33 954ab5d | approved | real-PG savepoint | |
| #296 #297 | B | cache_service, unified/base | #293 | integrated | a4381e7 6404d6d | approved | clock/namespace | |
| #291 | B | data_source_base | #292 | integrated (shared-base sources) | f13125a 1c4dc65 | approved | fetch/empty/write failure, prune | PubTator update_data still deletes before streaming (needs resume/completeness decision) |
| #294 | B | annotation_pipeline | #293 | integrated | 496d0c6 4bf9bcc | approved | bulk + fallback failures | |
| #295 | B | annotation_pipeline | – | integrated | cb1cd0f | approved | checkpoint | |
| #298 #303 #299 #300 #301 #302 #304 #278 | C | frontend, evidence null (genes.py, evidence_transform) | A | integrated bac3137 | 4bbe414 97110ac 85fa9fe fdd5638 0505821 c0152e0 f400f32 0a18e9c 2994671 f96645d ed582c3 44268ad | approved after recheck | vitest + backend null test | |
| #305 #306 #307 #308 | D | mcp/src, mcp/tests | – | integrated c0aac57 | 61ebd36 7876450 96c7bb5 ee3108a | approved | 210 mcp; #308 benchmark 368→13 serializations | |
| #309 #310 | E | scrapers utils + callers | – | integrated b755cb8 | d5ae2fc d4a60f1 fac3dcf | approved after recheck | lit 13, diag 14 | |
| #287 #280 #281 | F (+G migration 0004) | network service, diagnostic_panels, pubtator, PubTatorEvidence | B, C | integrated bb9829c | b33ead4 7ee7a61 45e07d5 f1495b5 be372a2 | approved after recheck | real-PG + vitest | #280 existing rows need operational repair (below) |
| #279 #253 | G | views, alembic 0002/0003, network schema, counters, contract | A–F | integrated 761257a | ffb9043 56c01cf | approved | SQL + upgrade-from-0001 tests | |
| #288 | H (G owner) | release_service, releases endpoint | G | integrated 761257a | 771dbb3 5dd3649 67a14bd 05bc8b5 e0b7f6d | approved after 2 rechecks | two-release + sidecar tests | closed ranges need operational repair (below) |
| #208 #250 #289 | conditional | – | evidence | deferred | | | | #208 no agreed limit or perf/provider check; #250 no verified trusted-peer boundary; #289 no documented unannotated/out-of-universe policy |
| #249 #254 #255 #282 #1 #26 #28 | deferred | – | – | deferred | | | | production evidence / scientific definition / validation design / feature work |

## Review log
- A (dd3e43b..0254a13) ponytail-review: meets AC for #285/#290/#286. Should fix: (1) settings-update body (jwt secret) logged → disable request-body logging; (2) staging reviewer input ignored → remove schema field + UI input; nice: (3) ADMIN_FORCE_PASSWORD_RESET keeps refresh token; (4) self password change silently logs out later → frontend logout. 1–3 sent back to A; 2(UI) and 4 queued for frontend owner C.
- A recheck (0254a13..9deefd5): Verdict Ship. Integrated as cd249a7.
- D (cd249a7..96c7bb5) review: meets AC #305/#306/#307/#308; Verdict Ship. Nice-to-have Redis back-off for silent host: not done (default deploy has no Redis; latency only, loop not blocked). README fallback note added (ee3108a). Integrated c0aac57; `make -C mcp check` 210 passed, contract-verify 0.
- C (dd3e43b..750fc4f) review: meets AC except #299 (missing user/staging control tests) and #278 (API reports missing normalized score as 0.0). Both sent back to C (backend null change: genes.py/evidence_transform.py ownership extended to C).
- B author follow-ups: cache test cleanup moved to conftest autouse (8451e42; #293 made cache writes commit outside test rollbacks); evidence insert savepoint (954ab5d). PubTator full mode still deletes before streaming (own update_data) → follow-up issue.
- C recheck (750fc4f..ed582c3): Ship; #278/#299/#304 meet AC. Integrated bac3137 (after A, so staging reviewer = current user). Coordinator fix 44268ad: spec lint (`HTMLButtonElement` undeclared global → HTMLElement). Int frontend gate: lint/format/build OK, vitest 24 files/143 passed.
- E review (ee3108a..d4a60f1): #310 normalizer meets AC; #309/#310 output status still "not_found" → fixed fac3dcf (status helper + null response); recheck pending.
- B review (dd3e43b..8451e42): Must fix fallback commit swallow (#294 sister path); should fix batch-commit error count, test-DB binding of cache SessionLocal; PubTator full-mode up-front delete (#291) attempted by B; idle-in-transaction risk under investigation.
- Process incident: git stash is shared across worktrees; E/C stashes swapped. Recovered from saved patch, both trees verified; rule added: no git stash.
- Ordering: G (#279/#253) and H (#288) both touch app/db/views.py + Alembic chain → one owner, sequential (G then H).
- E recheck (d4a60f1..fac3dcf): approve; #309/#310 meet AC. Integrated b755cb8; literature 13 passed, diagnostics 14 passed (`uv run --no-project --with pytest --with pyyaml`).
- B follow-ups: 4bf9bcc fallback re-raise (#294), 142c1bb conftest binds SessionLocal to test engine, 1c4dc65 batch-commit errors counted (#291), f230005 normalizer SET LOCAL idle_in_transaction_session_timeout=0 before HGNC await (regression exposed by #293, demonstrated with 1 s guard). PubTator full-mode up-front delete: BLOCKED (resume would drop pre-interruption PMIDs; no completeness signal; "full" ambiguous) → follow-up, #291 closed for shared-base sources only.
- B recheck (8451e42..f230005): Ship; #291 (shared-base), #292–#297 meet AC. Integrated 6df734f. Int backend: ruff OK, full suite 727 passed / 10 skipped (baseline skips), cache_entries 0 rows after.
- F started (worktree f @6df734f, kgdb_c). G+H started sequentially in one owner (worktree g @6df734f, kgdb_g*); file sets disjoint from F.
- F review (6df734f..45e07d5): #287 meets AC. #281 partial → TS/MCP field docs (F) + data migration stripping ", N mentions" from stored PubTator source_detail (G, last revision). #280 partial → repair procedure documented below.
- Follow-up found by F reviewer (out of scope): network endpoint `@cache` keys include `str(request)` with an object memory address → never hits, writes a new cache row per request.

## Operational repair: #280 already-seeded diagnostic records (not executed)
Records seeded before the fix store a pseudo-provider `Seeded from <n> files` (n = files loaded in that run); merge never removes it. Order matters:
1. Read the exact pseudo-provider string from the DiagnosticPanels `providers` list in `/api/datasources`.
2. Re-upload each provider's authoritative file via `POST /api/ingestion/DiagnosticPanels/upload` with `provider_name=<real provider>` and `mode=merge`. The seeder only runs when `needs_initial_seeding` is true, so do not rely on it.
3. Then `DELETE /api/ingestion/DiagnosticPanels/identifiers/<URL-encoded pseudo-provider>`. It drops a record only when no other provider remains, otherwise removes just that name; before step 2 it would delete records whose only provider is the pseudo-provider.
4. Verify the `/api/datasources` DiagnosticPanels provider count equals the real provider names.
Limit: the delete keeps panel lists; a seeded panel absent from the re-uploaded files stays on the gene under the remaining providers (harmless when the authoritative files are the seeded files).

## Operational repair: #288 genes closed by earlier publishes (not executed; needs authorization)
Before the fix, publishing set `valid_to = published_at` on current genes, hiding them from `genes_current` and later exports. Releases' export files are immutable and stay untouched.
1. Backup first (`make db-backup-full`).
2. Dry run: list gene rows whose `valid_to` equals a published release's `published_at` and whose `hgnc_id` has no other current row; check per-release counts against `data_releases.gene_count` and the IDs in that release's export.
3. After review, in one transaction set `valid_to = 'infinity'` for exactly those IDs, then `POST /api/annotations/refresh-view`.
Never reopen rows by any broader predicate. Local dev DB had 0 such rows; production not checked.
- G review (6df734f..f4eda57): #279, #253, 0004 (#281 data), f4eda57 (#286 snapshot sync) meet AC. #288 partial: must fix whole-export load on public endpoint (OOM), should fix 400+path leak on integrity errors and gene_count race; sent back to G.
- G recheck: Ship (e0b7f6d). Integrated 761257a. Migrations: existing kgdb_int 0001→0004 OK; fresh DB up 4 / down 3 / up 3 OK; 0001 unchanged. Combined A–F cross-stream review: no integration defects.
