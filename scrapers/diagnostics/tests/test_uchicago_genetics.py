"""UChicago Genetic Services parser against captured HTML (no live provider/HGNC calls)."""

import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import utils  # noqa: E402
from providers.uchicago_genetics import UChicagoGeneticsScraper  # noqa: E402

FIXTURES = Path(__file__).parent / "fixtures" / "uchicago_genetics"
CATEGORY_URL = "https://dnatesting.uchicago.edu/category/nephrology"
CAKUT_URL = "https://dnatesting.uchicago.edu/tests/congenital-anomalies-kidney-and-urinary-tract-cakut-panel"
CYSTIC_URL = (
    "https://dnatesting.uchicago.edu/tests/hereditary-cystic-and-glomerular-disorders-panel-0"
)
CAKUT = "Congenital Anomalies of Kidney and Urinary Tract (CAKUT) Panel"
CYSTIC = "Hereditary Cystic and Glomerular Disorders Panel"


class FakeHGNC:
    """FAM58A is a previous symbol of CCNQ; UMOD is forced unresolved to cover that path."""

    def normalize_batch(self, symbols):
        known = {"ACE": "HGNC:2707", "HNF1B": "HGNC:11630", "PAX2": "HGNC:8616"}
        out = {s: {"found": True, "approved_symbol": s, "hgnc_id": h} for s, h in known.items()}
        out["FAM58A"] = {"found": True, "approved_symbol": "CCNQ", "hgnc_id": "HGNC:28434"}
        out["UMOD"] = {"found": False}
        return {s: out[s] for s in symbols}

    def get_stats(self):
        return {"api_calls": 0, "cache_hits": 0, "cache_misses": 0}


@pytest.fixture
def scraper(monkeypatch, tmp_path):
    monkeypatch.chdir(tmp_path)  # data/ and output/ are relative
    monkeypatch.setattr(utils, "_normalizer", FakeHGNC())
    config = {"scrapers": {"uchicago_genetics": {"url": CATEGORY_URL, "rate_limit": 0}}}
    return UChicagoGeneticsScraper(config)


def serve(monkeypatch, scraper, pages):
    monkeypatch.setattr(scraper, "fetch_content", lambda url: pages[url])


def read(name):
    return (FIXTURES / name).read_text(encoding="utf-8")


def test_extract_panel_links(scraper):
    assert scraper.extract_panel_links(read("nephrology_category.html")) == [
        {"name": CAKUT, "url": CAKUT_URL},
        {"name": CYSTIC, "url": CYSTIC_URL},
    ]


def test_extract_genes(scraper):
    assert scraper.extract_genes_from_panel(read("cakut_panel.html")) == [
        "ACE",
        "FAM58A",
        "HNF1B",
        "PAX2",
        "UMOD",
    ]


def test_run_keeps_provenance_and_unresolved(monkeypatch, scraper):
    serve(
        monkeypatch,
        scraper,
        {
            CATEGORY_URL: read("nephrology_category.html"),
            CAKUT_URL: read("cakut_panel.html"),
            CYSTIC_URL: "<html><body><h1>Maintenance</h1></body></html>",
        },
    )
    result = scraper.run()

    assert result.provider_id == "uchicago_genetics"
    assert result.main_url == CATEGORY_URL
    assert [(p.name, p.url, p.gene_count) for p in result.sub_panels] == [(CAKUT, CAKUT_URL, 5)]
    assert result.errors == [f"{CYSTIC}: no genes found"]
    genes = {g.reported_as: g for g in result.genes}
    assert all(g.panels == [CAKUT] for g in genes.values())
    assert (genes["FAM58A"].symbol, genes["FAM58A"].hgnc_id) == ("CCNQ", "HGNC:28434")
    umod = genes["UMOD"]
    assert (umod.symbol, umod.hgnc_id, umod.normalization_status) == ("UMOD", None, "not_found")
    assert result.total_unique_genes == 5
    assert list(Path("output").glob("*/uchicago_genetics.json"))


@pytest.mark.parametrize("category", ["", "<html><body>No tests listed</body></html>"])
def test_run_empty_category_is_an_error(monkeypatch, scraper, category):
    serve(monkeypatch, scraper, {CATEGORY_URL: category})
    result = scraper.run()
    assert result.genes == [] and result.sub_panels == []
    assert result.errors == ["category page: no panel links found"]


def test_run_fetch_failure_is_an_error(monkeypatch, scraper):
    def boom(url):
        raise OSError("HTTP 503")

    monkeypatch.setattr(scraper, "fetch_content", boom)
    result = scraper.run()
    assert result.genes == [] and result.errors == ["category page: HTTP 503"]
