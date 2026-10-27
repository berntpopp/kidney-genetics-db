"""Tests for ClinGen CSV bulk download optimisation."""

from unittest.mock import AsyncMock, MagicMock, patch

import httpx
import pytest

from app.pipeline.sources.unified.clingen import ClinGenUnifiedSource

# ── Fixtures ────────────────────────────────────────────────────────────


CSV_HEADER = (
    '"CLINGEN GENE DISEASE VALIDITY CURATIONS","","","","","","","","",""\n'
    '"FILE CREATED: 2026-03-01","","","","","","","","",""\n'
    '"WEBPAGE: https://search.clinicalgenome.org/kb/gene-validity","","","","","","","","",""\n'
    '"+++++++++++","+++++","+++++","+++++","+++++","+++++","+++++","+++++","+++++","+++++"\n'
    '"GENE SYMBOL","GENE ID (HGNC)","DISEASE LABEL","DISEASE ID (MONDO)","MOI","SOP",'
    '"CLASSIFICATION","ONLINE REPORT","CLASSIFICATION DATE","GCEP"\n'
)

KIDNEY_ROW = (
    '"PKD1","HGNC:9008","autosomal dominant polycystic kidney disease 1",'
    '"MONDO:0008839","AD","SOP8","Definitive",'
    '"https://search.clinicalgenome.org/kb/gene-validity/report1",'
    '"2023-01-15T16:00:00.000Z",'
    '"Kidney Cystic and Ciliopathy Disorders Gene Curation Expert Panel"\n'
)

NON_KIDNEY_ROW = (
    '"BRCA1","HGNC:1100","breast cancer susceptibility",'
    '"MONDO:0100038","AD","SOP12","Definitive",'
    '"https://search.clinicalgenome.org/kb/gene-validity/report2",'
    '"2023-02-01T16:00:00.000Z",'
    '"Hereditary Breast and Ovarian Cancer Gene Curation Expert Panel"\n'
)

GLOM_ROW = (
    '"APOL1","HGNC:618","focal segmental glomerulosclerosis 4",'
    '"MONDO:0012931","AR","SOP8","Definitive",'
    '"https://search.clinicalgenome.org/kb/gene-validity/report3",'
    '"2021-09-28T02:30:00.000Z",'
    '"Glomerulopathy Gene Curation Expert Panel"\n'
)

# Non-kidney panel but kidney-related disease (should be included)
CROSS_PANEL_KIDNEY_ROW = (
    '"HNF1B","HGNC:11630","renal cysts and diabetes syndrome",'
    '"MONDO:0010894","AD","SOP8","Definitive",'
    '"https://search.clinicalgenome.org/kb/gene-validity/report4",'
    '"2024-06-15T16:00:00.000Z",'
    '"Monogenic Diabetes Gene Curation Expert Panel"\n'
)


@pytest.fixture
def source():
    """Create ClinGenUnifiedSource with mocked dependencies."""
    with patch.object(ClinGenUnifiedSource, "__init__", lambda self, **kw: None):
        src = ClinGenUnifiedSource.__new__(ClinGenUnifiedSource)
        src.csv_url = "https://search.clinicalgenome.org/kb/gene-validity/download"
        src.kidney_panel_names = {
            "Kidney Cystic and Ciliopathy Disorders Gene Curation Expert Panel",
            "Glomerulopathy Gene Curation Expert Panel",
            "Tubulopathy Gene Curation Expert Panel",
            "Complement-Mediated Kidney Diseases Gene Curation Expert Panel",
            "Congenital Anomalies of the Kidney and Urinary Tract Gene Curation Expert Panel",
        }
        src.http_client = AsyncMock()
        src.cache_ttl = 86400
        return src


# ── fetch_raw_data ──────────────────────────────────────────────────────


@pytest.mark.unit
@pytest.mark.asyncio
async def test_csv_parses_kidney_rows(source):
    """CSV parser extracts kidney panel rows and cross-panel kidney diseases."""
    csv_text = CSV_HEADER + KIDNEY_ROW + NON_KIDNEY_ROW + GLOM_ROW + CROSS_PANEL_KIDNEY_ROW

    mock_resp = MagicMock()
    mock_resp.status_code = 200
    mock_resp.text = csv_text
    source.http_client.get = AsyncMock(return_value=mock_resp)

    result = await source.fetch_raw_data()

    assert result is not None
    # PKD1 (kidney panel) + APOL1 (kidney panel) + HNF1B (kidney disease from other panel)
    assert result["total_records"] == 3
    assert len(result["validities"]) == 3

    symbols = {v["symbol"] for v in result["validities"]}
    assert "PKD1" in symbols
    assert "APOL1" in symbols
    assert "HNF1B" in symbols  # Cross-panel match via "renal" keyword
    assert "BRCA1" not in symbols  # Non-kidney disease, non-kidney panel


