"""Tests for MPO/MGI bulk MouseMine query optimisation."""

import json
from unittest.mock import AsyncMock, MagicMock, Mock, patch

import pytest

from app.pipeline.sources.annotations.mpo_mgi import MPOMGIAnnotationSource


# ── Fixtures ────────────────────────────────────────────────────────────


@pytest.fixture
def source():
    """Create MPOMGIAnnotationSource with mocked session."""
    mock_session = Mock()
    src = MPOMGIAnnotationSource(mock_session)
    # Pre-load MPO terms cache so tests skip the JAX fetch
    src._mpo_terms_cache = {"MP:0000519", "MP:0000520", "MP:0002135"}
    return src


def _make_gene(gene_id: int, symbol: str) -> MagicMock:
    """Create a mock Gene with id and approved_symbol."""
    g = MagicMock()
    g.id = gene_id
    g.approved_symbol = symbol
    return g


# ── _bulk_query_phenotypes ──────────────────────────────────────────────


@pytest.mark.unit
@pytest.mark.asyncio
async def test_bulk_phenotypes_parses_results(source):
    """Bulk phenotype query correctly groups results by human gene symbol."""
    # MouseMine HGene_MPhenotype returns rows:
    # [human_id, human_symbol, human_organism, mouse_id, mouse_symbol, mouse_organism, mpo_id, mpo_name]
    mock_rows = [
        ["HGNC:9008", "PKD1", "H. sapiens", "MGI:1", "Pkd1", "M. musculus", "MP:0000519", "hydroureter"],
        ["HGNC:9008", "PKD1", "H. sapiens", "MGI:1", "Pkd1", "M. musculus", "MP:0099999", "some phenotype"],
        ["HGNC:9009", "PKD2", "H. sapiens", "MGI:2", "Pkd2", "M. musculus", "MP:0000520", "kidney hemorrhage"],
    ]

    mock_response = MagicMock()
    mock_response.status_code = 200
    mock_response.json.return_value = {"results": mock_rows}

    mock_client = AsyncMock()
    mock_client.get = AsyncMock(return_value=mock_response)

    with patch.object(source, "get_http_client", return_value=mock_client):
        with patch.object(source, "apply_rate_limit", new_callable=AsyncMock):
            result = await source._bulk_query_phenotypes(
                ["PKD1", "PKD2", "COL4A3"],
                source._mpo_terms_cache,
            )

    # PKD1: 1 kidney phenotype (MP:0000519), 1 non-kidney (MP:0099999)
    assert result["PKD1"]["has_kidney_phenotype"] is True
    assert result["PKD1"]["phenotype_count"] == 1
    assert result["PKD1"]["mouse_orthologs"] == ["Pkd1"]
    assert result["PKD1"]["total_phenotypes"] == 2

    # PKD2: 1 kidney phenotype
    assert result["PKD2"]["has_kidney_phenotype"] is True
    assert result["PKD2"]["phenotype_count"] == 1

    # COL4A3: no results from API → empty
    assert result["COL4A3"]["has_kidney_phenotype"] is False
    assert result["COL4A3"]["phenotype_count"] == 0
    assert result["COL4A3"]["mouse_orthologs"] == []


@pytest.mark.unit
@pytest.mark.asyncio
async def test_bulk_phenotypes_handles_api_error(source):
    """Bulk phenotype query returns empty results on HTTP error."""
    mock_response = MagicMock()
    mock_response.status_code = 500

    mock_client = AsyncMock()
    mock_client.get = AsyncMock(return_value=mock_response)

    with patch.object(source, "get_http_client", return_value=mock_client):
        with patch.object(source, "apply_rate_limit", new_callable=AsyncMock):
            result = await source._bulk_query_phenotypes(
                ["PKD1"],
                source._mpo_terms_cache,
            )

    # All genes should have empty results
    assert result["PKD1"]["has_kidney_phenotype"] is False
    assert result["PKD1"]["phenotype_count"] == 0


