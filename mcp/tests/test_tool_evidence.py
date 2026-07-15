"""Tests for the kgdb_get_gene_evidence tool + evidence service."""

from __future__ import annotations

from typing import Any

import httpx
import pytest
import respx
from fastmcp import FastMCP

from kidney_genetics_mcp.client.api_client import ApiClient
from kidney_genetics_mcp.services import dataclass
from kidney_genetics_mcp.services.errors import McpToolError
from kidney_genetics_mcp.services.evidence import get_gene_evidence
from kidney_genetics_mcp.tools.genes import register

_BASE = "http://test-backend"


def _ev_item(eid: str, source: str, score: float) -> dict[str, Any]:
    return {
        "type": "evidence",
        "id": eid,
        "attributes": {
            "source_name": source,
            "source_detail": f"{source} panel v1",
            "evidence_data": {"panel_id": eid, "confidence": "Green", "blob": "x" * 50},
            "evidence_date": "2026-01-01",
            "created_at": "2026-01-01T00:00:00",
            "normalized_score": score,
        },
        "relationships": {"gene": {"data": {"type": "genes", "id": "42"}}},
    }


_EVIDENCE_BODY = {
    "data": [
        _ev_item("10", "PanelApp", 1.0),
        _ev_item("11", "ClinGen", 0.9),
        _ev_item("12", "GenCC", 0.8),
    ],
    "meta": {"gene_symbol": "PKD1", "gene_id": 42, "evidence_count": 3},
}


async def _get_tool(mcp: FastMCP, name: str) -> Any:
    tool = await mcp.get_tool(name)
    assert tool is not None
    return tool


async def test_evidence_tool_registered_readonly() -> None:
    mcp = FastMCP("test")
    register(mcp, None)
    tool = await _get_tool(mcp, "kgdb_get_gene_evidence")
    assert tool.annotations.readOnlyHint is True
    assert tool.annotations.idempotentHint is True
    assert tool.annotations.openWorldHint is False
    assert tool.annotations.title


@respx.mock
async def test_evidence_compact_drops_evidence_data() -> None:
    respx.get(f"{_BASE}/api/genes/PKD1/evidence").mock(
        return_value=httpx.Response(200, json=_EVIDENCE_BODY)
    )
    client = ApiClient(base_url=_BASE)
    try:
        result = await get_gene_evidence(client, "PKD1", response_mode="compact")
    finally:
        await client.aclose()
    assert result["gene_symbol"] == "PKD1"
    assert result["evidence_count"] == 3
    rec = result["evidence"][0]
    assert rec["source_name"] == "PanelApp"
    assert rec["normalized_score"] == 1.0
    assert rec["source_detail"] == "PanelApp panel v1"
    assert rec["evidence_date"] == "2026-01-01"
    # bulky JSONB dropped in compact
    assert "evidence_data" not in rec


@respx.mock
async def test_evidence_standard_keeps_evidence_data() -> None:
    respx.get(f"{_BASE}/api/genes/PKD1/evidence").mock(
        return_value=httpx.Response(200, json=_EVIDENCE_BODY)
    )
    client = ApiClient(base_url=_BASE)
    try:
        result = await get_gene_evidence(client, "PKD1", response_mode="standard")
    finally:
        await client.aclose()
    rec = result["evidence"][0]
    assert "evidence_data" in rec
    assert rec["evidence_data"]["confidence"] == "Green"


@respx.mock
async def test_evidence_sources_filter() -> None:
    respx.get(f"{_BASE}/api/genes/PKD1/evidence").mock(
        return_value=httpx.Response(200, json=_EVIDENCE_BODY)
    )
    client = ApiClient(base_url=_BASE)
    try:
        result = await get_gene_evidence(
            client, "PKD1", sources=["ClinGen"], response_mode="compact"
        )
    finally:
        await client.aclose()
    assert result["evidence_count"] == 1
    assert {r["source_name"] for r in result["evidence"]} == {"ClinGen"}


@respx.mock
async def test_evidence_not_found_propagates() -> None:
    respx.get(f"{_BASE}/api/genes/NOPE/evidence").mock(return_value=httpx.Response(404))
    client = ApiClient(base_url=_BASE)
    try:
        with pytest.raises(McpToolError) as exc:
            await get_gene_evidence(client, "NOPE")
    finally:
        await client.aclose()
    assert exc.value.code == "not_found"


@respx.mock
async def test_evidence_tool_envelope() -> None:
    respx.get(f"{_BASE}/api/genes/PKD1/evidence").mock(
        return_value=httpx.Response(200, json=_EVIDENCE_BODY)
    )
    client = ApiClient(base_url=_BASE)
    mcp = FastMCP("test")
    register(mcp, client)
    try:
        tool = await _get_tool(mcp, "kgdb_get_gene_evidence")
        out = await tool.fn(gene_symbol="PKD1", response_mode="compact")
    finally:
        await client.aclose()
    assert out["data_class"] == dataclass.EVIDENCE
    assert out["meta"]["response_mode"] == "compact"
    assert out["evidence_count"] == 3
