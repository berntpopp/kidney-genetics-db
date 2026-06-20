# Kidney-Genetics-DB MCP Server — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: superpowers:subagent-driven-development (parallel waves). Steps use checkbox (`- [ ]`) syntax. Spec: `.planning/specs/2026-06-20-mcp-server-design.md`. **Reference implementation to copy patterns from:** `/home/bernt-popp/development/hnf1b-db/mcp/` (same stack, near-1:1 template). Read the analogous hnf1b file before writing each module.

**Goal:** Ship `kidney-genetics-mcp`, a standalone read-only FastMCP HTTP sidecar exposing the KGDB gene database to MCP clients, GeneFoundry-fleet-compatible.

**Architecture:** FastMCP 2.x streamable-HTTP sidecar (`mcp/` in-repo). Thin tools → fat services → allowlisted httpx client against the public KGDB REST API (`:8000`). One backend addition: `GET /api/genes/resolve`. Zero DB/schema coupling.

**Tech Stack:** Python 3.11+, `uv`, FastMCP ≥2.3, httpx, pydantic v2 + pydantic-settings, redis (optional), ruff + mypy (strict), pytest + respx. Backend: FastAPI + sync SQLAlchemy.

## Global Constraints

- Tool prefix `kgdb_`; package `kidney_genetics_mcp`; console script `kidney-genetics-mcp`; env prefix `KGDB_MCP_`; port `8789`; protocol version `2025-11-25`.
- Every tool: `readOnlyHint=True, idempotentHint=True, openWorldHint=False` + human `title`.
- Response modes: `minimal|compact|standard|full` → char budgets `{4000,12000,24000,48000}`, hard cap `80000`, default `compact`.
- Error codes (exactly 4): `invalid_input`, `not_found`, `ambiguous_query`, `temporarily_unavailable`. Envelope `{schema_version:"1.0", error:{code,message,...}}`, `is_error=True`.
- Success envelope: payload + `data_class` + `meta{response_mode,effective_chars,elapsed_ms,truncated?}`.
- Citation: `recommended_citation` with date-confidence gating; cite per-source version + data-release version + DOI + concept DOI `10.5281/zenodo.19316248`.
- Safety: "research use only, not clinical decision support" + injection notice in instructions + capabilities + tool-guide. Read-only allowlist is the enforced boundary.
- No writes/admin/auth/pipeline surfaces; no live external calls (Enrichr deferred).
- Gates: `ruff check`, `mypy src/` strict, `pytest` cov ≥80, `-m 'not live'` in CI.
- KGDB API: routers carry `/api/` prefix; base URL `http://localhost:8000` (compose `http://backend:8000`). All GET reads are public (no auth). `gene_crud.get_by_symbol` / `get_by_hgnc_id` exist in `backend/app/crud/gene.py`.

---

## File Structure & Ownership (parallel-safe partition)

```
mcp/
  pyproject.toml  Makefile  Dockerfile  Dockerfile.prod  README.md  .env.example
  scripts/gen_contract.py
  contract/openapi.snapshot.json
  src/kidney_genetics_mcp/
    __init__.py
    config.py                       [Wave1-plumbing]
    server.py                       [Wave1-plumbing]
    server_ratelimit.py             [Wave1-plumbing]
    client/__init__.py
    client/allowlist.py             [Wave1-plumbing]
    client/api_client.py            [Wave1-plumbing]
    contract/__init__.py            [Wave0-scaffold, generated]
    contract/_generated_*.py        [Wave0-scaffold, generated]
    services/__init__.py
    services/shaping.py             [Wave1-plumbing]
    services/safe_tool.py           [Wave1-plumbing]
    services/errors.py              [Wave1-plumbing]
    services/dataclass.py           [Wave1-plumbing]
    services/citation.py            [Wave1-plumbing]
    services/capabilities.py        [Wave2-D]
    services/resources.py           [Wave2-D]
    services/resolve.py             [Wave2-A]
    services/genes.py               [Wave2-A]
    services/evidence.py            [Wave2-A]
    services/annotations.py         [Wave2-B]
    services/network.py             [Wave2-B]
    services/statistics.py          [Wave2-C]
    services/sources.py             [Wave2-C]
    services/releases.py            [Wave2-C]
    tools/__init__.py               [Wave1-plumbing: static _MODULES = all 4 families + capabilities]
    tools/genes.py                  [Wave2-A]  (resolve, search, get_gene, evidence)
    tools/annotations.py            [Wave2-B]  (annotations, constraint, interaction_partners)
    tools/statistics.py             [Wave2-C]  (database_stats, list_sources, release_citation)
    tools/capabilities.py           [Wave2-D]  (get_capabilities + register resources)
    resources/schema_overview.md    [Wave2-D]
    resources/tool_guide.md         [Wave2-D]
  tests/                            each family owns its test files
backend/  (Wave1-backend, independent)
  app/crud/gene.py        (modify: add resolve_query)
  app/api/endpoints/genes.py (modify: add GET /resolve)
  tests/test_gene_resolve.py (create)
```

