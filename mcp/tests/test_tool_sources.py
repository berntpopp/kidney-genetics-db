"""Tests for the kgdb_list_sources tool + sources merge service."""

from __future__ import annotations

import httpx
import respx
from fastmcp import FastMCP

from kidney_genetics_mcp.client.api_client import ApiClient
from kidney_genetics_mcp.services.dataclass import SOURCE
from kidney_genetics_mcp.tools.statistics import register

BASE = "http://api.test"
ANN_SOURCES = f"{BASE}/api/annotations/sources"
DATASOURCES = f"{BASE}/api/datasources/"

_ANN_SOURCES_RESPONSE = [
    {
        "source_name": "HGNC",
        "display_name": "HGNC",
        "version": "2024-01",
        "description": "Gene nomenclature",
        "url": "https://www.genenames.org",
        "base_url": "https://rest.genenames.org",
        "is_active": True,
        "priority": 100,
        "update_frequency": "monthly",
        "last_update": "2024-01-15T00:00:00",
        "next_update": None,
        "created_at": "2023-01-01T00:00:00",
        "updated_at": "2024-01-15T00:00:00",
    },
    {
        "source_name": "gnomAD",
        "display_name": "gnomAD",
        "version": "v4.0",
        "description": "Constraint",
        "url": "https://gnomad.broadinstitute.org",
        "base_url": None,
        "is_active": True,
        "priority": 90,
        "update_frequency": "yearly",
        "last_update": "2023-11-01T00:00:00",
        "next_update": None,
        "created_at": "2023-01-01T00:00:00",
        "updated_at": "2023-11-01T00:00:00",
    },
]

_DATASOURCES_RESPONSE = {
    "data": {
        "sources": [
            {
                "name": "HGNC",
                "display_name": "HGNC",
                "description": "Gene nomenclature",
                "status": "active",
                "stats": {
                    "gene_count": 5000,
                    "evidence_count": 5000,
                    "last_updated": "2024-01-15T00:00:00",
                    "metadata": {},
                },
                "url": "https://www.genenames.org",
                "documentation_url": "https://www.genenames.org/help",
            },
            {
                "name": "PanelApp",
                "display_name": "PanelApp",
                "description": "Clinical panels",
                "status": "active",
                "stats": {
                    "gene_count": 800,
                    "evidence_count": 1200,
                    "last_updated": "2024-02-01T00:00:00",
                    "metadata": {},
                },
                "url": "https://panelapp.genomicsengland.co.uk",
                "documentation_url": None,
            },
        ],
        "total_active": 2,
        "total_sources": 2,
    },
    "meta": {},
}


def _make() -> tuple[FastMCP, ApiClient]:  # type: ignore[type-arg]
    mcp: FastMCP = FastMCP("test")  # type: ignore[type-arg]
    client = ApiClient(base_url=BASE)
    register(mcp, client)
    return mcp, client


def _mock_both() -> None:
    respx.get(ANN_SOURCES).mock(
        return_value=httpx.Response(200, json=_ANN_SOURCES_RESPONSE)
    )
    respx.get(DATASOURCES).mock(
        return_value=httpx.Response(200, json=_DATASOURCES_RESPONSE)
    )


async def test_registers_with_readonly_hints() -> None:
    mcp: FastMCP = FastMCP("test")  # type: ignore[type-arg]
    register(mcp, None)
    tools = await mcp.list_tools()
    tool = next(t for t in tools if t.name == "kgdb_list_sources")
    assert tool.annotations.readOnlyHint is True
    assert tool.annotations.idempotentHint is True
    assert tool.annotations.openWorldHint is False


@respx.mock
async def test_merge_and_envelope() -> None:
    _mock_both()
    mcp, client = _make()
    r = await mcp.call_tool("kgdb_list_sources", {"response_mode": "standard"})
    await client.aclose()

    sc = r.structured_content
    assert sc["data_class"] == SOURCE
    assert sc["meta"]["response_mode"] == "standard"
    # 2 annotation sources + 1 datasource-only (PanelApp) = 3 merged records
    assert sc["total"] == 3
    by_name = {s["source_name"]: s for s in sc["sources"]}
    # HGNC matched both registries -> version from annotations + counts from ds
    hgnc = by_name["HGNC"]
    assert hgnc["version"] == "2024-01"
    assert hgnc["gene_count"] == 5000
    assert hgnc["evidence_count"] == 5000
    # gnomAD only in annotation registry -> no counts, version preserved
    assert by_name["gnomAD"]["version"] == "v4.0"
    # PanelApp only in datasource registry -> appended with counts, no version
    panelapp = by_name["PanelApp"]
    assert panelapp["version"] is None
    assert panelapp["gene_count"] == 800


@respx.mock
async def test_minimal_projection_drops_url_and_counts() -> None:
    _mock_both()
    mcp, client = _make()
    r = await mcp.call_tool("kgdb_list_sources", {"response_mode": "minimal"})
    await client.aclose()

    sc = r.structured_content
    hgnc = next(s for s in sc["sources"] if s["source_name"] == "HGNC")
    assert set(hgnc.keys()) == {"source_name", "display_name", "version"}


@respx.mock
async def test_default_mode_is_compact() -> None:
    _mock_both()
    mcp, client = _make()
    r = await mcp.call_tool("kgdb_list_sources", {})
    await client.aclose()

    sc = r.structured_content
    assert sc["meta"]["response_mode"] == "compact"
    hgnc = next(s for s in sc["sources"] if s["source_name"] == "HGNC")
    # compact = name, display_name, version, url, last_update (no counts)
    assert "url" in hgnc
    assert "last_update" in hgnc
    assert "gene_count" not in hgnc


@respx.mock
async def test_upstream_error_mapped() -> None:
    respx.get(ANN_SOURCES).mock(return_value=httpx.Response(503))
    respx.get(DATASOURCES).mock(
        return_value=httpx.Response(200, json=_DATASOURCES_RESPONSE)
    )
    mcp, client = _make()
    r = await mcp.call_tool("kgdb_list_sources", {})
    await client.aclose()

    sc = r.structured_content
    assert sc.get("is_error") is True
    assert sc["error"]["code"] == "temporarily_unavailable"
