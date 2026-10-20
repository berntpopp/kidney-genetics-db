"""HGNC normalizer behavior with mocked HTTP (no live HGNC calls)."""

import io
import json
import sys
import urllib.error
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import utils  # noqa: E402


def empty():
    return {"response": {"numFound": 0, "docs": []}}


def hits(*docs):
    return {"response": {"numFound": len(docs), "docs": list(docs)}}


@pytest.fixture
def hgnc(monkeypatch, tmp_path):
    """Route HGNC requests to `routes` ({endpoint: payload | Exception}); log calls."""
    monkeypatch.chdir(tmp_path)  # CACHE_DIR is relative
    routes, calls = {}, []

    def fake_urlopen(req, timeout=None):
        endpoint = req.full_url.split("/search/")[1].split("/")[0]
        calls.append(endpoint)
        payload = routes.get(endpoint, empty())
        if isinstance(payload, Exception):
            raise payload
        return io.BytesIO(json.dumps(payload).encode())

    monkeypatch.setattr(utils.urllib.request, "urlopen", fake_urlopen)
    return routes, calls


def test_outage_is_not_cached_and_recovery_resolves(hgnc):
    routes, calls = hgnc
    for endpoint in ("symbol", "prev_symbol", "alias_symbol"):
        routes[endpoint] = urllib.error.URLError("down")

    first = utils.HGNCNormalizer()
    assert first.normalize_symbol("PKD1")["found"] is False
    routes["symbol"] = hits({"hgnc_id": "HGNC:9008", "symbol": "PKD1"})
    # Same process must retry too (no session negative cache).
    assert first.normalize_symbol("PKD1")["hgnc_id"] == "HGNC:9008"

    # And a fresh normalizer reuses the real (disk-cached) success.
    calls.clear()
    assert utils.HGNCNormalizer().normalize_symbol("PKD1")["found"] is True
    assert calls == []


def test_partial_outage_does_not_fall_through_to_alias(hgnc):
    routes, _ = hgnc
    routes["symbol"] = urllib.error.URLError("down")
    routes["alias_symbol"] = hits({"hgnc_id": "HGNC:1", "symbol": "OTHER"})
    assert utils.HGNCNormalizer().normalize_symbol("PKD1")["found"] is False


def test_successful_empty_response_is_cached_as_not_found(hgnc):
    _, calls = hgnc
    assert utils.HGNCNormalizer().normalize_symbol("NOTAGENE")["found"] is False
    calls.clear()
    assert utils.HGNCNormalizer().normalize_symbol("NOTAGENE")["found"] is False
    assert calls == []


def test_legacy_unversioned_cache_entry_is_re_resolved(hgnc):
    routes, calls = hgnc
    normalizer = utils.HGNCNormalizer()
    legacy = {
        "symbol": "PKD1",
        "data": {"hgnc_id": None, "approved_symbol": "PKD1", "found": False},
        "cached_at": "2999-01-01T00:00:00",
    }
    normalizer._get_cache_path("PKD1").write_text(json.dumps(legacy))
    routes["symbol"] = hits({"hgnc_id": "HGNC:9008", "symbol": "PKD1"})
    assert normalizer.normalize_symbol("PKD1")["hgnc_id"] == "HGNC:9008"
    assert calls == ["symbol"]


@pytest.mark.parametrize("endpoint", ["prev_symbol", "alias_symbol"])
@pytest.mark.parametrize("reverse", [False, True])
def test_ambiguous_match_is_not_normalized_in_any_order(hgnc, endpoint, reverse):
    routes, _ = hgnc
    docs = [
        {"hgnc_id": "HGNC:1", "symbol": "AAA"},
        {"hgnc_id": "HGNC:2", "symbol": "BBB"},
    ]
    routes[endpoint] = hits(*(docs[::-1] if reverse else docs))
    result = utils.HGNCNormalizer().normalize_symbol("OLD1")
    assert result["found"] is False
    assert result["hgnc_id"] is None
    assert result["approved_symbol"] == "OLD1"
    assert result["ambiguous"] is True
    assert result["candidates"] == ["HGNC:1", "HGNC:2"]


def test_numfound_above_returned_docs_is_ambiguous(hgnc):
    routes, _ = hgnc
    routes["alias_symbol"] = {
        "response": {"numFound": 2, "docs": [{"hgnc_id": "HGNC:1", "symbol": "AAA"}]}
    }
    assert utils.HGNCNormalizer().normalize_symbol("OLD1")["found"] is False


def test_unique_alias_match_is_normalized(hgnc):
    routes, _ = hgnc
    routes["alias_symbol"] = hits({"hgnc_id": "HGNC:1", "symbol": "AAA"})
    result = utils.HGNCNormalizer().normalize_symbol("OLD1")
    assert (result["found"], result["hgnc_id"], result.get("was_alias")) == (
        True,
        "HGNC:1",
        True,
    )


def test_v2_cached_alias_pick_is_re_resolved(hgnc):
    routes, _ = hgnc
    normalizer = utils.HGNCNormalizer()
    stale = {
        "symbol": "OLD1",
        "version": 2,
        "data": {
            "hgnc_id": "HGNC:1",
            "approved_symbol": "AAA",
            "found": True,
            "was_alias": True,
        },
        "cached_at": "2999-01-01T00:00:00",
    }
    normalizer._get_cache_path("OLD1").write_text(json.dumps(stale))
    routes["alias_symbol"] = hits({"hgnc_id": "HGNC:1"}, {"hgnc_id": "HGNC:2"})
    assert normalizer.normalize_symbol("OLD1")["found"] is False


def test_null_response_body_is_unavailable_and_not_cached(hgnc):
    routes, calls = hgnc
    routes["symbol"] = {"response": None}
    result = utils.HGNCNormalizer().normalize_symbol("PKD1")
    assert result["hgnc_unavailable"] is True
    routes["symbol"] = hits({"hgnc_id": "HGNC:9008", "symbol": "PKD1"})
    assert utils.HGNCNormalizer().normalize_symbol("PKD1")["found"] is True


def test_output_status_for_outage_and_ambiguous(hgnc):
    routes, _ = hgnc
    routes["symbol"] = urllib.error.URLError("down")
    outage = utils.HGNCNormalizer().normalize_symbol("PKD1")
    assert utils.normalization_status(outage) == "hgnc_unavailable"
    routes["symbol"] = empty()
    routes["alias_symbol"] = hits({"hgnc_id": "HGNC:1"}, {"hgnc_id": "HGNC:2"})
    ambiguous = utils.HGNCNormalizer().normalize_symbol("OLD1")
    assert utils.normalization_status(ambiguous) == "ambiguous"
    assert utils.normalization_status({"found": False}) == "not_found"