**Coordination rules that make waves parallel-safe:**
- `tools/__init__.py` (Wave 1) defines `_MODULES = ("genes","annotations","statistics","capabilities")` and `register_all` imports each and calls `.register(mcp, client)`. Wave 2 agents **create** their module files; they never edit `__init__.py`. No merge conflicts.
- `services/__init__.py` stays empty of cross-imports; each service imports cross-cutting helpers from `services.shaping/safe_tool/errors/citation/dataclass` (Wave 1). Wave 2 agents only **add** their own service files.
- Each Wave 2 agent owns disjoint files (its `tools/<x>.py`, its `services/<y>.py`, its `tests/test_*`), so they run concurrently in the same workspace without collisions.

---

## WAVE 0 — Scaffold + Contract (BLOCKING; one agent, must finish first)

### Task 0.1: Package scaffold

**Files:** Create `mcp/pyproject.toml`, `mcp/src/kidney_genetics_mcp/__init__.py`, `mcp/.env.example`, `mcp/Makefile`.

- [ ] **Step 1:** Copy `/home/bernt-popp/development/hnf1b-db/mcp/pyproject.toml` and adapt: name `kidney-genetics-mcp`, package `kidney_genetics_mcp`, script `kidney-genetics-mcp = "kidney_genetics_mcp.server:main"`, keep `fastmcp>=2.3.0, httpx>=0.27, pydantic>=2.7, pydantic-settings>=2.3, redis>=5.0`; dev group `ruff, mypy, pytest, pytest-asyncio, pytest-cov (fail_under=80), pytest-xdist, respx, mcp>=1.2, datamodel-code-generator`. Keep ruff line-length 88, mypy strict, pytest `addopts="-m 'not live'"`, markers `smoke`/`live`.
- [ ] **Step 2:** Write `__init__.py` with `__version__ = "0.1.0"`.
- [ ] **Step 3:** Write `.env.example` listing all §7 env vars with defaults.
- [ ] **Step 4:** Write `Makefile` targets: `install` (`uv sync --group dev`), `check` (`uv run ruff check . && uv run mypy src/ && uv run pytest`), `contract` (`uv run python scripts/gen_contract.py`), `contract-verify` (`make contract && git diff --exit-code contract/ src/kidney_genetics_mcp/contract/`), `run` (`uv run kidney-genetics-mcp`).
- [ ] **Step 5:** `cd mcp && uv sync --group dev` → verify it resolves. Commit `chore(mcp): scaffold package`.

### Task 0.2: Contract generation from KGDB OpenAPI

**Files:** Create `mcp/scripts/gen_contract.py`, `mcp/contract/openapi.snapshot.json`, `mcp/src/kidney_genetics_mcp/contract/__init__.py`, `_generated_paths.py`, `_generated_enums.py`, `_generated_models.py`.

