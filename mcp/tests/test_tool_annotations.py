"""Tests for the kgdb_get_gene_annotations tool (registration + behavior)."""

from __future__ import annotations

import httpx
import respx
from fastmcp import FastMCP

from kidney_genetics_mcp.client.api_client import ApiClient
from kidney_genetics_mcp.services.dataclass import ANNOTATION
from kidney_genetics_mcp.tools.annotations import register

BASE = "http://test-backend"
GENE_ID = 42
ANN_URL = f"{BASE}/api/annotations/genes/{GENE_ID}/annotations"

GENE_BLOCK = {"id": GENE_ID, "symbol": "PKD1", "hgnc_id": "HGNC:9008"}

ANNOTATIONS_PAYLOAD = {
    "gene": GENE_BLOCK,
    "annotations": {
        "hgnc": [
            {
                "version": "2024-01",
                "data": {
                    "symbol": "PKD1",
                    "name": "polycystin 1",
                    "extra_blob": "x" * 200,
                    "summary": {"alias_count": 3},
                },
                "metadata": {"source_url": "http://example.test/hgnc"},
                "updated_at": "2026-01-01T00:00:00Z",
            }
        ],
        "gnomad": [
            {
                "version": "v4",
                "data": {"pli": 1.0, "oe_lof": 0.05, "internal": "y" * 200},
                "metadata": {"build": "GRCh38"},
                "updated_at": "2026-02-01T00:00:00Z",
            }
        ],
    },
}


def _mock(payload: dict = ANNOTATIONS_PAYLOAD) -> None:
    respx.get(ANN_URL).mock(return_value=httpx.Response(200, json=payload))


# --------------------------------------------------------------------------- #
# Registration                                                                #
# --------------------------------------------------------------------------- #


async def test_registers_with_readonly_hints() -> None:
    mcp = FastMCP("test")
    register(mcp, None)
    tools = await mcp.list_tools()
    t = next(t for t in tools if t.name == "kgdb_get_gene_annotations")
    assert t.annotations.readOnlyHint is True
    assert t.annotations.idempotentHint is True
    assert t.annotations.openWorldHint is False
    assert t.annotations.title == "Get Gene Descriptive Annotations"


async def test_registers_with_client_none() -> None:
    mcp = FastMCP("test")
    register(mcp, None)
    names = [t.name for t in await mcp.list_tools()]
    assert "kgdb_get_gene_annotations" in names


# --------------------------------------------------------------------------- #
# Happy path + mode projection                                                #
# --------------------------------------------------------------------------- #


@respx.mock
async def test_compact_returns_summary_not_full_data() -> None:
    _mock()
    client = ApiClient(base_url=BASE)
    try:
        mcp = FastMCP("test")
        register(mcp, client)
        r = await mcp.call_tool("kgdb_get_gene_annotations", {"gene_id": GENE_ID})
        sc = r.structured_content
        assert sc["data_class"] == ANNOTATION
        assert sc["gene"] == GENE_BLOCK
        assert sc["meta"]["response_mode"] == "compact"
        hgnc = sc["annotations"]["hgnc"][0]
        # compact: summary block lifted, but no full data / metadata
        assert "summary" in hgnc
        assert hgnc["summary"]["symbol"] == "PKD1"
        assert hgnc["summary"]["summary"] == {"alias_count": 3}
        assert "data" not in hgnc
        assert "metadata" not in hgnc
    finally:
        await client.aclose()


@respx.mock
async def test_minimal_returns_only_versions() -> None:
    _mock()
    client = ApiClient(base_url=BASE)
    try:
        mcp = FastMCP("test")
        register(mcp, client)
        r = await mcp.call_tool(
            "kgdb_get_gene_annotations",
            {"gene_id": GENE_ID, "response_mode": "minimal"},
        )
        sc = r.structured_content
        hgnc = sc["annotations"]["hgnc"][0]
        assert hgnc == {"version": "2024-01"}
    finally:
        await client.aclose()


