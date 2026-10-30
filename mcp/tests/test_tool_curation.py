"""Tests for the kgdb_list_curated_associations tool + curation service (#437)."""

from __future__ import annotations

import httpx
import pytest
import respx
from fastmcp import FastMCP

from kidney_genetics_mcp.client.allowlist import is_allowed
from kidney_genetics_mcp.client.api_client import ApiClient
from kidney_genetics_mcp.services.dataclass import CURATED_ASSOCIATION
from kidney_genetics_mcp.tools.curation import register

BASE = "http://api.test"
LIST = f"{BASE}/api/curation/associations/"

_MENDELIAN = {
    "id": 1,
    "gene_symbol": "PKD1",
    "disease_id": "MONDO:0008263",
    "disease_name": "polycystic kidney disease 1",
    "relationship_type": "mendelian",
    "evidence_strength": "Definitive",
    "moi": "HP:0000006",
    "moi_label": "Autosomal dominant inheritance",
    "methodology": "Kidney Gene Curation",
    "methodology_version": "draft iteration 3",
    "citations": ["PMID:1"],
    "source": "kgdb",
    "diagnostics": {"detectability": [{"challenge": "pseudogenes"}], "resources": []},
    "status": "published",
    "published_at": "2026-10-30T00:00:00Z",
}
_RISK = {
    **_MENDELIAN,
    "id": 2,
    "gene_symbol": "CFI",
    "relationship_type": "susceptibility",
    "evidence_strength": "Likely association",
}


def _make() -> tuple[FastMCP, ApiClient]:  # type: ignore[type-arg]
    mcp: FastMCP = FastMCP("test")  # type: ignore[type-arg]
    client = ApiClient(base_url=BASE)
    register(mcp, client)
    return mcp, client


@pytest.mark.parametrize(
    ("method", "path", "allowed"),
    [
        ("GET", "/api/curation/associations/", True),
        ("GET", "/api/curation/associations", True),
        ("GET", "/api/curation/associations/workflow", False),
        ("GET", "/api/curation/associations/5", False),
        ("GET", "/api/curation/associations/5/publish", False),
        ("POST", "/api/curation/associations/", False),
        ("PATCH", "/api/curation/associations/5", False),
    ],
)
def test_allowlist_exposes_only_the_public_list(
    method: str, path: str, allowed: bool
) -> None:
    assert is_allowed(method, path) is allowed


async def test_registers_with_readonly_hints_and_scope_note() -> None:
    mcp: FastMCP = FastMCP("test")  # type: ignore[type-arg]
    register(mcp, None)
    tool = next(
        t for t in await mcp.list_tools() if t.name == "kgdb_list_curated_associations"
    )
    assert tool.annotations.read_only_hint is True
    assert tool.annotations.idempotent_hint is True
    assert tool.annotations.open_world_hint is False
    assert "not part of the evidence score" in (tool.description or "")


@respx.mock
async def test_filters_by_relationship_type_and_forwards_gene() -> None:
    route = respx.get(LIST).mock(
        return_value=httpx.Response(
            200, json={"data": [_MENDELIAN, _RISK], "meta": {"total": 2}}
        )
    )
    mcp, client = _make()
    r = await mcp.call_tool(
        "kgdb_list_curated_associations",
        {"gene_symbol": "CFI", "relationship_type": "susceptibility"},
    )
    await client.aclose()

    sc = r.structured_content
    assert sc["data_class"] == CURATED_ASSOCIATION
    assert [a["gene_symbol"] for a in sc["associations"]] == ["CFI"]
    assert "gene_symbol=CFI" in str(route.calls.last.request.url)


@respx.mock
async def test_minimal_omits_diagnostics_full_keeps_them() -> None:
    respx.get(LIST).mock(
        return_value=httpx.Response(
            200, json={"data": [_MENDELIAN], "meta": {"total": 1}}
        )
    )
    mcp, client = _make()
    minimal = (
        await mcp.call_tool(
            "kgdb_list_curated_associations", {"response_mode": "minimal"}
        )
    ).structured_content
    full = (
        await mcp.call_tool("kgdb_list_curated_associations", {"response_mode": "full"})
    ).structured_content
    await client.aclose()

    assert set(minimal["associations"][0]) == {
        "gene_symbol",
        "disease_id",
        "disease_name",
        "relationship_type",
        "evidence_strength",
        "moi",
    }
    assert full["associations"][0]["diagnostics"] == _MENDELIAN["diagnostics"]
    assert full["associations"][0]["citations"] == ["PMID:1"]