@pytest.mark.unit
@pytest.mark.asyncio
async def test_bulk_phenotypes_chunks_large_lists(source):
    """Requests are chunked when gene list exceeds BULK_CHUNK_SIZE."""
    source.BULK_CHUNK_SIZE = 2  # Small chunk for testing

    call_count = 0

    async def mock_get(*args, **kwargs):
        nonlocal call_count
        call_count += 1
        resp = MagicMock()
        resp.status_code = 200
        resp.json.return_value = {"results": []}
        return resp

    mock_client = AsyncMock()
    mock_client.get = mock_get

    with patch.object(source, "get_http_client", return_value=mock_client):
        with patch.object(source, "apply_rate_limit", new_callable=AsyncMock):
            await source._bulk_query_phenotypes(
                ["G1", "G2", "G3", "G4", "G5"],
                source._mpo_terms_cache,
            )

    # 5 genes / 2 per chunk = 3 chunks
    assert call_count == 3


# ── _bulk_query_zygosity ────────────────────────────────────────────────


@pytest.mark.unit
@pytest.mark.asyncio
async def test_bulk_zygosity_parses_results(source):
    """Zygosity query groups phenotypes by zygosity bucket per gene."""
    # _Genotype_Phenotype rows:
    # [primaryId, symbol, background, zygosity, mpo_id, mpo_name]
    mock_rows = [
        ["MGI:1", "Pkd1", "C57BL/6J", "hm", "MP:0000519", "hydroureter"],
        ["MGI:1", "Pkd1", "C57BL/6J", "hm", "MP:0099999", "non-kidney"],
        ["MGI:1", "Pkd1", "C57BL/6J", "ht", "MP:0000520", "kidney hemorrhage"],
        ["MGI:2", "Pkd2", "C57BL/6J", "cn", "MP:0002135", "abnormal kidney morphology"],
    ]

    mock_response = MagicMock()
    mock_response.status_code = 200
    mock_response.json.return_value = {"results": mock_rows}

    mock_client = AsyncMock()
    mock_client.get = AsyncMock(return_value=mock_response)

    gene_mouse_map = {"PKD1": ["Pkd1"], "PKD2": ["Pkd2"]}

    with patch.object(source, "get_http_client", return_value=mock_client):
        with patch.object(source, "apply_rate_limit", new_callable=AsyncMock):
            result = await source._bulk_query_zygosity(
                gene_mouse_map, source._mpo_terms_cache
            )

    # PKD1 hm: MP:0000519 is kidney, MP:0099999 is not
    assert result["PKD1"]["homozygous"]["phenotype_count"] == 1
    assert result["PKD1"]["homozygous"]["has_kidney_phenotype"] is True

    # PKD1 ht: MP:0000520 is kidney
    assert result["PKD1"]["heterozygous"]["phenotype_count"] == 1
    assert result["PKD1"]["summary"] == "hm (true); ht (true)"

    # PKD2 cn: MP:0002135 is kidney
    assert result["PKD2"]["conditional"]["phenotype_count"] == 1
    assert result["PKD2"]["summary"] == "hm (false); ht (false)"


@pytest.mark.unit
@pytest.mark.asyncio
async def test_bulk_zygosity_handles_api_error(source):
    """Zygosity query returns empty structure on HTTP error."""
    mock_response = MagicMock()
    mock_response.status_code = 500

    mock_client = AsyncMock()
    mock_client.get = AsyncMock(return_value=mock_response)

    with patch.object(source, "get_http_client", return_value=mock_client):
        with patch.object(source, "apply_rate_limit", new_callable=AsyncMock):
            result = await source._bulk_query_zygosity(
                {"PKD1": ["Pkd1"]}, source._mpo_terms_cache
            )

    assert result["PKD1"]["homozygous"]["phenotype_count"] == 0
    assert result["PKD1"]["heterozygous"]["phenotype_count"] == 0
    assert result["PKD1"]["summary"] == "hm (false); ht (false)"


# ── fetch_batch (integration of bulk queries) ───────────────────────────


