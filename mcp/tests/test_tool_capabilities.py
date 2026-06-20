"""Tests for the kgdb_get_capabilities tool and its descriptor service."""

from __future__ import annotations

from typing import Any

import pytest
from fastmcp import FastMCP

from kidney_genetics_mcp.contract import (
    ANNOTATION_SOURCE_VALUES,
    EVIDENCE_GROUP_VALUES,
    EVIDENCE_SOURCE_VALUES,
    EVIDENCE_TIER_VALUES,
    GENE_SORT_FIELD_VALUES,
)
from kidney_genetics_mcp.services.capabilities import build_capabilities
from kidney_genetics_mcp.services.resources import register_resources
from kidney_genetics_mcp.tools import capabilities as cap_tool

_EXPECTED_TOOLS = {
    "kgdb_get_capabilities",
    "kgdb_resolve_gene",
    "kgdb_search_genes",
    "kgdb_get_gene",
    "kgdb_get_gene_evidence",
    "kgdb_get_gene_annotations",
    "kgdb_get_constraint_summary",
    "kgdb_get_interaction_partners",
    "kgdb_get_database_stats",
    "kgdb_list_sources",
    "kgdb_get_release_citation",
}


async def _call_capabilities() -> dict[str, Any]:
    """Register the tool on a fresh FastMCP and invoke it, returning the result."""
    mcp = FastMCP("test-capabilities")
    # Resources must be registered so the descriptor can content-hash them.
    register_resources(mcp)
    cap_tool.register(mcp, None)
    tool = await mcp.get_tool("kgdb_get_capabilities")
    result: dict[str, Any] = await tool.fn()
    return result


async def test_tool_registers_and_returns_descriptor() -> None:
    result = await _call_capabilities()
    assert result["data_class"] == "operational_metadata"
    assert "meta" in result
    assert result["meta"]["descriptor_chars"] == result["descriptor_chars"]


async def test_capabilities_version_is_sha256_token() -> None:
    result = await _call_capabilities()
    version = result["capabilities_version"]
    assert isinstance(version, str)
    assert version.startswith("sha256:")
    # "sha256:" + 16 hex chars
    assert len(version) == len("sha256:") + 16


async def test_descriptor_chars_present_and_int() -> None:
    result = await _call_capabilities()
    assert "descriptor_chars" in result
    assert isinstance(result["descriptor_chars"], int)
    assert result["descriptor_chars"] > 0


async def test_all_eleven_tools_present() -> None:
    result = await _call_capabilities()
    names = {tool["name"] for tool in result["tools"]}
    assert names == _EXPECTED_TOOLS
    assert len(result["tools"]) == 11


async def test_filterable_fields_populated_from_enums() -> None:
    result = await _call_capabilities()
    ff = result["filterable_fields"]

    # search_genes: tier / group / source / sort sourced from contract enums.
    search = ff["kgdb_search_genes"]
    assert search["tier"]["values"] == list(EVIDENCE_TIER_VALUES)
    assert search["group"]["values"] == list(EVIDENCE_GROUP_VALUES)
    assert search["source"]["values"] == list(EVIDENCE_SOURCE_VALUES)
    assert search["sort"]["values"] == list(GENE_SORT_FIELD_VALUES)

    # evidence sources enum.
    evidence = ff["kgdb_get_gene_evidence"]
    assert evidence["sources"]["values"] == list(EVIDENCE_SOURCE_VALUES)

    # annotation sources enum.
    annotations = ff["kgdb_get_gene_annotations"]
    assert annotations["source"]["values"] == list(ANNOTATION_SOURCE_VALUES)


async def test_descriptor_has_required_top_level_keys() -> None:
    result = await _call_capabilities()
    required = {
        "canonical_workflows",
        "tools",
        "filterable_fields",
        "payload_modes",
        "limits",
        "identifiers",
        "pagination_semantics",
        "citation_contract",
        "error_codes",
        "data_classes",
        "exclusions",
        "safety",
        "resources",
        "capabilities_version",
        "descriptor_chars",
    }
    assert required.issubset(result.keys())


async def test_payload_modes_have_char_budgets() -> None:
    result = await _call_capabilities()
    modes = result["payload_modes"]
    assert set(modes) == {"minimal", "compact", "standard", "full"}
    assert modes["minimal"]["char_budget"] == 4000
    assert modes["compact"]["char_budget"] == 12000
    assert modes["standard"]["char_budget"] == 24000
    assert modes["full"]["char_budget"] == 48000


async def test_error_codes_have_examples() -> None:
    result = await _call_capabilities()
    codes = result["error_codes"]
    assert set(codes) == {
        "invalid_input",
        "not_found",
        "ambiguous_query",
        "temporarily_unavailable",
    }
    for code, body in codes.items():
        assert body["example"], f"{code} missing example"


async def test_identifiers_cover_all_forms() -> None:
    result = await _call_capabilities()
    ids = result["identifiers"]
    for key in ("hgnc_id", "approved_symbol", "gene_id", "ensembl", "ncbi", "uniprot"):
        assert key in ids
        assert ids[key]


async def test_citation_contract_cites_concept_doi() -> None:
    result = await _call_capabilities()
    assert "10.5281/zenodo.19316248" in result["citation_contract"]
    assert result["concept_doi"] == "10.5281/zenodo.19316248"


async def test_safety_block_present() -> None:
    result = await _call_capabilities()
    safety = result["safety"]
    assert "research use only" in safety["disclaimer"].lower()
    assert "clinical decision support" in safety["disclaimer"].lower()
    assert "not instructions" in safety["injection_notice"].lower()


def test_capabilities_version_is_deterministic() -> None:
    first = build_capabilities()
    second = build_capabilities()
    assert first["capabilities_version"] == second["capabilities_version"]
    assert first["descriptor_chars"] == second["descriptor_chars"]
    # The full descriptors must be byte-for-byte identical (no timestamps).
    import json

    assert json.dumps(first, sort_keys=True, default=str) == json.dumps(
        second, sort_keys=True, default=str
    )


def test_exclusions_advertise_deferred_capabilities() -> None:
    descriptor = build_capabilities()
    joined = " ".join(descriptor["exclusions"]).lower()
    assert "not yet available" in joined
    assert "network" in joined  # heavy network build/cluster
    assert "enrich" in joined  # GO/Enrichr enrichment


@pytest.mark.parametrize("tool_name", sorted(_EXPECTED_TOOLS))
def test_every_expected_tool_in_inventory(tool_name: str) -> None:
    descriptor = build_capabilities()
    names = {tool["name"] for tool in descriptor["tools"]}
    assert tool_name in names
