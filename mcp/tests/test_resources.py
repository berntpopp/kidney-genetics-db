"""Tests for static MCP resource loading and registration."""

from __future__ import annotations

import pytest
from fastmcp import FastMCP

from kidney_genetics_mcp.services.errors import McpToolError
from kidney_genetics_mcp.services.resources import (
    RESOURCE_URIS,
    load_resource,
    register_resources,
)

_OVERVIEW = "kidney-genetics://schema/overview"
_TOOL_GUIDE = "kidney-genetics://schema/tool-guide"


def test_resource_uris_are_the_two_expected() -> None:
    assert set(RESOURCE_URIS) == {_OVERVIEW, _TOOL_GUIDE}


def test_load_resource_returns_nonempty_markdown() -> None:
    for uri in RESOURCE_URIS:
        body = load_resource(uri)
        assert isinstance(body, str)
        assert body.strip(), f"{uri} is empty"
        assert "#" in body  # markdown heading present


def test_load_resource_unknown_uri_raises_not_found() -> None:
    with pytest.raises(McpToolError) as excinfo:
        load_resource("kidney-genetics://schema/does-not-exist")
    assert excinfo.value.code == "not_found"


async def test_register_resources_registers_both_uris() -> None:
    mcp = FastMCP("test-resources")
    register_resources(mcp)
    resources = await mcp.list_resources()
    registered = {str(res.uri) for res in resources}
    assert _OVERVIEW in registered
    assert _TOOL_GUIDE in registered


async def test_registered_resources_serve_nonempty_markdown() -> None:
    mcp = FastMCP("test-resources")
    register_resources(mcp)
    for uri in RESOURCE_URIS:
        contents = await mcp.read_resource(uri)
        # FastMCP read_resource returns an object/list of resource contents.
        parts = getattr(contents, "contents", contents)
        body = "".join(part.content for part in parts)
        assert body.strip(), f"{uri} served empty body"
        assert "#" in body


async def test_registered_resource_advertises_markdown_mime() -> None:
    mcp = FastMCP("test-resources")
    register_resources(mcp)
    contents = await mcp.read_resource(_OVERVIEW)
    parts = getattr(contents, "contents", contents)
    assert any(part.mime_type == "text/markdown" for part in parts)


def test_overview_covers_sources_and_score() -> None:
    body = load_resource(_OVERVIEW)
    # 7 evidence sources.
    for source in ("PanelApp", "HPO", "ClinGen", "GenCC", "PubTator", "Literature"):
        assert source in body
    # 10 annotation sources.
    for source in ("hgnc", "gnomad", "clinvar", "ensembl", "uniprot", "string_ppi"):
        assert source in body
    assert "percentage_score" in body
    assert "comprehensive_support" in body  # an evidence tier value
    assert "well_supported" in body  # an evidence group value


def test_tool_guide_covers_workflow_and_safety() -> None:
    body = load_resource(_TOOL_GUIDE).lower()
    assert "kgdb_resolve_gene" in body
    assert "kgdb_get_release_citation" in body
    assert "research use only" in body
    assert "10.5281/zenodo.19316248" in body  # concept DOI in citation contract
    assert "response_mode" in body