- [ ] **Step 1:** Start the backend (`make hybrid-up && make backend` from repo root, or use a running instance). Fetch `http://localhost:8000/openapi.json` → save to `mcp/contract/openapi.snapshot.json`.
- [ ] **Step 2:** Adapt `/home/bernt-popp/development/hnf1b-db/mcp/scripts/gen_contract.py`: emit `_generated_paths.py` (path constants + `ALL_PATHS` for the genes/annotations/statistics/network/releases/datasources GET routes), `_generated_enums.py` (`Literal` enums + `*_VALUES` tuples for tier, group, sort, sources — pull enum/allowed values from the OpenAPI + the spec's known source lists), `_generated_models.py` (pydantic response models via datamodel-code-generator). `__init__.py` re-exports public names.
- [ ] **Step 3:** Run `make contract`; ensure files generate and import. Exempt generated files from ruff/mypy in pyproject.
- [ ] **Step 4:** Commit `feat(mcp): generate API contract from KGDB OpenAPI`.

> If the live backend is unavailable, generate `_generated_enums.py`/`_generated_paths.py` by hand from the spec's source lists and endpoint table, and snapshot a minimal openapi.json; mark a TODO to regen. Do NOT block downstream waves.

---

## WAVE 1 — Plumbing + Backend (parallel: 1a plumbing, 1b backend)

### Task 1a.1: Config

**Files:** Create `mcp/src/kidney_genetics_mcp/config.py`.
**Produces:** `Settings` (pydantic-settings, `env_prefix="KGDB_MCP_"`), `get_settings()` (cached). Fields per spec §7 + `mode_char_budgets: dict`, `max_response_chars_cap=80000`, `default_response_mode="compact"`, `allowed_origins: list[str]` (CSV `field_validator(mode="before")`), `rate_limit_global_rps=10.0`.

- [ ] Copy hnf1b `config.py`, rename prefix `HNF1B_MCP_`→`KGDB_MCP_`, set `api_base_url` default `http://localhost:8000`, port `8789`. Test `test_config.py`: env override works, CSV origins parse. Commit.

### Task 1a.2: Cross-cutting services — errors, shaping, dataclass, citation, safe_tool

**Files:** Create `services/errors.py`, `services/shaping.py`, `services/dataclass.py`, `services/citation.py`, `services/safe_tool.py`.
**Produces (exact signatures later tasks rely on):**
- `errors.McpToolError(code: str, message: str, **details)` with `.to_envelope() -> dict`; helpers `invalid_input()`, `not_found()`, `ambiguous_query(choices)`, `temporarily_unavailable()`.
- `shaping.ResponseMode = Literal["minimal","compact","standard","full"]`; `project_fields(row, fields_by_mode, mode)`, `sample_with_signal(items, prefix, size=10)`, `apply_budget(payload, max_chars, keep_min=1)`, `build_meta(mode, effective_chars, dropped=None, extra=None)`.
- `dataclass.DataClass` string constants (`gene`, `evidence`, `annotation`, `interaction`, `statistics`, `source`, `release`, `gene_identity`, `operational_metadata`).
- `citation.build_citation(pub: dict) -> dict` (recommended_citation + date_confidence), `build_release_citation(release: dict) -> dict`.
- `safe_tool.run_tool(coro_factory, data_class, response_mode) -> dict` — times, attaches `data_class`+`meta`, catches `McpToolError`→envelope, pops `_dropped`/`_meta`.

- [ ] Copy each from hnf1b `services/{errors,shaping,dataclass,citation,safe_tool}.py`; adapt data_class names + budgets from config. Tests: `test_shaping.py` (projection ladder, sampling signal, budget trim), `test_errors.py` (envelope shape, 4 codes), `test_citation.py` (date-confidence gating), `test_safe_tool.py` (meta attached, error caught). Commit per file group.

### Task 1a.3: Client — allowlist + api_client

**Files:** Create `client/__init__.py`, `client/allowlist.py`, `client/api_client.py`.
**Produces:**
- `allowlist.assert_allowed(method: str, path: str) -> None` (raises `PermissionError`); `ALLOW`/`DENY` regex lists. ALLOW: `^/api/genes/resolve$`, `^/api/genes/?$`, `^/api/genes/[^/]+$`, `^/api/genes/[^/]+/evidence$`, `^/api/annotations/genes/\d+/annotations$`, `^/api/annotations/genes/\d+/annotations/summary$`, `^/api/annotations/sources$`, `^/api/statistics/summary$`, `^/api/datasources/?$`, `^/api/releases/?$`. DENY everything else (admin/auth/staging/ingestion/pipeline/POST network — explicit).
- `api_client.ApiClient(base_url, timeout, cache_ttl)`: `async get(path, params=None) -> dict`; calls `assert_allowed("GET", path)`; in-proc TTL cache keyed on path+sorted params; maps 404→not_found, 422/400/409→invalid_input (with field/allowed/hint when parseable), 300→ambiguous_query, else→temporarily_unavailable; never echoes internal route in messages.

- [ ] Copy hnf1b `client/{allowlist,api_client}.py`; replace path regexes with KGDB's (above); keep error mapping + cache. Tests: `test_allowlist.py` (each allow passes, sample denies raise), `test_api_client.py` (respx-mocked: 200 cache hit, 404→not_found, 422→invalid_input with field). Commit.

### Task 1a.4: Server + middlewares + rate limiter + tools registry skeleton

**Files:** Create `server.py`, `server_ratelimit.py`, `tools/__init__.py`, `services/__init__.py` (empty), `client` already done.
**Produces:**
- `server.build_app(settings) -> FastMCP` (registers `/health`, instructions string w/ safety+injection notice, middlewares: `OriginValidationMiddleware`, `ErrorEnvelopeMiddleware`, `RateLimitMiddleware`; registers tools via `tools.register_all(mcp, client)`; registers MCP resources via `services.resources.register_resources(mcp)`); `server.main()` runs `transport="http", host, port, path="/", stateless_http=True, json_response=True`.
- `tools/__init__.py`: `_MODULES = ("genes","annotations","statistics","capabilities")`; `register_all(mcp, client)` imports `kidney_genetics_mcp.tools.<m>` and calls `.register(mcp, client)`.
- `server_ratelimit` token-bucket: global + per-tool; `HEAVY_TOOLS = {"kgdb_get_interaction_partners","kgdb_get_database_stats"}`.

- [ ] Copy hnf1b `server.py` + `server_ratelimit.py`; adapt names, port, instructions (KGDB safety text). Make `register_resources` and `tools.capabilities`/etc. tolerant of not-yet-existing modules by listing all in `_MODULES` (Wave 2 fills them). To keep Wave 1 green, create **stub** `tools/{genes,annotations,statistics,capabilities}.py` each with `def register(mcp, client): pass` and `services/resources.py` with `def register_resources(mcp): pass` — Wave 2 replaces them. Test `test_smoke.py`: `build_app` succeeds, `/health` route present, `await mcp.list_tools()` callable (empty OK at this stage). Test `test_register_all.py`: all `_MODULES` import. Commit `feat(mcp): server, middlewares, rate limiter, registry skeleton`.

### Task 1b.1: Backend `GET /api/genes/resolve` (parallel, independent of 1a)

**Files:** Modify `backend/app/crud/gene.py`, `backend/app/api/endpoints/genes.py`; create `backend/tests/test_gene_resolve.py`.
**Produces:** `GET /api/genes/resolve?query=<str>` → JSON:API `{data:{id,hgnc_id,approved_symbol,matched_on,match_type}, meta:{...}}`; ambiguous → `{data:null, meta:{ambiguous:true, candidates:[{id,hgnc_id,approved_symbol}]}}`; not found → 404 `GeneNotFoundError`.

- [ ] **Step 1 (test first):** Write `test_gene_resolve.py` (use existing test fixtures/factories): cases — exact symbol `PKD1`; HGNC id `HGNC:9008`; ENSG id; NCBI digits; alias→canonical; ambiguous (two genes sharing an alias) → `ambiguous:true` + candidates; unknown → 404. Run, expect FAIL.
- [ ] **Step 2:** Add `gene_crud.resolve_query(db, query) -> Gene | list[Gene] | None`: branch by regex (HGNC:/ENSG/digits/UniProt/symbol/alias). Reuse `get_by_symbol`, `get_by_hgnc_id`. For ENSG/NCBI query `gene_annotations_summary`; for UniProt query `gene_annotations` JSONB (source `uniprot`); for alias query `genes.aliases` array containment + HGNC-annotation JSONB. Return list when >1 candidate (ambiguous).
- [ ] **Step 3:** Add `@router.get("/resolve")` in `genes.py` (BEFORE `/{gene_symbol}` route to avoid shadowing) calling `resolve_query`; shape JSON:API response; 404 on None; ambiguous payload on list. Use `run_in_threadpool` for the DB work.
- [ ] **Step 4:** Run `cd backend && uv run pytest tests/test_gene_resolve.py -v` → PASS. `make lint` + `uv run mypy app/api/endpoints/genes.py app/crud/gene.py --ignore-missing-imports`. Commit `feat(backend): add GET /api/genes/resolve gene resolver`.

---

## WAVE 2 — Tool families (4 parallel agents: A, B, C, D) — depend on Wave 1a

Each agent: read the hnf1b analog, write `services/<x>.py` (logic + `_FIELDS_BY_MODE` ladders + shaping) and `tools/<x>.py` (replace the Wave-1 stub: typed params, docstring, `readOnly` annotations, delegate via `run_tool`), plus tests. Use generated enums for `filterable_fields`/param `Literal`s. Every record gets `resolve_with` handoffs where it returns IDs.

### Task 2A: Genes family — `tools/genes.py` + `services/{resolve,genes,evidence}.py`
Tools: `kgdb_resolve_gene`, `kgdb_search_genes`, `kgdb_get_gene`, `kgdb_get_gene_evidence`.
- [ ] `resolve.py` → `GET /api/genes/resolve`; map ambiguous body → `ambiguous_query(choices)`. `genes.py` → list (`/api/genes/` with filter/sort/page params) + detail (`/api/genes/{symbol}`), field ladders for score/tier/group/source_scores. `evidence.py` → `/api/genes/{symbol}/evidence`, project `evidence_data` JSONB per mode, optional `sources` filter. Each search/resolve hit carries `resolve_with`.
- [ ] Tests (respx): `test_tool_resolve.py`, `test_tool_search_genes.py`, `test_tool_get_gene.py`, `test_tool_evidence.py` — envelope, mode projection, `readOnlyHint`, ambiguous mapping. Commit.

### Task 2B: Annotations family — `tools/annotations.py` + `services/{annotations,network}.py`
Tools: `kgdb_get_gene_annotations`, `kgdb_get_constraint_summary`, `kgdb_get_interaction_partners`.
- [ ] `annotations.py` → `/api/annotations/genes/{id}/annotations` (optional `source`), summary → `/annotations/summary` (pLI/oe_lof/ids). `network.py` → read `?source=string_ppi`, parse `interactions[]`, filter by `min_string_score`, `sample_with_signal` to `limit`, rank by `string_score`. Heavy-tool rate budget.
- [ ] Tests: `test_tool_annotations.py`, `test_tool_constraint.py`, `test_tool_interactions.py`. Commit.

### Task 2C: Statistics family — `tools/statistics.py` + `services/{statistics,sources,releases}.py`
Tools: `kgdb_get_database_stats`, `kgdb_list_sources`, `kgdb_get_release_citation`.
- [ ] `statistics.py` → `/api/statistics/summary`. `sources.py` → merge `/api/annotations/sources` + `/api/datasources/` into one provenance list (display_name, version, url, last_update, counts). `releases.py` → `/api/releases/?status=published`, build release citation via `citation.build_release_citation` + concept DOI.
- [ ] Tests: `test_tool_stats.py`, `test_tool_sources.py`, `test_tool_releases.py`. Commit.

### Task 2D: Capabilities + Resources — `tools/capabilities.py` + `services/{capabilities,resources}.py` + `resources/*.md`
- [ ] `capabilities.py` builds the server-local descriptor (canonical_workflows, tools list, `filterable_fields` from generated enums, payload_modes/budgets, limits, identifiers, citation_contract, error_codes, data_classes, exclusions [heavy-network + Enrichr "not yet available"], safety, resources) + `capabilities_version = "sha256:"+sha256(sorted-json)[:16]` + `descriptor_chars`. `tools/capabilities.py` exposes `kgdb_get_capabilities`.
- [ ] `resources.py` `register_resources(mcp)` registers `kidney-genetics://schema/overview` + `kidney-genetics://schema/tool-guide` from packaged `resources/*.md`. Write `schema_overview.md` (data model: 7 evidence + 10 annotation sources, scoring/tiers/groups, identifiers, releases/DOI) and `tool_guide.md` (canonical workflow: resolve→get_gene→evidence/annotations→citation; response_mode guidance; citation+safety contract).
- [ ] Tests: `test_tool_capabilities.py` (hash deterministic, descriptor_chars present, all v1 tools listed), `test_resources.py`. Commit.

---

## WAVE 3 — Cross-cutting tests, deployment, verify (after Wave 2)

### Task 3.1: Security + contract tests
- [ ] `test_tool_allowlist_security.py`: `await mcp.list_tools()` returns EXACTLY the 11 v1 tool names; no tool name contains `write|admin|auth|sql|staging|ingest|delete|update|create`. `test_contract_drift.py`: every `ALLOW` regex matches a path in `contract/openapi.snapshot.json`; every snapshot GET path under the exposed domains is explicitly allowed or denied. Run full `make check` (cov ≥80). Commit.

### Task 3.2: Docker + compose + Makefile + README
- [ ] Adapt hnf1b `mcp/Dockerfile` + `Dockerfile.prod` (python:3.12-slim, uv, non-root 10001, read-only, healthcheck `curl -f http://localhost:8789/health`). Add service `mcp` to `docker-compose.yml` (build `./mcp`, `depends_on: backend healthy`, `KGDB_MCP_API_BASE_URL=http://backend:8000`, `ports:["8789:8789"]`) and `docker-compose.prod.yml` (internal+npm networks, `ports:[]`, non-root, read-only). Root `Makefile`: `mcp` (run), `mcp-build`, `mcp-test`. Write `mcp/README.md` (run, env, tools, safety). Commit.

### Task 3.3: Integration verify
- [ ] With backend running: build & start the MCP container; `curl /health`; run `scripts/`-style smoke (initialize → tools/list shows 11 → call `kgdb_get_capabilities`, `kgdb_resolve_gene?query=PKD1`, `kgdb_get_gene`, `kgdb_get_gene_evidence`). Confirm envelopes + citation. Document results. Commit `test(mcp): integration smoke verified`.

---

## Self-Review

**Spec coverage:** §3 data access → Wave 0/1a/1b; §3 resolve endpoint → 1b.1; §4 all 11 tools → 2A–2D; §5 envelopes/modes/errors/capabilities-hash/resources/citation/safety/ratelimit → 1a.2, 1a.4, 2D; §6 structure → file map; §7 config → 1a.1; §8 tests → 1a/2/3.1; §9 deployment → 3.2; verify → 3.3. No gaps.

**Placeholder scan:** Concrete file paths, signatures, allowlist regexes, env vars, and reference files given. Per-tool idiomatic code delegated to the hnf1b template (named file-by-file) rather than transcribed — acceptable because the reference is an exact-stack 1:1 and each task names the source file + produced signatures.

**Type consistency:** `run_tool`, `McpToolError`, `ResponseMode`, `sample_with_signal`, `apply_budget`, `build_meta`, `build_citation`, `assert_allowed`, `ApiClient.get`, `register(mcp, client)`, `register_all`, `register_resources` names are used consistently across Wave 1 (producers) and Wave 2 (consumers). `_MODULES` static list avoids `__init__.py` conflicts.