@pytest.mark.unit
@pytest.mark.asyncio
async def test_fetch_batch_uses_bulk_queries(source):
    """fetch_batch uses bulk queries and assembles per-gene results."""
    genes = [_make_gene(1, "PKD1"), _make_gene(2, "PKD2")]

    pheno_map = {
        "PKD1": {
            "has_kidney_phenotype": True,
            "mouse_orthologs": ["Pkd1"],
            "phenotypes": [{"term": "MP:0000519", "name": "hydroureter"}],
            "phenotype_count": 1,
            "total_phenotypes": 5,
        },
        "PKD2": {
            "has_kidney_phenotype": False,
            "mouse_orthologs": [],
            "phenotypes": [],
            "phenotype_count": 0,
            "total_phenotypes": 0,
        },
    }

    zyg_map = {
        "PKD1": {
            "homozygous": {
                "has_kidney_phenotype": True,
                "phenotype_count": 1,
                "phenotypes": [{"term": "MP:0000519", "name": "hydroureter"}],
            },
            "heterozygous": {
                "has_kidney_phenotype": False,
                "phenotype_count": 0,
                "phenotypes": [],
            },
            "conditional": {
                "has_kidney_phenotype": False,
                "phenotype_count": 0,
                "phenotypes": [],
            },
            "summary": "hm (true); ht (false)",
        },
    }

    with patch.object(
        source, "_bulk_query_phenotypes", new_callable=AsyncMock, return_value=pheno_map
    ):
        with patch.object(
            source, "_bulk_query_zygosity", new_callable=AsyncMock, return_value=zyg_map
        ):
            results = await source.fetch_batch(genes)

    assert 1 in results  # PKD1
    assert 2 in results  # PKD2

    # PKD1 has kidney phenotype
    r1 = results[1]
    assert r1["has_kidney_phenotype"] is True
    assert r1["gene_symbol"] == "PKD1"
    assert r1["zygosity_analysis"]["summary"] == "hm (true); ht (false)"

    # PKD2 has no kidney phenotype
    r2 = results[2]
    assert r2["has_kidney_phenotype"] is False
    assert r2["gene_symbol"] == "PKD2"


@pytest.mark.unit
@pytest.mark.asyncio
async def test_fetch_batch_fallback_for_missing_genes(source):
    """fetch_batch falls back to per-gene queries for missing bulk results."""
    genes = [_make_gene(1, "PKD1"), _make_gene(2, "RARE_GENE")]

    # Bulk only returns PKD1
    pheno_map = {
        "PKD1": {
            "has_kidney_phenotype": True,
            "mouse_orthologs": ["Pkd1"],
            "phenotypes": [{"term": "MP:0000519", "name": "hydroureter"}],
            "phenotype_count": 1,
            "total_phenotypes": 5,
        },
        "RARE_GENE": {
            "has_kidney_phenotype": False,
            "mouse_orthologs": [],
            "phenotypes": [],
            "phenotype_count": 0,
            "total_phenotypes": 0,
        },
    }

    with patch.object(
        source, "_bulk_query_phenotypes", new_callable=AsyncMock, return_value=pheno_map
    ):
        with patch.object(
            source, "_bulk_query_zygosity", new_callable=AsyncMock, return_value={}
        ):
            results = await source.fetch_batch(genes)

    # Both genes should be in results
    assert 1 in results
    assert 2 in results


@pytest.mark.unit
@pytest.mark.asyncio
async def test_fetch_batch_empty_gene_list(source):
    """fetch_batch handles empty gene list gracefully."""
    with patch.object(
        source, "_bulk_query_phenotypes", new_callable=AsyncMock, return_value={}
    ):
        with patch.object(
            source, "_bulk_query_zygosity", new_callable=AsyncMock, return_value={}
        ):
            results = await source.fetch_batch([])

    assert results == {}


