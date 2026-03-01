"""
Tests for UniProt ID Mapping API integration.

Verifies that the ID Mapping workflow (submit → poll → fetch) correctly
replaces OR-query batches, and that parsed results match the existing
_parse_protein_data field names.
"""

from __future__ import annotations

from typing import Any
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.pipeline.sources.annotations.uniprot import UniProtAnnotationSource

# ---------------------------------------------------------------------------
# Fixtures: sample API responses
# ---------------------------------------------------------------------------

SUBMIT_RESPONSE: dict[str, str] = {"jobId": "abc123"}

STATUS_RUNNING: dict[str, str] = {"jobStatus": "RUNNING"}
STATUS_FINISHED: dict[str, Any] = {"jobStatus": "FINISHED"}

# Minimal UniProtKB entry in the same shape as /uniprotkb/search results
_PKD1_ENTRY: dict[str, Any] = {
    "primaryAccession": "P98161",
    "uniProtkbId": "PKD1_HUMAN",
    "organism": {"scientificName": "Homo sapiens"},
    "proteinDescription": {
        "recommendedName": {"fullName": {"value": "Polycystin-1"}},
    },
    "genes": [{"geneName": {"value": "PKD1"}}],
    "sequence": {"length": 4302},
    "comments": [
        {
            "commentType": "FUNCTION",
            "texts": [{"value": "Involved in cell-cell/matrix interactions."}],
        }
    ],
    "features": [
        {
            "type": "Domain",
            "description": "PKD",
            "location": {"start": {"value": 100}, "end": {"value": 200}},
            "evidences": [{"evidenceCode": "ECO:0000269"}],
        },
        {
            "type": "Transmembrane",
            "description": "Helical",
            "location": {"start": {"value": 3074}, "end": {"value": 3094}},
        },
    ],
    "uniProtKBCrossReferences": [
        {
            "database": "Pfam",
            "id": "PF00801",
            "properties": [{"key": "entry name", "value": "PKD_dom"}],
        },
    ],
}

_PKD2_ENTRY: dict[str, Any] = {
    "primaryAccession": "Q13563",
    "uniProtkbId": "PKD2_HUMAN",
    "organism": {"scientificName": "Homo sapiens"},
    "proteinDescription": {
        "recommendedName": {"fullName": {"value": "Polycystin-2"}},
    },
    "genes": [{"geneName": {"value": "PKD2"}}],
    "sequence": {"length": 968},
    "comments": [],
    "features": [],
    "uniProtKBCrossReferences": [],
}

# ID Mapping results response wraps each entry in {from, to}
ID_MAPPING_RESULTS: dict[str, Any] = {
    "results": [
        {"from": "PKD1", "to": _PKD1_ENTRY},
        {"from": "PKD2", "to": _PKD2_ENTRY},
    ],
}


def _make_source() -> UniProtAnnotationSource:
    """Create a UniProtAnnotationSource without __init__ (no DB needed)."""
    source = UniProtAnnotationSource.__new__(UniProtAnnotationSource)
    source.base_url = "https://rest.uniprot.org"
    source.batch_size = 100
    source.source_name = "uniprot"
    source.requests_per_second = 5.0
    return source


# ---------------------------------------------------------------------------
# Tests: _parse_id_mapping_results
# ---------------------------------------------------------------------------


@pytest.mark.unit
class TestIdMappingResultParsing:
    """Test that ID Mapping results are correctly parsed into gene-keyed dict."""

    def test_parse_maps_from_field_to_gene_symbol(self) -> None:
        """Each result's 'from' field becomes the gene symbol key."""
        source = _make_source()
        parsed = source._parse_id_mapping_results(ID_MAPPING_RESULTS)

        assert "PKD1" in parsed
        assert "PKD2" in parsed

    def test_parse_extracts_accession(self) -> None:
        """Parsed annotation contains primaryAccession."""
        source = _make_source()
        parsed = source._parse_id_mapping_results(ID_MAPPING_RESULTS)

        assert parsed["PKD1"]["accession"] == "P98161"

    def test_parse_extracts_protein_name(self) -> None:
        """Parsed annotation contains protein_name."""
        source = _make_source()
        parsed = source._parse_id_mapping_results(ID_MAPPING_RESULTS)

        assert parsed["PKD1"]["protein_name"] == "Polycystin-1"

    def test_parse_extracts_domains(self) -> None:
        """Parsed annotation contains domain list."""
        source = _make_source()
        parsed = source._parse_id_mapping_results(ID_MAPPING_RESULTS)

        domains = parsed["PKD1"]["domains"]
        assert len(domains) == 2
        assert domains[0]["type"] == "Domain"
        assert domains[0]["start"] == 100
        assert domains[0]["end"] == 200

    def test_parse_extracts_transmembrane_flag(self) -> None:
        """has_transmembrane is True when Transmembrane features exist."""
        source = _make_source()
        parsed = source._parse_id_mapping_results(ID_MAPPING_RESULTS)

        assert parsed["PKD1"]["has_transmembrane"] is True
        assert parsed["PKD2"]["has_transmembrane"] is False

    def test_parse_extracts_pfam_refs(self) -> None:
        """Parsed annotation contains Pfam cross-references."""
        source = _make_source()
        parsed = source._parse_id_mapping_results(ID_MAPPING_RESULTS)

        pfam = parsed["PKD1"]["pfam_refs"]
        assert len(pfam) == 1
        assert pfam[0]["id"] == "PF00801"

    def test_parse_extracts_function(self) -> None:
        """Parsed annotation contains function text from comments."""
        source = _make_source()
        parsed = source._parse_id_mapping_results(ID_MAPPING_RESULTS)

        assert "cell-cell/matrix" in parsed["PKD1"]["function"]

    def test_parse_extracts_length(self) -> None:
        """Parsed annotation contains sequence length."""
        source = _make_source()
        parsed = source._parse_id_mapping_results(ID_MAPPING_RESULTS)

        assert parsed["PKD1"]["length"] == 4302
        assert parsed["PKD2"]["length"] == 968

    def test_parse_skips_entries_without_accession(self) -> None:
        """Entries missing primaryAccession are skipped."""
        source = _make_source()
        results = {
            "results": [
                {"from": "BOGUS", "to": {"genes": [{"geneName": {"value": "BOGUS"}}]}},
            ],
        }
        parsed = source._parse_id_mapping_results(results)

        assert "BOGUS" not in parsed

    def test_parse_empty_results(self) -> None:
        """Empty results list produces empty dict."""
        source = _make_source()
        parsed = source._parse_id_mapping_results({"results": []})

        assert parsed == {}


