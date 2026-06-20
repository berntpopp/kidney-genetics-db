"""Tests for the kgdb_get_gene tool + detail service."""

from __future__ import annotations

from typing import Any

import httpx
import pytest
import respx
from fastmcp import FastMCP

from kidney_genetics_mcp.client.api_client import ApiClient
from kidney_genetics_mcp.services import dataclass
from kidney_genetics_mcp.services.errors import McpToolError
from kidney_genetics_mcp.services.genes import get_gene
from kidney_genetics_mcp.tools.genes import register

_BASE = "http://test-backend"

_DETAIL_BODY = {
    "data": {
        "type": "genes",
        "id": "42",
        "attributes": {
            "hgnc_id": "HGNC:9008",
            "approved_symbol": "PKD1",
            "aliases": [],
            "evidence_count": 6,
            "evidence_score": 98.5,
            "evidence_tier": "comprehensive_support",
            "evidence_group": "well_supported",
            "sources": ["PanelApp", "ClinGen", "GenCC"],
            "score_breakdown": {"PanelApp": 1.0, "ClinGen": 0.9},
            "source_scores": {"PanelApp": {"raw": 3, "norm": 1.0}},
        },
    }
}


async def _get_tool(mcp: FastMCP, name: str) -> Any:
    tool = await mcp.get_tool(name)
    assert tool is not None
    return tool


async def test_get_gene_tool_registered_readonly() -> None:
    mcp = FastMCP("test")
    register(mcp, None)
    tool = await _get_tool(mcp, "kgdb_get_gene")
    assert tool.annotations.readOnlyHint is True
    assert tool.annotations.idempotentHint is True
    assert tool.annotations.openWorldHint is False
    assert tool.annotations.title


@respx.mock
async def test_get_gene_minimal_drops_breakdown_and_scores() -> None:
    respx.get(f"{_BASE}/api/genes/PKD1").mock(
        return_value=httpx.Response(200, json=_DETAIL_BODY)
    )
    client = ApiClient(base_url=_BASE)
    try:
        result = await get_gene(client, "PKD1", response_mode="minimal")
    finally:
        await client.aclose()
    # core score fields present
    assert result["evidence_score"] == 98.5
    assert result["evidence_tier"] == "comprehensive_support"
    assert result["evidence_count"] == 6
    # identity always kept
    assert result["approved_symbol"] == "PKD1"
    assert result["hgnc_id"] == "HGNC:9008"
    assert result["uri"] == "kidney-genetics://gene/PKD1"
    # bulky fields dropped in minimal
    assert "score_breakdown" not in result
    assert "source_scores" not in result
    assert "sources" not in result


@respx.mock
async def test_get_gene_full_keeps_all() -> None:
    respx.get(f"{_BASE}/api/genes/PKD1").mock(
        return_value=httpx.Response(200, json=_DETAIL_BODY)
    )
    client = ApiClient(base_url=_BASE)
    try:
        result = await get_gene(client, "PKD1", response_mode="full")
    finally:
        await client.aclose()
    assert result["sources"] == ["PanelApp", "ClinGen", "GenCC"]
    assert result["score_breakdown"] == {"PanelApp": 1.0, "ClinGen": 0.9}
    assert result["source_scores"] == {"PanelApp": {"raw": 3, "norm": 1.0}}


@respx.mock
async def test_get_gene_explicit_fields() -> None:
    respx.get(f"{_BASE}/api/genes/PKD1").mock(
        return_value=httpx.Response(200, json=_DETAIL_BODY)
    )
    client = ApiClient(base_url=_BASE)
    try:
        result = await get_gene(
            client, "PKD1", response_mode="full", fields=["evidence_score"]
        )
    finally:
        await client.aclose()
    assert result["evidence_score"] == 98.5
    # identity always retained even with explicit fields
    assert "approved_symbol" in result
    assert "hgnc_id" in result
    # other fields filtered out
    assert "sources" not in result
    assert "score_breakdown" not in result


@respx.mock
async def test_get_gene_not_found_propagates() -> None:
    respx.get(f"{_BASE}/api/genes/NOPE").mock(return_value=httpx.Response(404))
    client = ApiClient(base_url=_BASE)
    try:
        with pytest.raises(McpToolError) as exc:
            await get_gene(client, "NOPE")
    finally:
        await client.aclose()
    assert exc.value.code == "not_found"


@respx.mock
async def test_get_gene_tool_envelope() -> None:
    respx.get(f"{_BASE}/api/genes/PKD1").mock(
        return_value=httpx.Response(200, json=_DETAIL_BODY)
    )
    client = ApiClient(base_url=_BASE)
    mcp = FastMCP("test")
    register(mcp, client)
    try:
        tool = await _get_tool(mcp, "kgdb_get_gene")
        out = await tool.fn(gene_symbol="PKD1", response_mode="compact")
    finally:
        await client.aclose()
    assert out["data_class"] == dataclass.GENE
    assert out["meta"]["response_mode"] == "compact"
    assert out["approved_symbol"] == "PKD1"


@respx.mock
async def test_get_gene_tool_not_found_envelope() -> None:
    respx.get(f"{_BASE}/api/genes/NOPE").mock(return_value=httpx.Response(404))
    client = ApiClient(base_url=_BASE)
    mcp = FastMCP("test")
    register(mcp, client)
    try:
        tool = await _get_tool(mcp, "kgdb_get_gene")
        out = await tool.fn(gene_symbol="NOPE")
    finally:
        await client.aclose()
    assert out["is_error"] is True
    assert out["error"]["code"] == "not_found"
