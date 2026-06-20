"""Tests for the kgdb_get_interaction_partners tool (registration + behavior)."""

from __future__ import annotations

import httpx
import respx
from fastmcp import FastMCP

from kidney_genetics_mcp.client.api_client import ApiClient
from kidney_genetics_mcp.services.dataclass import INTERACTION
from kidney_genetics_mcp.tools.annotations import register

BASE = "http://test-backend"
GENE_ID = 11
ANN_URL = f"{BASE}/api/annotations/genes/{GENE_ID}/annotations"

GENE_BLOCK = {"id": GENE_ID, "symbol": "PKD1", "hgnc_id": "HGNC:9008"}


def _partner(symbol: str, score: int, evidence: float = 5.0) -> dict:
    return {
        "partner_symbol": symbol,
        "string_score": score,
        "partner_evidence": evidence,
        "weighted_score": round((score / 1000) * evidence, 2),
    }


def _string_payload(interactions: list[dict], **summary_extra: object) -> dict:
    data = {
        "ppi_score": 12.3,
        "ppi_degree": len(interactions),
        "ppi_percentile": 0.87,
        "interactions": interactions,
        "summary": {"total_interactions": len(interactions), **summary_extra},
    }
    return {
        "gene": GENE_BLOCK,
        "annotations": {
            "string_ppi": [
                {
                    "version": "v12",
                    "data": data,
                    "metadata": {},
                    "updated_at": "2026-01-01T00:00:00Z",
                }
            ]
        },
    }


def _mock(payload: dict) -> None:
    respx.get(ANN_URL, params={"source": "string_ppi"}).mock(
        return_value=httpx.Response(200, json=payload)
    )


# --------------------------------------------------------------------------- #
# Registration                                                                #
# --------------------------------------------------------------------------- #


async def test_registers_with_readonly_hints() -> None:
    mcp = FastMCP("test")
    register(mcp, None)
    tools = await mcp.list_tools()
    t = next(t for t in tools if t.name == "kgdb_get_interaction_partners")
    assert t.annotations.readOnlyHint is True
    assert t.annotations.idempotentHint is True
    assert t.annotations.openWorldHint is False
    assert t.annotations.title == "Get STRING Interaction Partners"


# --------------------------------------------------------------------------- #
# Happy path: filter, rank, resolve_with, summary                             #
# --------------------------------------------------------------------------- #


@respx.mock
async def test_filters_ranks_and_attaches_resolve_with() -> None:
    interactions = [
        _partner("LOWGENE", 300),
        _partner("MIDGENE", 600),
        _partner("TOPGENE", 950),
    ]
    _mock(_string_payload(interactions))
    client = ApiClient(base_url=BASE)
    try:
        mcp = FastMCP("test")
        register(mcp, client)
        r = await mcp.call_tool(
            "kgdb_get_interaction_partners",
            {"gene_id": GENE_ID, "min_string_score": 400},
        )
        sc = r.structured_content

        assert sc["data_class"] == INTERACTION
        assert sc["gene"] == GENE_BLOCK

        partners = sc["partners"]
        # LOWGENE (300) filtered out; ranked desc by string_score
        symbols = [p["partner_symbol"] for p in partners]
        assert symbols == ["TOPGENE", "MIDGENE"]

        # resolve_with directive present and correct
        top = partners[0]
        assert top["resolve_with"] == {
            "tool": "kgdb_get_gene",
            "argument": "gene_symbol",
            "value": "TOPGENE",
        }

        # summary block surfaced
        assert sc["summary"]["total_interactions"] == 3
        assert sc["summary"]["ppi_degree"] == 3
        assert sc["summary"]["ppi_percentile"] == 0.87
    finally:
        await client.aclose()


@respx.mock
async def test_limit_caps_partner_count_with_signal() -> None:
    interactions = [_partner(f"G{i:03d}", 500 + i) for i in range(40)]
    _mock(_string_payload(interactions))
    client = ApiClient(base_url=BASE)
    try:
        mcp = FastMCP("test")
        register(mcp, client)
        r = await mcp.call_tool(
            "kgdb_get_interaction_partners",
            {"gene_id": GENE_ID, "limit": 5, "response_mode": "full"},
        )
        sc = r.structured_content
        assert len(sc["partners"]) == 5
        # highest scores first
        assert sc["partners"][0]["string_score"] == 539
        # sample_with_signal surfaced truncation in meta
        assert sc["meta"]["partners_total"] == 40
        assert sc["meta"]["partners_returned"] == 5
        assert sc["meta"]["partners_truncated"] is True
    finally:
        await client.aclose()


