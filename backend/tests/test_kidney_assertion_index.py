"""Ontology-based kidney filter for GenCC and ClinGen assertions (#438)."""

from unittest.mock import AsyncMock, patch

import pandas as pd
import pytest

from app.pipeline.sources.unified import kidney_assertions
from app.pipeline.sources.unified.clingen import ClinGenUnifiedSource
from app.pipeline.sources.unified.gencc import GenCCUnifiedSource
from app.pipeline.sources.unified.kidney_assertions import KidneyAssertionIndex

# HP:0000077 kidney > HP:0000787 nephrolithiasis; HP:0001250 seizure is outside the root
PARENTS = {
    "HP:0000787": {"HP:0000077"},
    "HP:0000077": {"HP:0000079"},
    "HP:0001250": {"HP:0000707"},
}
G2P = (
    "ncbi_gene_id\tgene_symbol\thpo_id\thpo_name\tfrequency\tdisease_id\n"
    "189\tAGXT\tHP:0000787\tNephrolithiasis\t-\tOMIM:259900\n"
    "6559\tSLC12A3\tHP:0000077\tAbnormality of the kidney\t-\tORPHA:358\n"
    "1\tSCN1A\tHP:0001250\tSeizure\t-\tOMIM:607208\n"
    "2\tNOPANEL\tHP:0000787\tNephrolithiasis\t-\tOMIM:999999\n"
    "3\tEXCL\tHP:0000787\tNephrolithiasis\tHP:0040285\tOMIM:888888\n"
)
SSSOM = {
    "OMIM:259900": {"MONDO:0009823"},
    "Orphanet:358": {"MONDO:0009288"},
    "OMIM:111111": {"MONDO:0000001", "MONDO:0000002"},  # ambiguous
    "OMIM:222222": {"MONDO:0000003"},  # obsolete
}
LABELS = {"MONDO:0000003": "obsolete thing"}
PANEL_GENES = {"AGXT", "SLC12A3", "SCN1A", "EXCL"}


@pytest.fixture
def index(tmp_path):
    g2p = tmp_path / "g2p.txt"
    g2p.write_text(G2P)
    return KidneyAssertionIndex.build(PARENTS, g2p, SSSOM, LABELS, PANEL_GENES, "HP:0000077")


@pytest.mark.unit
class TestIndex:
    def test_hpo_disease_id_and_panel_gene_match(self, index):
        assert index.matches("AGXT", ["OMIM:259900"])

    def test_mondo_resolves_via_sssom(self, index):
        assert index.matches("AGXT", ["MONDO:0009823"])

    def test_orpha_prefix_is_normalised(self, index):
        assert index.matches("SLC12A3", ["MONDO:0009288"])
        assert index.matches("slc12a3", ["ORPHA:358"])

    def test_non_kidney_term_rejected(self, index):
        assert not index.matches("SCN1A", ["OMIM:607208"])

    def test_kidney_term_without_panel_gene_rejected(self, index):
        assert not index.matches("NOPANEL", ["OMIM:999999"])

    def test_excluded_frequency_ignored(self, index):
        assert not index.matches("EXCL", ["OMIM:888888"])

    def test_wrong_gene_for_disease_rejected(self, index):
        assert not index.matches("SLC12A3", ["OMIM:259900"])

    def test_ambiguous_and_obsolete_mappings_ignored(self, index):
        assert not index.mondo_xrefs.get("MONDO:0000001")
        assert not index.mondo_xrefs.get("MONDO:0000003")

    def test_blank_ids_ignored(self, index):
        assert not index.matches("AGXT", [None, "", "  "])


@pytest.mark.unit
@pytest.mark.asyncio
async def test_loader_falls_back_to_none_on_failure():
    with patch.object(kidney_assertions, "_pinned_file", AsyncMock(side_effect=ValueError("x"))):
        assert await kidney_assertions.load_kidney_assertion_index(object()) is None


@pytest.mark.unit
@pytest.mark.asyncio
async def test_loader_without_session_returns_none():
    assert await kidney_assertions.load_kidney_assertion_index(None) is None