@pytest.mark.unit
@pytest.mark.asyncio
async def test_fetch_batch_loads_mpo_terms_once(source):
    """fetch_batch pre-loads MPO terms before bulk queries."""
    source._mpo_terms_cache = None  # Force reload

    mock_terms = {"MP:0000519", "MP:0000520"}

    with patch.object(
        source, "fetch_kidney_mpo_terms", new_callable=AsyncMock, return_value=mock_terms
    ) as mock_fetch:
        with patch.object(
            source, "_bulk_query_phenotypes", new_callable=AsyncMock, return_value={}
        ):
            with patch.object(
                source, "_bulk_query_zygosity", new_callable=AsyncMock, return_value={}
            ):
                await source.fetch_batch([_make_gene(1, "PKD1")])

    mock_fetch.assert_called_once()
    assert source._mpo_terms_cache == mock_terms


# ── BULK_CHUNK_SIZE constant ────────────────────────────────────────────


@pytest.mark.unit
def test_bulk_chunk_size_default():
    """Default BULK_CHUNK_SIZE is reasonable for URL length limits."""
    mock_session = Mock()
    src = MPOMGIAnnotationSource(mock_session)
    assert src.BULK_CHUNK_SIZE == 100


# ── Zygosity summary format ────────────────────────────────────────────


@pytest.mark.unit
@pytest.mark.asyncio
async def test_zygosity_summary_format(source):
    """Zygosity summary follows 'hm (true/false); ht (true/false)' format."""
    mock_rows = [
        ["MGI:1", "Pkd1", "C57BL/6J", "hm", "MP:0000519", "hydroureter"],
    ]

    mock_response = MagicMock()
    mock_response.status_code = 200
    mock_response.json.return_value = {"results": mock_rows}

    mock_client = AsyncMock()
    mock_client.get = AsyncMock(return_value=mock_response)

    with patch.object(source, "get_http_client", return_value=mock_client):
        with patch.object(source, "apply_rate_limit", new_callable=AsyncMock):
            result = await source._bulk_query_zygosity(
                {"PKD1": ["Pkd1"]}, source._mpo_terms_cache
            )

    assert result["PKD1"]["summary"] == "hm (true); ht (false)"


# ── Result structure parity with fetch_annotation ──────────────────────


@pytest.mark.unit
@pytest.mark.asyncio
async def test_batch_result_structure_matches_single(source):
    """Batch results contain same fields as single-gene fetch_annotation."""
    genes = [_make_gene(1, "PKD1")]

    pheno_map = {
        "PKD1": {
            "has_kidney_phenotype": True,
            "mouse_orthologs": ["Pkd1"],
            "phenotypes": [{"term": "MP:0000519", "name": "hydroureter"}],
            "phenotype_count": 1,
            "total_phenotypes": 5,
        },
    }

    zyg_map = {
        "PKD1": {
            "homozygous": {
                "has_kidney_phenotype": True,
                "phenotype_count": 1,
                "phenotypes": [{"term": "MP:0000519", "name": "hydroureter"}],
            },
            "heterozygous": {
                "has_kidney_phenotype": False,
                "phenotype_count": 0,
                "phenotypes": [],
            },
            "conditional": {
                "has_kidney_phenotype": False,
                "phenotype_count": 0,
                "phenotypes": [],
            },
            "summary": "hm (true); ht (false)",
        },
    }

    with patch.object(
        source, "_bulk_query_phenotypes", new_callable=AsyncMock, return_value=pheno_map
    ):
        with patch.object(
            source, "_bulk_query_zygosity", new_callable=AsyncMock, return_value=zyg_map
        ):
            results = await source.fetch_batch(genes)

    r = results[1]
    # Verify all expected fields present
    expected_fields = {
        "gene_symbol",
        "has_kidney_phenotype",
        "mouse_orthologs",
        "phenotypes",
        "phenotype_count",
        "mpo_terms_searched",
        "zygosity_analysis",
    }
    assert set(r.keys()) == expected_fields

    # Verify zygosity_analysis structure
    zyg = r["zygosity_analysis"]
    assert "homozygous" in zyg
    assert "heterozygous" in zyg
    assert "conditional" in zyg
    assert "summary" in zyg
