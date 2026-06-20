"""Tests for the kgdb_resolve_gene tool + resolve service."""

from __future__ import annotations

from typing import Any

import httpx
import pytest
import respx
from fastmcp import FastMCP

from kidney_genetics_mcp.client.api_client import ApiClient
from kidney_genetics_mcp.services import dataclass
from kidney_genetics_mcp.services.errors import McpToolError
from kidney_genetics_mcp.services.resolve import resolve_gene
from kidney_genetics_mcp.tools.genes import register

_BASE = "http://test-backend"

_SINGLE_BODY = {
    "data": {
        "type": "gene",
        "id": "42",
        "attributes": {
            "hgnc_id": "HGNC:9008",
            "approved_symbol": "PKD1",
            "matched_on": "PKD1",
            "match_type": "symbol",
        },
    },
    "meta": {"ambiguous": False, "query": "PKD1"},
}

_AMBIGUOUS_BODY = {
    "data": None,
    "meta": {
        "ambiguous": True,
        "query": "X",
        "candidates": [
            {"id": "1", "hgnc_id": "HGNC:1", "approved_symbol": "ABC1"},
            {"id": "2", "hgnc_id": "HGNC:2", "approved_symbol": "ABC2"},
        ],
    },
}


async def _get_tool(mcp: FastMCP, name: str) -> Any:
    tool = await mcp.get_tool(name)
    assert tool is not None, f"{name} not registered"
    return tool


def _build() -> FastMCP:
    mcp = FastMCP("test")
    register(mcp, None)
    return mcp


async def test_resolve_tool_registered_readonly() -> None:
    mcp = _build()
    tools = await mcp.list_tools()
    by_name = {t.name: t for t in tools}
    assert "kgdb_resolve_gene" in by_name
    tool = by_name["kgdb_resolve_gene"]
    assert tool.annotations is not None
    assert tool.annotations.readOnlyHint is True
    assert tool.annotations.idempotentHint is True
    assert tool.annotations.openWorldHint is False
    assert tool.annotations.title


@respx.mock
async def test_resolve_single_envelope_and_handoff() -> None:
    respx.get(f"{_BASE}/api/genes/resolve").mock(
        return_value=httpx.Response(200, json=_SINGLE_BODY)
    )
    client = ApiClient(base_url=_BASE)
    try:
        result = await resolve_gene(client, "PKD1")
    finally:
        await client.aclose()
    assert result["gene"] == {
        "id": "42",
        "hgnc_id": "HGNC:9008",
        "approved_symbol": "PKD1",
        "match_type": "symbol",
    }
    assert result["resolve_with"] == {
        "tool": "kgdb_get_gene",
        "argument": "gene_symbol",
        "value": "PKD1",
    }


@respx.mock
async def test_resolve_tool_attaches_envelope() -> None:
    respx.get(f"{_BASE}/api/genes/resolve").mock(
        return_value=httpx.Response(200, json=_SINGLE_BODY)
    )
    client = ApiClient(base_url=_BASE)
    mcp = FastMCP("test")
    register(mcp, client)
    try:
        tool = await _get_tool(mcp, "kgdb_resolve_gene")
        out = await tool.fn(query="PKD1")
    finally:
        await client.aclose()
    assert out["data_class"] == dataclass.GENE_IDENTITY
    assert out["meta"]["response_mode"] == "compact"
    assert out["gene"]["approved_symbol"] == "PKD1"
    assert "is_error" not in out


@respx.mock
async def test_resolve_ambiguous_raises_ambiguous_query() -> None:
    respx.get(f"{_BASE}/api/genes/resolve").mock(
        return_value=httpx.Response(200, json=_AMBIGUOUS_BODY)
    )
    client = ApiClient(base_url=_BASE)
    try:
        with pytest.raises(McpToolError) as exc:
            await resolve_gene(client, "X")
    finally:
        await client.aclose()
    assert exc.value.code == "ambiguous_query"
    assert exc.value.details["choices"] == _AMBIGUOUS_BODY["meta"]["candidates"]


@respx.mock
async def test_resolve_tool_ambiguous_envelope() -> None:
    respx.get(f"{_BASE}/api/genes/resolve").mock(
        return_value=httpx.Response(200, json=_AMBIGUOUS_BODY)
    )
    client = ApiClient(base_url=_BASE)
    mcp = FastMCP("test")
    register(mcp, client)
    try:
        tool = await _get_tool(mcp, "kgdb_resolve_gene")
        out = await tool.fn(query="X")
    finally:
        await client.aclose()
    assert out["is_error"] is True
    assert out["error"]["code"] == "ambiguous_query"
    assert len(out["error"]["choices"]) == 2


async def test_resolve_empty_query_invalid_input() -> None:
    with pytest.raises(McpToolError) as exc:
        await resolve_gene(None, "   ")  # type: ignore[arg-type]
    assert exc.value.code == "invalid_input"
    assert exc.value.details["field"] == "query"


@respx.mock
async def test_resolve_not_found_propagates() -> None:
    respx.get(f"{_BASE}/api/genes/resolve").mock(return_value=httpx.Response(404))
    client = ApiClient(base_url=_BASE)
    try:
        with pytest.raises(McpToolError) as exc:
            await resolve_gene(client, "ZZZ")
    finally:
        await client.aclose()
    assert exc.value.code == "not_found"
