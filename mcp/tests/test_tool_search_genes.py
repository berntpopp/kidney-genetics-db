"""Tests for the kgdb_search_genes tool + search service."""

from __future__ import annotations

from typing import Any

import httpx
import pytest
import respx
from fastmcp import FastMCP

from kidney_genetics_mcp.client.api_client import ApiClient
from kidney_genetics_mcp.services import dataclass
from kidney_genetics_mcp.services.errors import McpToolError
from kidney_genetics_mcp.services.genes import search_genes
from kidney_genetics_mcp.tools.genes import register

_BASE = "http://test-backend"


def _gene_item(gid: str, symbol: str, score: float) -> dict[str, Any]:
    return {
        "type": "genes",
        "id": gid,
        "attributes": {
            "hgnc_id": f"HGNC:{gid}",
            "approved_symbol": symbol,
            "aliases": [],
            "evidence_count": 5,
            "evidence_score": score,
            "evidence_tier": "comprehensive_support",
            "evidence_group": "well_supported",
            "sources": ["PanelApp", "ClinGen"],
        },
    }


_LIST_BODY = {
    "data": [
        _gene_item("1", "PKD1", 98.0),
        _gene_item("2", "PKD2", 95.0),
    ],
    "meta": {"total": 2, "page": 1, "per_page": 20, "page_count": 1},
    "links": {},
}


async def _get_tool(mcp: FastMCP, name: str) -> Any:
    tool = await mcp.get_tool(name)
    assert tool is not None
    return tool


async def test_search_tool_registered_readonly() -> None:
    mcp = FastMCP("test")
    register(mcp, None)
    tool = await _get_tool(mcp, "kgdb_search_genes")
    assert tool.annotations.readOnlyHint is True
    assert tool.annotations.idempotentHint is True
    assert tool.annotations.openWorldHint is False
    assert tool.annotations.title


@respx.mock
async def test_search_maps_bracket_params() -> None:
    route = respx.get(f"{_BASE}/api/genes/").mock(
        return_value=httpx.Response(200, json=_LIST_BODY)
    )
    client = ApiClient(base_url=_BASE)
    try:
        await search_genes(
            client,
            query="cyst",
            tier="comprehensive_support",
            group="well_supported",
            min_score=10,
            max_score=99,
            source="PanelApp",
            sort="-evidence_score",
            page=2,
            page_size=5,
        )
    finally:
        await client.aclose()
    sent = route.calls.last.request
    qp = dict(httpx.QueryParams(sent.url.query))
    assert qp["filter[search]"] == "cyst"
    assert qp["filter[tier]"] == "comprehensive_support"
    assert qp["filter[group]"] == "well_supported"
    assert qp["filter[min_score]"] == "10"
    assert qp["filter[max_score]"] == "99"
    assert qp["filter[source]"] == "PanelApp"
    assert qp["sort"] == "-evidence_score"
    assert qp["page[number]"] == "2"
    assert qp["page[size]"] == "5"


@respx.mock
async def test_search_hits_have_resolve_with_and_pagination() -> None:
    respx.get(f"{_BASE}/api/genes/").mock(
        return_value=httpx.Response(200, json=_LIST_BODY)
    )
    client = ApiClient(base_url=_BASE)
    try:
        result = await search_genes(client, query="x")
    finally:
        await client.aclose()
    assert len(result["genes"]) == 2
    first = result["genes"][0]
    assert first["approved_symbol"] == "PKD1"
    assert first["resolve_with"] == {
        "tool": "kgdb_get_gene",
        "argument": "gene_symbol",
        "value": "PKD1",
    }
    assert result["pagination"] == {
        "total": 2,
        "page": 1,
        "page_size": 20,
        "page_count": 1,
        "has_more": False,
    }


@respx.mock
async def test_search_response_mode_projection() -> None:
    respx.get(f"{_BASE}/api/genes/").mock(
        return_value=httpx.Response(200, json=_LIST_BODY)
    )
    client = ApiClient(base_url=_BASE)
    try:
        minimal = await search_genes(client, query="x", response_mode="minimal")
        full = await search_genes(client, query="x", response_mode="full")
    finally:
        await client.aclose()
    min_hit = minimal["genes"][0]
    # minimal drops evidence_group + sources; resolve_with always present
    assert "evidence_group" not in min_hit
    assert "sources" not in min_hit
    assert "evidence_tier" in min_hit
    assert "resolve_with" in min_hit
    # full keeps sources + group
    full_hit = full["genes"][0]
    assert "sources" in full_hit
    assert "evidence_group" in full_hit


async def test_search_invalid_tier_raises() -> None:
    with pytest.raises(McpToolError) as exc:
        await search_genes(None, tier="platinum")  # type: ignore[arg-type]
    assert exc.value.code == "invalid_input"
    assert exc.value.details["field"] == "tier"
    assert "comprehensive_support" in exc.value.details["allowed"]


async def test_search_invalid_sort_raises() -> None:
    with pytest.raises(McpToolError) as exc:
        await search_genes(None, sort="-nonsense")  # type: ignore[arg-type]
    assert exc.value.code == "invalid_input"
    assert exc.value.details["field"] == "sort"


@respx.mock
async def test_search_tool_envelope() -> None:
    respx.get(f"{_BASE}/api/genes/").mock(
        return_value=httpx.Response(200, json=_LIST_BODY)
    )
    client = ApiClient(base_url=_BASE)
    mcp = FastMCP("test")
    register(mcp, client)
    try:
        tool = await _get_tool(mcp, "kgdb_search_genes")
        out = await tool.fn(query="cyst", response_mode="compact")
    finally:
        await client.aclose()
    assert out["data_class"] == dataclass.GENE
    assert out["meta"]["response_mode"] == "compact"
    assert "effective_chars" in out["meta"]
    assert len(out["genes"]) == 2
