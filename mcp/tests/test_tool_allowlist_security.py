"""Security test: the registered tool surface is exactly the approved v1 set.

This is the "tool-allowlist" security boundary (SysNDD idea): the MCP must expose
*only* the 11 read-only ``kgdb_``-prefixed tools from the spec §4 catalog, every
one flagged read-only / closed-world / idempotent, and no tool name may leak a
privileged verb (write/admin/auth/sql/staging/ingest/delete/update/create/...).
A new tool added without updating this set — or any tool whose name hints at a
side-effecting surface — fails here.
"""

from __future__ import annotations

import pytest
from fastmcp import FastMCP

from kidney_genetics_mcp.config import Settings, get_settings
from kidney_genetics_mcp.server import build_app

# The exact, frozen v1 tool catalog (spec §4). Set equality is asserted, so this
# fails on *any* addition, removal, or rename.
EXPECTED_TOOLS: frozenset[str] = frozenset(
    {
        "kgdb_get_capabilities",
        "kgdb_resolve_gene",
        "kgdb_search_genes",
        "kgdb_get_gene",
        "kgdb_get_gene_evidence",
        "kgdb_get_gene_annotations",
        "kgdb_get_constraint_summary",
        "kgdb_get_interaction_partners",
        "kgdb_get_database_stats",
        "kgdb_list_sources",
        "kgdb_get_release_citation",
    }
)

# Substrings that must never appear in a tool name — they would advertise a
# write/admin/auth/SQL/staging/ingestion or other side-effecting surface.
FORBIDDEN_NAME_TOKENS: tuple[str, ...] = (
    "write",
    "admin",
    "auth",
    "sql",
    "staging",
    "ingest",
    "delete",
    "update",
    "create",
    "patch",
    "drop",
    "exec",
)


@pytest.fixture
def settings(monkeypatch: pytest.MonkeyPatch) -> Settings:
    """Build settings from a dummy backend URL (no real network access)."""
    monkeypatch.setenv("KGDB_MCP_API_BASE_URL", "http://test-backend:8000")
    get_settings.cache_clear()
    return get_settings()


@pytest.fixture
def app(settings: Settings) -> FastMCP:
    """A fully-built FastMCP app with all tools + resources registered."""
    return build_app(settings)


async def test_exposes_exactly_the_eleven_approved_tools(app: FastMCP) -> None:
    """``list_tools`` must return precisely the 11 v1 tool names — no more."""
    tools = await app.list_tools()
    names = {t.name for t in tools}
    assert names == EXPECTED_TOOLS, (
        "registered tool set drifted from the approved v1 catalog: "
        f"unexpected={sorted(names - EXPECTED_TOOLS)} "
        f"missing={sorted(EXPECTED_TOOLS - names)}"
    )


async def test_no_tool_name_leaks_a_privileged_verb(app: FastMCP) -> None:
    """No tool name may contain a write/admin/auth/sql/... token (case-insensitive)."""
    names = [t.name for t in await app.list_tools()]
    for name in names:
        lowered = name.lower()
        offending = [tok for tok in FORBIDDEN_NAME_TOKENS if tok in lowered]
        assert not offending, (
            f"tool name {name!r} contains forbidden token(s) {offending} — "
            "tool names must not advertise a side-effecting surface"
        )


async def test_every_tool_is_read_only_closed_world_idempotent(app: FastMCP) -> None:
    """Each tool's annotations must declare it read-only, closed-world, idempotent.

    Accessed via ``get_tool(name).annotations`` (the Wave-2 idiom): a missing or
    write-leaning annotation set would silently weaken the read-only contract.
    """
    for name in EXPECTED_TOOLS:
        tool = await app.get_tool(name)
        annotations = tool.annotations
        assert annotations is not None, f"{name} has no annotations block"
        assert annotations.readOnlyHint is True, f"{name} readOnlyHint must be True"
        assert annotations.openWorldHint is False, f"{name} openWorldHint must be False"
        assert (
            annotations.idempotentHint is True
        ), f"{name} idempotentHint must be True"