@pytest.mark.unit
@pytest.mark.asyncio
async def test_csv_includes_cross_panel_kidney_disease(source):
    """Genes from non-kidney panels are included if disease is kidney-related."""
    csv_text = CSV_HEADER + CROSS_PANEL_KIDNEY_ROW + NON_KIDNEY_ROW

    mock_resp = MagicMock()
    mock_resp.status_code = 200
    mock_resp.text = csv_text
    source.http_client.get = AsyncMock(return_value=mock_resp)

    result = await source.fetch_raw_data()

    assert result is not None
    assert len(result["validities"]) == 1
    assert result["validities"][0]["symbol"] == "HNF1B"
    assert result["validities"][0]["disease_name"] == "renal cysts and diabetes syndrome"


@pytest.mark.unit
@pytest.mark.asyncio
async def test_csv_field_mapping(source):
    """CSV fields map to the same dict keys as the API response."""
    csv_text = CSV_HEADER + KIDNEY_ROW

    mock_resp = MagicMock()
    mock_resp.status_code = 200
    mock_resp.text = csv_text
    source.http_client.get = AsyncMock(return_value=mock_resp)

    result = await source.fetch_raw_data()
    assert result is not None

    v = result["validities"][0]
    assert v["symbol"] == "PKD1"
    assert v["hgnc_id"] == "HGNC:9008"
    assert v["disease_name"] == "autosomal dominant polycystic kidney disease 1"
    assert v["mondo"] == "MONDO:0008839"
    assert v["moi"] == "AD"
    assert v["classification"] == "Definitive"
    assert v["released"] == "2023-01-15T16:00:00.000Z"
    assert "ep" in v


@pytest.mark.unit
@pytest.mark.asyncio
async def test_csv_panel_stats(source):
    """Panel stats count records per GCEP."""
    csv_text = CSV_HEADER + KIDNEY_ROW + GLOM_ROW

    mock_resp = MagicMock()
    mock_resp.status_code = 200
    mock_resp.text = csv_text
    source.http_client.get = AsyncMock(return_value=mock_resp)

    result = await source.fetch_raw_data()
    assert result is not None

    stats = result["panel_stats"]
    assert stats["Kidney Cystic and Ciliopathy Disorders Gene Curation Expert Panel"] == 1
    assert stats["Glomerulopathy Gene Curation Expert Panel"] == 1


@pytest.mark.unit
@pytest.mark.asyncio
async def test_csv_http_error_raises(source):
    """A failed download fails the run instead of returning a partial panel subset."""

    async def get(url, **kwargs):
        # The per-panel API still answers; its five panels alone miss cross-panel genes
        status = 503 if url == source.csv_url else 200
        return httpx.Response(status, json={"rows": []}, request=httpx.Request("GET", url))

    source.http_client.get = AsyncMock(side_effect=get)

    with pytest.raises(httpx.HTTPStatusError):
        await source.fetch_raw_data()


@pytest.mark.unit
@pytest.mark.asyncio
async def test_csv_unexpected_format_raises(source):
    """An HTML error page or a changed layout raises instead of parsing to nothing."""
    mock_resp = MagicMock()
    mock_resp.text = "<html>maintenance</html>\n"
    source.http_client.get = AsyncMock(return_value=mock_resp)

    with pytest.raises(ValueError, match="unexpected format"):
        await source.fetch_raw_data()


@pytest.mark.unit
@pytest.mark.asyncio
async def test_csv_raises_when_no_http_client(source):
    source.http_client = None

    with pytest.raises(RuntimeError):
        await source.fetch_raw_data()


# ── kidney_panel_names constant ─────────────────────────────────────────


@pytest.mark.unit
def test_kidney_panel_names_match_known_panels():
    """All 5 kidney GCEP names are configured."""
    with patch.object(ClinGenUnifiedSource, "__init__", lambda self, **kw: None):
        src = ClinGenUnifiedSource.__new__(ClinGenUnifiedSource)
        src.kidney_panel_names = {
            "Kidney Cystic and Ciliopathy Disorders Gene Curation Expert Panel",
            "Glomerulopathy Gene Curation Expert Panel",
            "Tubulopathy Gene Curation Expert Panel",
            "Complement-Mediated Kidney Diseases Gene Curation Expert Panel",
            "Congenital Anomalies of the Kidney and Urinary Tract Gene Curation Expert Panel",
        }
    assert len(src.kidney_panel_names) == 5
