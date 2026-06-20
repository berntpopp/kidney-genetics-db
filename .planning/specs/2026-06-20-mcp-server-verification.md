# MCP Server — Verification Record (2026-06-20)

Branch `feat/mcp-server`. Implemented in parallel waves (scaffold/contract → plumbing + backend resolve → 4 tool families → security/contract tests + deployment → live smoke).

## Gates (full `mcp/` package)
- `ruff check .` — clean
- `mypy src/` (strict) — clean (30 source files)
- `pytest --cov` — **202 passed, 90.75% coverage** (gate ≥80)
- `docker compose config` (dev + prod) — valid
- Backend: `pytest tests/test_gene_resolve.py` — 20 passed against live PostgreSQL

## Live integration smoke (MCP app → live KGDB backend on :8000)
Transport boots (FastMCP HTTP stateless on :8789); `/health` → `200 {"status":"ok"}`; `tools/list` → exactly 11 `kgdb_` tools + 2 resources.

| Tool | Result |
|---|---|
| kgdb_get_capabilities | ✅ descriptor + `capabilities_version=sha256:…` + descriptor_chars |
| kgdb_resolve_gene("PKD1") | ✅ → id 6362, HGNC:9008, match_type=symbol, resolve_with handoff |
| kgdb_search_genes("PKD") | ✅ paginated, per-hit resolve_with |
| kgdb_get_gene("PKD1") | ✅ score 95.2, comprehensive_support, well_supported, 7 sources |
| kgdb_get_gene_evidence("PKD1") | ✅ per-source scored evidence |
| kgdb_get_gene_annotations(6362) | ✅ string_ppi/etc., mode-projected |
| kgdb_get_constraint_summary(6362) | ✅ oe_lof + ENSG/NCBI/MANE ids |
| kgdb_get_interaction_partners(6362) | ✅ PKD1→PKD2 string_score 999, resolve_with |
| kgdb_list_sources | ✅ merged provenance + versions |
| kgdb_get_release_citation | ✅ graceful `not_found` (no published release exists in dev DB — correct) |
| kgdb_get_gene("NOTAGENEXYZ") | ✅ graceful `not_found` envelope |
| kgdb_get_database_stats | ⚠️ surfaces upstream 422 — see below |

## Known environment gaps (NOT MCP defects)
1. **`kgdb_get_database_stats`**: `/api/statistics/summary` returns 422 in this dev DB because the `source_overlap_statistics` relation is missing (`to_regclass` → NULL). The MCP tool correctly surfaces the upstream error as an envelope; happy-path projection is covered by unit tests (`test_tool_stats.py`). Fix belongs to the DB (recreate views).
2. **`make db-refresh-views` is broken locally**: passes a `SecretStr` to `create_engine` (`Makefile:688`) — pre-existing backend tooling bug, unrelated to the MCP. Would otherwise recreate the missing view.

## Follow-ups (optional, out of v1 scope)
- Add explicit deny rules for exposed-domain *detail* routes (`/api/releases/{version}*`, `/api/datasources/{source_name}`) so `is_denied` returns True rather than relying on default-deny (currently secure either way).
- Consider mapping backend-internal 422s (server failures wrapped as `validation_error`) to `temporarily_unavailable` rather than `invalid_input`.
- Backend rate-limit exemption for internal MCP traffic if the response cache proves insufficient.
