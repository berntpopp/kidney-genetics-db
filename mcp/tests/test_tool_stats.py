"""Tests for the kgdb_get_database_stats tool + statistics service."""

from __future__ import annotations

import httpx
import pytest
import respx
from fastmcp import FastMCP
from pydantic import ValidationError

from kidney_genetics_mcp.client.api_client import ApiClient
from kidney_genetics_mcp.services.dataclass import STATISTICS
from kidney_genetics_mcp.tools.statistics import register

BASE = "http://api.test"
SUMMARY = f"{BASE}/api/statistics/summary"

_PAIRWISE = [
    {
        "source1": f"S{i}",
        "source2": f"S{i + 1}",
        "overlap_count": 100 - i,
        "source1_total": 200,
        "source2_total": 180,
        "overlap_percentage": 50.0,
    }
    for i in range(15)
]

_SUMMARY_RESPONSE = {
    "data": {
        "overview": {
            "total_genes": 5080,
            "active_sources": 7,
            "total_intersections": 42,
            "genes_in_all_sources": 12,
        },
        "quality": {
            "avg_sources_per_gene": 2.3,
            "total_evidence_records": 18000,
            "high_confidence_genes": 350,
        },
        "coverage": {
            "single_source_genes": 3000,
            "multi_source_genes": 2080,
            "source_distribution_variety": 7,
        },
        "pairwise_overlaps": _PAIRWISE,
    },
    "meta": {"description": "Summary statistics for dashboard overview"},
}


def _make() -> tuple[FastMCP, ApiClient]:  # type: ignore[type-arg]
    mcp: FastMCP = FastMCP("test")  # type: ignore[type-arg]
    client = ApiClient(base_url=BASE)
    register(mcp, client)
    return mcp, client


async def test_registers_with_readonly_hints() -> None:
    mcp: FastMCP = FastMCP("test")  # type: ignore[type-arg]
    register(mcp, None)
    tools = await mcp.list_tools()
    tool = next(t for t in tools if t.name == "kgdb_get_database_stats")
    assert tool.annotations.readOnlyHint is True
    assert tool.annotations.idempotentHint is True
    assert tool.annotations.openWorldHint is False
    assert tool.annotations.title == "Get Kidney-Genetics Database Statistics"


@respx.mock
async def test_compact_envelope_and_projection() -> None:
    respx.get(SUMMARY).mock(return_value=httpx.Response(200, json=_SUMMARY_RESPONSE))
    mcp, client = _make()
    r = await mcp.call_tool("kgdb_get_database_stats", {})
    await client.aclose()

    sc = r.structured_content
    assert sc["data_class"] == STATISTICS
    assert sc["meta"]["response_mode"] == "compact"
    # compact = overview + quality, NO coverage / pairwise_overlaps
    assert sc["overview"]["total_genes"] == 5080
    assert sc["quality"]["high_confidence_genes"] == 350
    assert "coverage" not in sc
    assert "pairwise_overlaps" not in sc


@respx.mock
async def test_minimal_only_overview() -> None:
    respx.get(SUMMARY).mock(return_value=httpx.Response(200, json=_SUMMARY_RESPONSE))
    mcp, client = _make()
    r = await mcp.call_tool("kgdb_get_database_stats", {"response_mode": "minimal"})
    await client.aclose()

    sc = r.structured_content
    assert "overview" in sc
    assert "quality" not in sc
    assert "coverage" not in sc
    assert "pairwise_overlaps" not in sc


@respx.mock
async def test_full_includes_coverage_and_overlaps_sampled() -> None:
    respx.get(SUMMARY).mock(return_value=httpx.Response(200, json=_SUMMARY_RESPONSE))
    mcp, client = _make()
    r = await mcp.call_tool("kgdb_get_database_stats", {"response_mode": "full"})
    await client.aclose()

    sc = r.structured_content
    assert sc["coverage"]["single_source_genes"] == 3000
    # 15 overlaps > sample size 10 -> capped + meta signal
    assert len(sc["pairwise_overlaps"]) == 10
    assert sc["meta"]["pairwise_overlaps_truncated"] is True
    assert sc["meta"]["pairwise_overlaps_total"] == 15
    assert sc["meta"]["pairwise_overlaps_returned"] == 10


async def test_invalid_response_mode_rejected() -> None:
    # response_mode is a Literal, so an out-of-enum value is rejected by
    # FastMCP's argument validation before the handler runs. The server's
    # ErrorEnvelopeMiddleware (not installed on this bare test harness) maps
    # this ValidationError into the invalid_input envelope at runtime.
    mcp, client = _make()
    with pytest.raises(ValidationError):
        await mcp.call_tool("kgdb_get_database_stats", {"response_mode": "huge"})
    await client.aclose()


@respx.mock
async def test_upstream_error_mapped() -> None:
    respx.get(SUMMARY).mock(return_value=httpx.Response(500))
    mcp, client = _make()
    r = await mcp.call_tool("kgdb_get_database_stats", {})
    await client.aclose()

    sc = r.structured_content
    assert sc.get("is_error") is True
    assert sc["error"]["code"] == "temporarily_unavailable"
