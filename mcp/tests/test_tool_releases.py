"""Tests for the kgdb_get_release_citation tool + releases service."""

from __future__ import annotations

import httpx
import respx
from fastmcp import FastMCP

from kidney_genetics_mcp.client.api_client import ApiClient
from kidney_genetics_mcp.services.citation import CONCEPT_DOI
from kidney_genetics_mcp.services.dataclass import RELEASE
from kidney_genetics_mcp.tools.statistics import register

BASE = "http://api.test"
RELEASES = f"{BASE}/api/releases/"

_RELEASE_NEW = {
    "id": 2,
    "version": "2026.06",
    "status": "published",
    "release_date": "2026-06-01T00:00:00",
    "published_at": "2026-06-02T00:00:00",
    "gene_count": 5080,
    "total_evidence_count": 18000,
    "export_file_path": "/data/exports/kgdb_2026.06.json",
    "export_checksum": "abc123def456",
    "doi": "10.5281/zenodo.7654321",
    "citation_text": "Kidney-Genetics-DB data release 2026.06. doi:10.5281/zenodo.7654321",
    "release_notes": "June release",
    "created_at": "2026-06-01T00:00:00",
    "updated_at": "2026-06-02T00:00:00",
}

_RELEASE_OLD = {
    **_RELEASE_NEW,
    "id": 1,
    "version": "2026.03",
    "doi": "10.5281/zenodo.1111111",
    "citation_text": None,
    "export_checksum": "old0000",
}

# Endpoint returns releases newest-first (version desc).
_RELEASES_RESPONSE = {
    "data": [_RELEASE_NEW, _RELEASE_OLD],
    "meta": {"total": 2, "limit": 100, "offset": 0},
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
    tool = next(t for t in tools if t.name == "kgdb_get_release_citation")
    assert tool.annotations.readOnlyHint is True
    assert tool.annotations.idempotentHint is True
    assert tool.annotations.openWorldHint is False


@respx.mock
async def test_citation_includes_concept_doi_and_checksum() -> None:
    respx.get(RELEASES).mock(return_value=httpx.Response(200, json=_RELEASES_RESPONSE))
    mcp, client = _make()
    r = await mcp.call_tool("kgdb_get_release_citation", {})
    await client.aclose()

    sc = r.structured_content
    assert sc["data_class"] == RELEASE
    citation = sc["citation"]
    # latest published release is 2026.06
    assert citation["version"] == "2026.06"
    assert citation["doi"] == "10.5281/zenodo.7654321"
    assert citation["concept_doi"] == CONCEPT_DOI
    assert CONCEPT_DOI in citation["recommended_citation"]
    assert citation["recommended_citation"].startswith(
        "Kidney-Genetics-DB data release 2026.06"
    )
    assert sc["export_checksum"] == "abc123def456"
    assert sc["release"]["gene_count"] == 5080


@respx.mock
async def test_status_published_filter_forwarded() -> None:
    route = respx.get(RELEASES).mock(
        return_value=httpx.Response(200, json=_RELEASES_RESPONSE)
    )
    mcp, client = _make()
    await mcp.call_tool("kgdb_get_release_citation", {})
    await client.aclose()

    url_str = str(route.calls.last.request.url)
    assert "status=published" in url_str


@respx.mock
async def test_no_published_release_returns_not_found() -> None:
    respx.get(RELEASES).mock(
        return_value=httpx.Response(200, json={"data": [], "meta": {"total": 0}})
    )
    mcp, client = _make()
    r = await mcp.call_tool("kgdb_get_release_citation", {})
    await client.aclose()

    sc = r.structured_content
    assert sc.get("is_error") is True
    assert sc["error"]["code"] == "not_found"


@respx.mock
async def test_citation_assembled_when_no_citation_text() -> None:
    # Only the draft-less old release (no citation_text) present.
    respx.get(RELEASES).mock(
        return_value=httpx.Response(
            200, json={"data": [_RELEASE_OLD], "meta": {"total": 1}}
        )
    )
    mcp, client = _make()
    r = await mcp.call_tool("kgdb_get_release_citation", {})
    await client.aclose()

    sc = r.structured_content
    cite = sc["citation"]["recommended_citation"]
    assert "2026.03" in cite
    assert "doi:10.5281/zenodo.1111111" in cite
    assert CONCEPT_DOI in cite


@respx.mock
async def test_upstream_error_mapped() -> None:
    respx.get(RELEASES).mock(return_value=httpx.Response(500))
    mcp, client = _make()
    r = await mcp.call_tool("kgdb_get_release_citation", {})
    await client.aclose()

    sc = r.structured_content
    assert sc.get("is_error") is True
    assert sc["error"]["code"] == "temporarily_unavailable"
