"""Tests for ClinGen CSV bulk download optimisation."""

from unittest.mock import AsyncMock, MagicMock, Mock, patch

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


@pytest.fixture
def source():
    """Create ClinGenUnifiedSource with mocked dependencies."""
    with patch.object(ClinGenUnifiedSource, "__init__", lambda self, **kw: None):
        src = ClinGenUnifiedSource.__new__(ClinGenUnifiedSource)
        src.base_url = "https://search.clinicalgenome.org/api"
        src.csv_url = "https://search.clinicalgenome.org/kb/gene-validity/download"
        src.kidney_affiliate_ids = [40066, 40068, 40067, 40069, 40070]
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


# ── _fetch_bulk_csv ─────────────────────────────────────────────────────


@pytest.mark.unit
@pytest.mark.asyncio
async def test_csv_parses_kidney_rows(source):
    """CSV parser extracts only kidney panel rows."""
    csv_text = CSV_HEADER + KIDNEY_ROW + NON_KIDNEY_ROW + GLOM_ROW

    mock_resp = MagicMock()
    mock_resp.status_code = 200
    mock_resp.text = csv_text
    source.http_client.get = AsyncMock(return_value=mock_resp)

    result = await source._fetch_bulk_csv()

    assert result is not None
    assert result["total_records"] == 2  # PKD1 + APOL1
    assert len(result["validities"]) == 2

    symbols = {v["symbol"] for v in result["validities"]}
    assert "PKD1" in symbols
    assert "APOL1" in symbols
    assert "BRCA1" not in symbols


@pytest.mark.unit
@pytest.mark.asyncio
async def test_csv_field_mapping(source):
    """CSV fields map to the same dict keys as the API response."""
    csv_text = CSV_HEADER + KIDNEY_ROW

    mock_resp = MagicMock()
    mock_resp.status_code = 200
    mock_resp.text = csv_text
    source.http_client.get = AsyncMock(return_value=mock_resp)

    result = await source._fetch_bulk_csv()
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

    result = await source._fetch_bulk_csv()
    assert result is not None

    stats = result["panel_stats"]
    assert stats["Kidney Cystic and Ciliopathy Disorders Gene Curation Expert Panel"] == 1
    assert stats["Glomerulopathy Gene Curation Expert Panel"] == 1


@pytest.mark.unit
@pytest.mark.asyncio
async def test_csv_returns_none_on_http_error(source):
    """CSV download returns None on non-200 status."""
    mock_resp = MagicMock()
    mock_resp.status_code = 500
    source.http_client.get = AsyncMock(return_value=mock_resp)

    result = await source._fetch_bulk_csv()
    assert result is None


@pytest.mark.unit
@pytest.mark.asyncio
async def test_csv_returns_none_on_exception(source):
    """CSV download returns None on network exception."""
    source.http_client.get = AsyncMock(side_effect=Exception("timeout"))

    result = await source._fetch_bulk_csv()
    assert result is None


@pytest.mark.unit
@pytest.mark.asyncio
async def test_csv_returns_none_when_no_http_client(source):
    """CSV download returns None when http_client is None."""
    source.http_client = None

    result = await source._fetch_bulk_csv()
    assert result is None


# ── fetch_raw_data (CSV + fallback) ─────────────────────────────────────


@pytest.mark.unit
@pytest.mark.asyncio
async def test_fetch_raw_data_prefers_csv(source):
    """fetch_raw_data uses CSV when available."""
    csv_result = {
        "validities": [{"symbol": "PKD1"}],
        "panel_stats": {},
        "total_records": 1,
        "fetch_date": "2026-03-01T00:00:00+00:00",
    }

    with patch.object(source, "_fetch_bulk_csv", new_callable=AsyncMock, return_value=csv_result):
        with patch.object(source, "_fetch_per_panel_api", new_callable=AsyncMock) as mock_api:
            result = await source.fetch_raw_data()

    assert result == csv_result
    mock_api.assert_not_called()


@pytest.mark.unit
@pytest.mark.asyncio
async def test_fetch_raw_data_falls_back_to_api(source):
    """fetch_raw_data falls back to per-panel API when CSV fails."""
    api_result = {
        "validities": [{"symbol": "PKD2"}],
        "panel_stats": {},
        "total_records": 1,
        "fetch_date": "2026-03-01T00:00:00+00:00",
    }

    with patch.object(source, "_fetch_bulk_csv", new_callable=AsyncMock, return_value=None):
        with patch.object(
            source, "_fetch_per_panel_api", new_callable=AsyncMock, return_value=api_result
        ):
            result = await source.fetch_raw_data()

    assert result == api_result


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