@respx.mock
async def test_standard_includes_full_data_blob() -> None:
    _mock()
    client = ApiClient(base_url=BASE)
    try:
        mcp = FastMCP("test")
        register(mcp, client)
        r = await mcp.call_tool(
            "kgdb_get_gene_annotations",
            {"gene_id": GENE_ID, "response_mode": "standard"},
        )
        sc = r.structured_content
        hgnc = sc["annotations"]["hgnc"][0]
        assert hgnc["data"]["name"] == "polycystin 1"
        assert "metadata" not in hgnc  # metadata only in full
    finally:
        await client.aclose()


@respx.mock
async def test_full_returns_everything() -> None:
    _mock()
    client = ApiClient(base_url=BASE)
    try:
        mcp = FastMCP("test")
        register(mcp, client)
        r = await mcp.call_tool(
            "kgdb_get_gene_annotations",
            {"gene_id": GENE_ID, "response_mode": "full"},
        )
        sc = r.structured_content
        hgnc = sc["annotations"]["hgnc"][0]
        assert hgnc["metadata"] == {"source_url": "http://example.test/hgnc"}
        assert hgnc["data"]["extra_blob"]
    finally:
        await client.aclose()


@respx.mock
async def test_source_filter_forwarded_as_query_param() -> None:
    route = respx.get(ANN_URL, params={"source": "gnomad"}).mock(
        return_value=httpx.Response(
            200,
            json={
                "gene": GENE_BLOCK,
                "annotations": {"gnomad": ANNOTATIONS_PAYLOAD["annotations"]["gnomad"]},
            },
        )
    )
    client = ApiClient(base_url=BASE)
    try:
        mcp = FastMCP("test")
        register(mcp, client)
        r = await mcp.call_tool(
            "kgdb_get_gene_annotations",
            {"gene_id": GENE_ID, "source": "gnomad"},
        )
        sc = r.structured_content
        assert route.called
        assert set(sc["annotations"].keys()) == {"gnomad"}
    finally:
        await client.aclose()


# --------------------------------------------------------------------------- #
# Errors                                                                       #
# --------------------------------------------------------------------------- #


async def test_service_rejects_unknown_source() -> None:
    # The service layer has its own defensive guard (the tool param is enum-typed
    # so this is belt-and-suspenders). Call the service directly to assert it.
    from kidney_genetics_mcp.services import annotations as annotations_service
    from kidney_genetics_mcp.services.errors import McpToolError

    client = ApiClient(base_url=BASE)
    try:
        try:
            await annotations_service.get_gene_annotations(
                client, gene_id=GENE_ID, source="not_a_source"
            )
        except McpToolError as exc:
            assert exc.code == "invalid_input"
            assert exc.details["field"] == "source"
            assert exc.details["allowed"] is not None
        else:  # pragma: no cover — should not reach here
            raise AssertionError("expected invalid_input for unknown source")
    finally:
        await client.aclose()


@respx.mock
async def test_not_found_propagates_error_envelope() -> None:
    respx.get(ANN_URL).mock(return_value=httpx.Response(404))
    client = ApiClient(base_url=BASE)
    try:
        mcp = FastMCP("test")
        register(mcp, client)
        r = await mcp.call_tool("kgdb_get_gene_annotations", {"gene_id": GENE_ID})
        sc = r.structured_content
        assert sc.get("is_error") is True
        assert sc["error"]["code"] == "not_found"
        assert "meta" not in sc
    finally:
        await client.aclose()


@respx.mock
async def test_budget_trims_oversized_annotation_lists() -> None:
    # Build a source with many records so compact's 12000-char budget trips.
    big_records = [
        {
            "version": f"v{i}",
            "data": {"name": "z" * 400, "summary": {"k": "v" * 100}},
            "metadata": {},
            "updated_at": "2026-01-01T00:00:00Z",
        }
        for i in range(80)
    ]
    payload = {
        "gene": GENE_BLOCK,
        "annotations": {"hpo": big_records},
    }
    _mock(payload)
    client = ApiClient(base_url=BASE)
    try:
        mcp = FastMCP("test")
        register(mcp, client)
        r = await mcp.call_tool(
            "kgdb_get_gene_annotations",
            {"gene_id": GENE_ID, "response_mode": "compact"},
        )
        sc = r.structured_content
        assert sc["meta"]["truncated"] is True
        assert sc["meta"]["dropped_summary"]["dropped_records"] > 0
        # never empty when a match exists
        assert len(sc["annotations"]["hpo"]) >= 1
    finally:
        await client.aclose()