GENCC_ROWS = [
    {  # primary hyperoxaluria: no kidney keyword, kept via hpo_panel
        "gene_symbol": "AGXT",
        "disease_title": "primary hyperoxaluria type 1",
        "disease_curie": "MONDO:0009823",
        "disease_original_curie": "OMIM:259900",
        "classification_title": "Definitive",
    },
    {
        "gene_symbol": "PKD1",
        "disease_title": "polycystic kidney disease",
        "disease_curie": "MONDO:0004691",
        "classification_title": "Definitive",
    },
    {
        "gene_symbol": "SCN1A",
        "disease_title": "Dravet syndrome",
        "disease_curie": "MONDO:0100135",
        "classification_title": "Definitive",
    },
]


def _gencc(index):
    source = GenCCUnifiedSource.__new__(GenCCUnifiedSource)
    source.kidney_keywords = ["kidney", "polycystic"]
    source.classification_weights = {"Definitive": 1.0}
    source.db_session = object()
    loader = AsyncMock(return_value=index)
    return source, loader


@pytest.mark.unit
@pytest.mark.asyncio
async def test_gencc_keeps_agxt_via_hpo_panel(index):
    source, loader = _gencc(index)
    with patch("app.pipeline.sources.unified.gencc.load_kidney_assertion_index", loader):
        result = await source.process_data(pd.DataFrame(GENCC_ROWS))

    assert set(result) == {"AGXT", "PKD1"}
    assert result["AGXT"]["submissions"][0]["kidney_match"] == "hpo_panel"
    assert result["PKD1"]["submissions"][0]["kidney_match"] == "keyword"
    assert result["AGXT"]["kidney_filter"] == "ontology"


@pytest.mark.unit
@pytest.mark.asyncio
async def test_gencc_falls_back_to_keyword_only():
    source, loader = _gencc(None)
    with patch("app.pipeline.sources.unified.gencc.load_kidney_assertion_index", loader):
        result = await source.process_data(pd.DataFrame(GENCC_ROWS))

    assert set(result) == {"PKD1"}
    assert result["PKD1"]["kidney_filter"] == "keyword_only"


CLINGEN_CSV = (
    '"","","","","","","","","",""\n'
    * 4
    + '"GENE SYMBOL","GENE ID (HGNC)","DISEASE LABEL","DISEASE ID (MONDO)","MOI","SOP",'
    '"CLASSIFICATION","ONLINE REPORT","CLASSIFICATION DATE","GCEP"\n'
    '"AGXT","HGNC:341","primary hyperoxaluria type 1","MONDO:0009823","AR","SOP10",'
    '"Definitive","https://example.org/r1","2024-01-01","Inborn Errors of Metabolism GCEP"\n'
    '"SCN1A","HGNC:10585","Dravet syndrome","MONDO:0100135","AD","SOP10",'
    '"Definitive","https://example.org/r2","2024-01-01","Epilepsy GCEP"\n'
    '"PKD1","HGNC:9008","polycystic kidney disease","MONDO:0004691","AD","SOP10",'
    '"Definitive","https://example.org/r3","2024-01-01","Kidney Cystic and Ciliopathy '
    'Disorders Gene Curation Expert Panel"\n'
)


@pytest.mark.unit
@pytest.mark.asyncio
@pytest.mark.parametrize("with_index", [True, False])
async def test_clingen_keeps_agxt_via_hpo_panel(index, with_index):
    source = ClinGenUnifiedSource.__new__(ClinGenUnifiedSource)
    source.csv_url = "https://example.org/csv"
    source.kidney_panel_names = {
        "Kidney Cystic and Ciliopathy Disorders Gene Curation Expert Panel"
    }
    source.classification_weights = {"Definitive": 1.0}
    source.db_session = object()
    source.http_client = AsyncMock()
    response = AsyncMock()
    response.text = CLINGEN_CSV
    response.raise_for_status = lambda: None
    source.http_client.get = AsyncMock(return_value=response)
    loader = AsyncMock(return_value=index if with_index else None)

    with patch("app.pipeline.sources.unified.clingen.load_kidney_assertion_index", loader):
        result = await source.process_data(await source.fetch_raw_data())

    if with_index:
        assert set(result) == {"AGXT", "PKD1"}
        assert result["AGXT"]["validities"][0]["kidney_match"] == "hpo_panel"
        assert result["AGXT"]["kidney_filter"] == "ontology"
    else:
        assert set(result) == {"PKD1"}
        assert result["PKD1"]["kidney_filter"] == "keyword_only"
    assert result["PKD1"]["validities"][0]["kidney_match"] in {"keyword", "expert_panel"}