@respx.mock
async def test_no_interactions_returns_empty_partners() -> None:
    _mock(_string_payload([]))
    client = ApiClient(base_url=BASE)
    try:
        mcp = FastMCP("test")
        register(mcp, client)
        r = await mcp.call_tool(
            "kgdb_get_interaction_partners", {"gene_id": GENE_ID}
        )
        sc = r.structured_content
        assert sc["partners"] == []
        assert sc["summary"]["total_interactions"] == 0
    finally:
        await client.aclose()


@respx.mock
async def test_missing_string_ppi_record_handled() -> None:
    # Gene exists but has no string_ppi annotation row.
    respx.get(ANN_URL, params={"source": "string_ppi"}).mock(
        return_value=httpx.Response(
            200, json={"gene": GENE_BLOCK, "annotations": {}}
        )
    )
    client = ApiClient(base_url=BASE)
    try:
        mcp = FastMCP("test")
        register(mcp, client)
        r = await mcp.call_tool(
            "kgdb_get_interaction_partners", {"gene_id": GENE_ID}
        )
        sc = r.structured_content
        assert sc["partners"] == []
        assert sc["summary"] == {}
        assert sc["uri"] == "kidney-genetics://gene/PKD1"
    finally:
        await client.aclose()


@respx.mock
async def test_budget_trims_partner_list() -> None:
    # Many partners with bulky symbols so compact's 12000-char budget trips even
    # though limit is large.
    interactions = [_partner("PARTNER" + "X" * 50 + f"{i:03d}", 900) for i in range(60)]
    _mock(_string_payload(interactions))
    client = ApiClient(base_url=BASE)
    try:
        mcp = FastMCP("test")
        register(mcp, client)
        r = await mcp.call_tool(
            "kgdb_get_interaction_partners",
            {"gene_id": GENE_ID, "limit": 60, "response_mode": "compact"},
        )
        sc = r.structured_content
        assert sc["meta"]["truncated"] is True
        assert len(sc["partners"]) >= 1  # never emptied
    finally:
        await client.aclose()


# --------------------------------------------------------------------------- #
# Errors / validation                                                          #
# --------------------------------------------------------------------------- #


@respx.mock
async def test_invalid_min_string_score_returns_invalid_input() -> None:
    client = ApiClient(base_url=BASE)
    try:
        mcp = FastMCP("test")
        register(mcp, client)
        r = await mcp.call_tool(
            "kgdb_get_interaction_partners",
            {"gene_id": GENE_ID, "min_string_score": 5000},
        )
        sc = r.structured_content
        assert sc.get("is_error") is True
        assert sc["error"]["code"] == "invalid_input"
        assert sc["error"]["field"] == "min_string_score"
    finally:
        await client.aclose()


@respx.mock
async def test_invalid_limit_returns_invalid_input() -> None:
    client = ApiClient(base_url=BASE)
    try:
        mcp = FastMCP("test")
        register(mcp, client)
        r = await mcp.call_tool(
            "kgdb_get_interaction_partners",
            {"gene_id": GENE_ID, "limit": 0},
        )
        sc = r.structured_content
        assert sc.get("is_error") is True
        assert sc["error"]["code"] == "invalid_input"
        assert sc["error"]["field"] == "limit"
    finally:
        await client.aclose()


@respx.mock
async def test_not_found_propagates_error_envelope() -> None:
    respx.get(ANN_URL, params={"source": "string_ppi"}).mock(
        return_value=httpx.Response(404)
    )
    client = ApiClient(base_url=BASE)
    try:
        mcp = FastMCP("test")
        register(mcp, client)
        r = await mcp.call_tool(
            "kgdb_get_interaction_partners", {"gene_id": GENE_ID}
        )
        sc = r.structured_content
        assert sc.get("is_error") is True
        assert sc["error"]["code"] == "not_found"
    finally:
        await client.aclose()