# ---------------------------------------------------------------------------
# Tests: PKD1/PRKD1 disambiguation
# ---------------------------------------------------------------------------


@pytest.mark.unit
class TestPKD1Disambiguation:
    """The 'from' field in ID Mapping results resolves gene name ambiguity."""

    def test_from_field_prevents_misassignment(self) -> None:
        """PKD1 and PRKD1 are mapped to separate entries via 'from' field."""
        source = _make_source()

        prkd1_entry = {
            "primaryAccession": "Q15139",
            "uniProtkbId": "KPCD1_HUMAN",
            "organism": {"scientificName": "Homo sapiens"},
            "proteinDescription": {
                "recommendedName": {
                    "fullName": {"value": "Serine/threonine-protein kinase D1"}
                },
            },
            "genes": [{"geneName": {"value": "PRKD1"}}],
            "sequence": {"length": 912},
            "comments": [],
            "features": [],
            "uniProtKBCrossReferences": [],
        }

        results = {
            "results": [
                {"from": "PKD1", "to": _PKD1_ENTRY},
                {"from": "PRKD1", "to": prkd1_entry},
            ],
        }

        parsed = source._parse_id_mapping_results(results)

        assert parsed["PKD1"]["accession"] == "P98161"
        assert parsed["PRKD1"]["accession"] == "Q15139"


# ---------------------------------------------------------------------------
# Tests: fetch_batch with ID Mapping
# ---------------------------------------------------------------------------


def _make_gene(gene_id: int, symbol: str) -> MagicMock:
    """Create a mock Gene object."""
    gene = MagicMock()
    gene.id = gene_id
    gene.approved_symbol = symbol
    return gene


@pytest.mark.unit
class TestFetchBatchIdMapping:
    """Test that fetch_batch uses ID Mapping API."""

    @pytest.mark.asyncio
    async def test_batch_uses_id_mapping_when_available(self) -> None:
        """fetch_batch delegates to _fetch_via_id_mapping."""
        source = _make_source()
        source.rate_limiter = MagicMock()
        source.rate_limiter.wait = AsyncMock()

        genes = [_make_gene(1, "PKD1"), _make_gene(2, "PKD2")]

        with patch.object(
            source,
            "_fetch_via_id_mapping",
            new_callable=AsyncMock,
            return_value={1: {"accession": "P98161"}, 2: {"accession": "Q13563"}},
        ) as mock_idmap:
            results = await source.fetch_batch(genes)

        mock_idmap.assert_awaited_once()
        assert 1 in results
        assert 2 in results

    @pytest.mark.asyncio
    async def test_batch_falls_back_on_id_mapping_failure(self) -> None:
        """fetch_batch falls back to OR-query batches on error."""
        source = _make_source()
        source.rate_limiter = MagicMock()
        source.rate_limiter.wait = AsyncMock()

        genes = [_make_gene(1, "PKD1")]

        with (
            patch.object(
                source,
                "_fetch_via_id_mapping",
                new_callable=AsyncMock,
                side_effect=Exception("ID mapping failed"),
            ),
            patch.object(
                source,
                "_fetch_batch_or_query",
                new_callable=AsyncMock,
                return_value={1: {"accession": "P98161"}},
            ) as mock_or_query,
        ):
            results = await source.fetch_batch(genes)

        mock_or_query.assert_awaited_once()
        assert 1 in results


# ---------------------------------------------------------------------------
# Tests: _build_id_mapping_gene_map
# ---------------------------------------------------------------------------


@pytest.mark.unit
class TestIdMappingGeneMap:
    """Test gene-symbol-to-gene-id mapping for batch results."""

    def test_maps_parsed_results_to_gene_ids(self) -> None:
        """Parsed symbol-keyed results are remapped to gene IDs."""
        source = _make_source()

        parsed = {
            "PKD1": {"accession": "P98161", "gene_symbol": "PKD1"},
            "PKD2": {"accession": "Q13563", "gene_symbol": "PKD2"},
        }
        genes = [_make_gene(10, "PKD1"), _make_gene(20, "PKD2")]

        mapped = source._map_parsed_to_gene_ids(parsed, genes)

        assert mapped[10]["accession"] == "P98161"
        assert mapped[20]["accession"] == "Q13563"

    def test_missing_genes_are_excluded(self) -> None:
        """Genes not in parsed results are not in output."""
        source = _make_source()

        parsed = {"PKD1": {"accession": "P98161", "gene_symbol": "PKD1"}}
        genes = [_make_gene(10, "PKD1"), _make_gene(20, "MISSING")]

        mapped = source._map_parsed_to_gene_ids(parsed, genes)

        assert 10 in mapped
        assert 20 not in mapped
