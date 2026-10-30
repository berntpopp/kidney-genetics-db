"""Parsers fixed in the 2026-10 rescrape, against captured HTML (no live provider/HGNC calls)."""

import io
import json
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import utils  # noqa: E402
from providers import natera as natera_module  # noqa: E402
from providers.cegat import CegatScraper  # noqa: E402
from providers.mgz_muenchen import MGZMuenchenScraper  # noqa: E402
from providers.mvz_medicover import MVZMedicoverScraper  # noqa: E402
from providers.natera import NateraScraper  # noqa: E402
from providers.prevention_genetics import PreventionGeneticsScraper  # noqa: E402

FIXTURES = Path(__file__).parent / "fixtures"
MGZ_URL = "https://www.mgz-muenchen.de/leistungsspektrum/"
MGZ_API = "https://www.mgz-muenchen.de/wp-json/mgz/v1/product-genes/"
ALPORT = "Alport-Syndrom/Hämaturie I Panel"
ALPORT_URL = "https://www.mgz-muenchen.de/leistungsspektrum/alport-syndrom-haematurie-i-panel/"
PG_NAME = "PGmax™ - Comprehensive Inherited Kidney Diseases Panel"
PG_URL = (
    "https://www.preventiongenetics.com/tests/pgmax-comprehensive-inherited-kidney-diseases-panel"
)


class FakeHGNC:
    def normalize_batch(self, symbols):
        return {s: {"found": True, "approved_symbol": s, "hgnc_id": f"HGNC:{s}"} for s in symbols}

    def get_stats(self):
        return {"api_calls": 0, "cache_hits": 0, "cache_misses": 0}


@pytest.fixture(autouse=True)
def offline(monkeypatch, tmp_path):
    monkeypatch.chdir(tmp_path)  # data/ and output/ are relative
    monkeypatch.setattr(utils, "_normalizer", FakeHGNC())


def read(path):
    return (FIXTURES / path).read_text(encoding="utf-8")


def make(cls, provider_id, **cfg):
    return cls({"rate_limit": 0, "scrapers": {provider_id: cfg}})


def test_cegat_reads_only_the_gene_directory_list(monkeypatch):
    scraper = make(CegatScraper, "cegat", url="https://cegat.com/kidney")
    page = read("cegat/kidney_diseases.html")
    # Page words from the free text (ACMG, ENDE, EN, CAP, II) and the HLA list are not genes.
    assert scraper.extract_genes(page) == ["ACE", "COL4A5", "DNAJB11", "PKD1", "PKD2"]
    assert scraper.extract_genes("<p>ACMG guidelines, CAP, EN ISO</p>") == []

    monkeypatch.setattr(scraper, "fetch_content", lambda url: page)
    result = scraper.run()
    assert result.total_unique_genes == 5 and result.errors is None
    assert [(p.name, p.url, p.gene_count) for p in result.sub_panels] == [
        ("Kidney Disease Panel", "https://cegat.com/kidney", 5)
    ]


def test_mgz_lists_area_tests_and_reads_gene_endpoint(monkeypatch):
    scraper = make(
        MGZMuenchenScraper, "mgz_muenchen", url=MGZ_URL, area="nephrologie-und-elektrolytstoerungen"
    )
    pages = {
        MGZ_URL: read("mgz_muenchen/leistungsspektrum.html"),
        MGZ_API + "alport-syndrom-haematurie-i-panel": json.dumps(
            {"genes": ["COL4A3", "COL4A5", "IV"], "total": 3}
        ),
        MGZ_API + "adrenogenitales-syndrom-cyp21a2": json.dumps({"genes": [], "total": 0}),
    }
    monkeypatch.setattr(scraper, "fetch_content", lambda url: pages[url])
    result = scraper.run()

    assert result.main_url == MGZ_URL and result.provider_type == "multi_panel"
    assert [(p.name, p.url, p.gene_count) for p in result.sub_panels] == [(ALPORT, ALPORT_URL, 3)]
    assert result.errors == ["Adrenogenitales Syndrom | CYP21A2: no genes found"]
    assert {g.reported_as for g in result.genes} == {"COL4A3", "COL4A5", "IV"}
    assert all(g.panels == [ALPORT] for g in result.genes)


def test_mgz_missing_area_is_an_error(monkeypatch):
    scraper = make(MGZMuenchenScraper, "mgz_muenchen", url=MGZ_URL, area="nephrologie")
    monkeypatch.setattr(scraper, "fetch_content", lambda url: "<html></html>")
    assert scraper.run().errors == ["no panels found in the configured area"]


def test_natera_posts_the_nonce_from_the_page(monkeypatch):
    scraper = make(
        NateraScraper, "natera", url="https://natera.test/list", api_url="https://natera.test/ajax"
    )
    monkeypatch.setattr(
        scraper, "fetch_content", lambda url: read("natera/gene_conditions_list.html")
    )
    monkeypatch.setattr(natera_module.time, "sleep", lambda s: None)
    posted = []

    def fake_urlopen(req, timeout=None):
        form = dict(p.split("=") for p in req.data.decode().split("&"))
        posted.append(form)
        body = read("natera/api_page_1.html") if form["page"] == "1" else "0"
        return io.BytesIO(body.encode())

    monkeypatch.setattr(natera_module.urllib.request, "urlopen", fake_urlopen)
    assert sorted(scraper.fetch_all_genes_via_api()) == ["ABCC6", "PKD1"]
    assert [f["nonce"] for f in posted] == ["8f7ac73ec3", "8f7ac73ec3"]


def test_natera_missing_nonce_is_an_error(monkeypatch):
    scraper = make(NateraScraper, "natera", url="https://natera.test/list", api_url="x")
    monkeypatch.setattr(scraper, "fetch_content", lambda url: "<html></html>")
    assert "nonce not found" in scraper.run().errors[0]


def test_mvz_skips_panel_codes_and_disease_slugs():
    scraper = make(MVZMedicoverScraper, "mvz_medicover", url="https://mvz.test")
    assert scraper.use_browser is False
    assert scraper.extract_genes(read("mvz_medicover/nierenerkrankungen.html")) == ["CD2AP", "PKD1"]


def test_prevention_genetics_picks_the_named_test(monkeypatch):
    scraper = make(
        PreventionGeneticsScraper, "prevention_genetics", url=PG_URL, display_name=PG_NAME
    )
    page = read("prevention_genetics/pgmax_kidney.html")
    assert scraper.extract_genes(page) == ["ACE", "PKHD1"]

    monkeypatch.setattr(scraper, "fetch_content", lambda url: page)
    result = scraper.run()
    assert result.errors is None
    assert [(p.name, p.url, p.gene_count) for p in result.sub_panels] == [
        ("Comprehensive Kidney Disease Panel", PG_URL, 2)
    ]
    assert result.scraped_at.endswith("+00:00")


def test_prevention_genetics_renamed_test_is_an_error(monkeypatch):
    scraper = make(PreventionGeneticsScraper, "prevention_genetics", url=PG_URL, display_name="X")
    monkeypatch.setattr(
        scraper, "fetch_content", lambda url: read("prevention_genetics/pgmax_kidney.html")
    )
    result = scraper.run()
    assert result.genes == [] and result.errors == ["no geneList found for test 'X'"]
