"""normalize_genes writes the output status (mocked HTTP; needs pyyaml)."""

import io
import json
import logging
import sys
import urllib.error
from pathlib import Path
from types import SimpleNamespace

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import utils  # noqa: E402
from base_scraper import BaseDiagnosticScraper  # noqa: E402
from schemas import GeneEntry  # noqa: E402


def test_normalize_genes_writes_outage_and_ambiguous_status(monkeypatch, tmp_path):
    monkeypatch.chdir(tmp_path)  # CACHE_DIR is relative
    monkeypatch.setattr(utils, "_normalizer", None)

    def fake_urlopen(req, timeout=None):
        if "/PKD1" in req.full_url:
            raise urllib.error.URLError("down")
        docs = [{"hgnc_id": "HGNC:1"}, {"hgnc_id": "HGNC:2"}] if "alias" in req.full_url else []
        return io.BytesIO(json.dumps({"response": {"numFound": len(docs), "docs": docs}}).encode())

    monkeypatch.setattr(utils.urllib.request, "urlopen", fake_urlopen)
    genes = [GeneEntry(symbol="PKD1", panels=["p"]), GeneEntry(symbol="OLD1", panels=["p"])]
    fake_self = SimpleNamespace(logger=logging.getLogger("test"))
    out = BaseDiagnosticScraper.normalize_genes(fake_self, genes)
    assert [(g.symbol, g.hgnc_id, g.normalization_status) for g in out] == [
        ("PKD1", None, "hgnc_unavailable"),
        ("OLD1", None, "ambiguous"),
    ]
