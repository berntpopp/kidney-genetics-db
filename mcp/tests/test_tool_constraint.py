"""Tests for the kgdb_get_constraint_summary tool (registration + behavior)."""

from __future__ import annotations

import httpx
import respx
from fastmcp import FastMCP

from kidney_genetics_mcp.client.api_client import ApiClient
from kidney_genetics_mcp.services.dataclass import ANNOTATION
from kidney_genetics_mcp.tools.annotations import register

BASE = "http://test-backend"
GENE_ID = 7
SUMMARY_URL = f"{BASE}/api/annotations/genes/{GENE_ID}/annotations/summary"

SUMMARY_PAYLOAD = {
    "gene_id": GENE_ID,
    "symbol": "PKD2",
    "hgnc_id": "HGNC:9009",
    "identifiers": {
        "ncbi_gene_id": "5311",
        "ensembl_gene_id": "ENSG00000118762",
        "mane_select_transcript": "NM_000297.4",
    },
    "constraint_scores": {
        "pli": 0.99,
        "oe_lof": 0.12,
        "oe_lof_upper": 0.20,
        "oe_lof_lower": 0.07,
        "lof_z": 3.1,
        "mis_z": 1.2,
        "syn_z": -0.3,
        "oe_mis": 0.85,
        "oe_syn": 1.01,
    },
}


def _mock(payload: dict = SUMMARY_PAYLOAD) -> None:
    respx.get(SUMMARY_URL).mock(return_value=httpx.Response(200, json=payload))


# --------------------------------------------------------------------------- #
# Registration                                                                #
# --------------------------------------------------------------------------- #


async def test_registers_with_readonly_hints() -> None:
    mcp = FastMCP("test")
    register(mcp, None)
    tools = await mcp.list_tools()
    t = next(t for t in tools if t.name == "kgdb_get_constraint_summary")
    assert t.annotations.readOnlyHint is True
    assert t.annotations.idempotentHint is True
    assert t.annotations.openWorldHint is False
    assert t.annotations.title == "Get Gene Constraint Summary"


# --------------------------------------------------------------------------- #
# Happy path                                                                   #
# --------------------------------------------------------------------------- #


@respx.mock
async def test_returns_flat_constraint_and_identifiers() -> None:
    _mock()
    client = ApiClient(base_url=BASE)
    try:
        mcp = FastMCP("test")
        register(mcp, client)
        r = await mcp.call_tool("kgdb_get_constraint_summary", {"gene_id": GENE_ID})
        sc = r.structured_content

        assert sc["data_class"] == ANNOTATION
        assert sc["meta"]["response_mode"] == "compact"

        assert sc["gene"] == {"id": GENE_ID, "symbol": "PKD2", "hgnc_id": "HGNC:9009"}

        ident = sc["identifiers"]
        assert ident["ncbi_gene_id"] == "5311"
        assert ident["ensembl_gene_id"] == "ENSG00000118762"
        assert ident["mane_select_transcript"] == "NM_000297.4"

        c = sc["constraint"]
        assert c["pli"] == 0.99
        assert c["oe_lof"] == 0.12
        assert c["oe_lof_upper"] == 0.20
        assert c["oe_lof_lower"] == 0.07
        assert c["lof_z"] == 3.1
        assert c["mis_z"] == 1.2
        assert c["syn_z"] == -0.3
        assert c["oe_mis"] == 0.85
        assert c["oe_syn"] == 1.01
    finally:
        await client.aclose()


@respx.mock
async def test_uri_uses_symbol() -> None:
    _mock()
    client = ApiClient(base_url=BASE)
    try:
        mcp = FastMCP("test")
        register(mcp, client)
        r = await mcp.call_tool("kgdb_get_constraint_summary", {"gene_id": GENE_ID})
        assert r.structured_content["uri"] == "kidney-genetics://gene/PKD2"
    finally:
        await client.aclose()


@respx.mock
async def test_missing_constraint_blocks_yield_nulls() -> None:
    # Summary view rows can have null constraint values for unconstrained genes.
    payload = {
        "gene_id": GENE_ID,
        "symbol": "PKD2",
        "hgnc_id": "HGNC:9009",
        "identifiers": {},
        "constraint_scores": {},
    }
    _mock(payload)
    client = ApiClient(base_url=BASE)
    try:
        mcp = FastMCP("test")
        register(mcp, client)
        r = await mcp.call_tool("kgdb_get_constraint_summary", {"gene_id": GENE_ID})
        sc = r.structured_content
        assert sc["constraint"]["pli"] is None
        assert sc["identifiers"]["ncbi_gene_id"] is None
    finally:
        await client.aclose()


@respx.mock
async def test_response_mode_echoed_in_meta() -> None:
    _mock()
    client = ApiClient(base_url=BASE)
    try:
        mcp = FastMCP("test")
        register(mcp, client)
        r = await mcp.call_tool(
            "kgdb_get_constraint_summary",
            {"gene_id": GENE_ID, "response_mode": "full"},
        )
        assert r.structured_content["meta"]["response_mode"] == "full"
    finally:
        await client.aclose()


# --------------------------------------------------------------------------- #
# Errors                                                                       #
# --------------------------------------------------------------------------- #


@respx.mock
async def test_not_found_returns_error_envelope() -> None:
    respx.get(SUMMARY_URL).mock(return_value=httpx.Response(404))
    client = ApiClient(base_url=BASE)
    try:
        mcp = FastMCP("test")
        register(mcp, client)
        r = await mcp.call_tool("kgdb_get_constraint_summary", {"gene_id": GENE_ID})
        sc = r.structured_content
        assert sc.get("is_error") is True
        assert sc["error"]["code"] == "not_found"
    finally:
        await client.aclose()
