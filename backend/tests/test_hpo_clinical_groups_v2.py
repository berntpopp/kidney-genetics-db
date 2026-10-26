"""HPO clinical groups v2: root terms, frequency x information content (#338).

Spec: .planning/specs/2026-10-26-hpo-clinical-groups-v2.md. Golden fixtures are
extracted from the pinned HPO 2026-09-01 release (genes_to_phenotype.txt rows of
seven genes whose terms fall under a group root, the matching hp.json subgraph, and
the disease counts n(t), N used for IC), so these tests run offline.
"""

import hashlib
import importlib.util
import json
import math
import os
import re
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.core.datasource_config import get_source_parameter
from app.pipeline.sources.annotations.hpo import (
    CLINICAL_GROUP_METHOD,
    CLINICAL_GROUP_PRIORITY,
    SECONDARY_GROUP_RATIO,
    BulkDataSourceMixin,
    ClinicalGroupClassifier,
    HPOAnnotationSource,
    hpo_frequency,
    load_hpo_parents,
)

FIXTURES = Path(__file__).parent / "fixtures" / "hpo"
CONFIG = Path(__file__).parents[1] / "config" / "datasources.yaml"
EVAL_SCRIPT = Path(__file__).parents[1] / "scripts" / "evaluate_hpo_clinical_groups.py"

# Tiny ontology: ROOT > A > A1 > A11, ROOT > B > B1, ROOT > X
PARENTS = {
    "HP:A": {"HP:ROOT"},
    "HP:A1": {"HP:A"},
    "HP:A11": {"HP:A1"},
    "HP:B": {"HP:ROOT"},
    "HP:B1": {"HP:B"},
    "HP:X": {"HP:ROOT"},
}
GROUPS = {"cakut": ["HP:A"], "neoplasia": ["HP:B"]}
LN4 = math.log(4)


def _tiny() -> ClinicalGroupClassifier:
    classifier = ClinicalGroupClassifier(PARENTS, GROUPS, "test")
    # 4 diseases: n(A11)=1, n(A1)=2, n(B1)=1, n(ROOT)=4
    classifier.fit_information_content([{"HP:A11"}, {"HP:A1"}, {"HP:B1"}, {"HP:X"}])
    return classifier


# ---------- unit: frequency, IC, pruning, secondary, ties, None ----------


@pytest.mark.parametrize(
    ("value", "expected"),
    [
        ("HP:0040280", 1.0),  # obligate
        ("HP:0040281", 0.895),  # very frequent, 80-99 % midpoint
        ("HP:0040282", 0.545),
        ("HP:0040283", 0.17),
        ("HP:0040284", 0.025),
        ("HP:0040285", 0.0),  # excluded
        ("3/5", 3.8 / 7),
        ("0/4", 0.8 / 6),
        ("50%", 0.5),
        ("12.5%", 0.125),
        ("0%", 0.0),
        ("-", 0.35),
        ("", 0.35),
    ],
)
def test_frequency(value, expected):
    assert hpo_frequency(value) == pytest.approx(expected)


def test_information_content_counts_diseases_under_each_term():
    ic = _tiny().ic
    assert ic["HP:A11"] == pytest.approx(LN4)
    assert ic["HP:A1"] == pytest.approx(math.log(2))
    assert ic["HP:A"] == pytest.approx(math.log(2))
    assert ic["HP:ROOT"] == pytest.approx(0.0)


def test_most_specific_term_only_and_frequency_weight():
    result = _tiny().classify({"d1": {"HP:A1": 1.0, "HP:A11": 0.5}})
    assert result["evidence"]["cakut"] == round(0.5 * LN4, 3)  # A1 pruned: A11 is below it
    assert result["supporting_terms"] == ["HP:A11"]


def test_evidence_sums_over_diseases():
    result = _tiny().classify({"d1": {"HP:A11": 1.0}, "d2": {"HP:A11": 1.0}})
    assert result["evidence"]["cakut"] == round(2 * LN4, 3)


def test_secondary_at_calibrated_share_of_primary_evidence():
    classifier = _tiny()
    at_cut = classifier.classify({"d1": {"HP:A11": 1.0}, "d2": {"HP:B1": 0.4}})
    assert (at_cut["primary"], at_cut["secondary"]) == ("cakut", ["neoplasia"])
    # between the old 0.5 and the new 0.4 cut-off: secondary now
    between = classifier.classify({"d1": {"HP:A11": 1.0}, "d2": {"HP:B1": 0.45}})
    assert between["secondary"] == ["neoplasia"]
    below = classifier.classify({"d1": {"HP:A11": 1.0}, "d2": {"HP:B1": 0.39}})
    assert (below["primary"], below["secondary"]) == ("cakut", [])
    # 0.40 chosen on PanelApp by multi-label macro-F1 (spec: secondary cut-off calibration)
    assert SECONDARY_GROUP_RATIO == 0.4


def test_multilabel_macro_f1_hand_computed():
    spec = importlib.util.spec_from_file_location("evaluate_hpo", EVAL_SCRIPT)
    evaluate = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(evaluate)
    truth = {"g1": {"a"}, "g2": {"a", "b"}, "g3": {"b"}}
    pred = {"g1": {"a", "b"}, "g2": {"a"}, "g3": {"b"}}
    # a: TP 2, FP 0, FN 0 -> 1.0; b: TP 1, FP 1, FN 1 -> 0.5; c: no TP -> 0.0
    assert evaluate.multilabel_macro_f1(pred, truth, ["a", "b", "c"]) == pytest.approx(0.5)


def test_scores_are_share_of_evidence():
    result = _tiny().classify({"d1": {"HP:A11": 1.0, "HP:B1": 0.5}})
    assert result["scores"] == {"cakut": round(1 / 1.5, 3), "neoplasia": round(0.5 / 1.5, 3)}
    assert result["method"] == CLINICAL_GROUP_METHOD
    assert result["hpo_release"] == "test"


def test_tie_goes_to_priority_with_neoplasia_last():
    assert CLINICAL_GROUP_PRIORITY[-1] == "neoplasia"
    result = _tiny().classify({"d1": {"HP:B1": 1.0, "HP:A11": 1.0}})
    assert (result["primary"], result["secondary"]) == ("cakut", ["neoplasia"])


def test_no_matching_term_has_no_primary():
    result = _tiny().classify({"d1": {"HP:X": 1.0}})
    assert result["primary"] is None
    assert result["secondary"] == []
    assert result["scores"] == {"cakut": 0.0, "neoplasia": 0.0}
    assert result["supporting_terms"] == []


# ---------- golden genes (pinned HPO 2026-09-01 fixture) ----------


def _golden() -> tuple[ClinicalGroupClassifier, dict]:
    groups = {k: v["root_terms"] for k, v in get_source_parameter("HPO", "clinical_groups").items()}
    classifier = ClinicalGroupClassifier(
        load_hpo_parents(FIXTURES / "hp_golden_subset.json"), groups, "2026-09-01"
    )
    counts = json.loads((FIXTURES / "information_content_golden.json").read_text())
    classifier.ic = {t: -math.log(n / counts["N"]) for t, n in counts["n"].items()}
    source = HPOAnnotationSource.__new__(HPOAnnotationSource)
    return classifier, source.parse_bulk_file(FIXTURES / "genes_to_phenotype_golden.tsv")


@pytest.mark.parametrize(
    ("symbol", "primary", "secondary"),
    [
        ("HNF1B", "cakut", ["cyst_cilio"]),
        ("VHL", "neoplasia", ["glomerulopathy"]),  # known miss: glomerulopathy at 0.84
        ("FH", "neoplasia", ["glomerulopathy"]),
        # neoplasia evidence is 0.493 of cakut: secondary at the calibrated 0.40 cut-off
        ("PALB2", "cakut", ["neoplasia"]),
        ("CFH", "complement", []),
        ("COL4A5", "glomerulopathy", []),
        # kidney stones and proteinuria at 0.46 of cyst_cilio: secondary at 0.40
        ("PKD1", "cyst_cilio", ["nephrolithiasis", "glomerulopathy"]),
    ],
)
def test_golden_genes(symbol, primary, secondary):
    classifier, bulk = _golden()
    result = classifier.classify(bulk[symbol]["disease_terms"])
    assert (result["primary"], result["secondary"]) == (primary, secondary)


def test_palb2_neoplasia_share_of_cakut_evidence():
    classifier, bulk = _golden()
    evidence = classifier.classify(bulk["PALB2"]["disease_terms"])["evidence"]
    assert round(evidence["neoplasia"] / evidence["cakut"], 3) == 0.493


# ---------- YAML: roots exist, are current, comments are hp.json labels ----------


def test_yaml_root_terms_match_pinned_hp_json_labels():
    graph = json.loads((FIXTURES / "hp_golden_subset.json").read_text())["graphs"][0]
    nodes = {n["id"].rsplit("/", 1)[-1].replace("_", ":"): n for n in graph["nodes"]}
    text = CONFIG.read_text()
    block = text[text.index("    clinical_groups:\n") : text.index("    onset_groups:\n")]
    commented = dict(re.findall(r"- (HP:\d{7})  # (.+)", block))
    groups = get_source_parameter("HPO", "clinical_groups")
    roots = [t for g in groups.values() for t in g["root_terms"]]
    assert sorted(commented) == sorted(roots)
    for term, comment in commented.items():
        assert not nodes[term].get("meta", {}).get("deprecated"), term
        assert nodes[term]["lbl"] == comment, term
    assert list(groups) == list(CLINICAL_GROUP_PRIORITY)


def test_yaml_pins_release_urls():
    release = get_source_parameter("HPO", "hpo_release")
    assert release == "2026-09-01"
    for key in ("genes_to_phenotype_url", "hp_json_url"):
        assert f"/releases/download/v{release}/" in get_source_parameter("HPO", key)


# ---------- fail closed: no write when a pinned file is missing or broken ----------


def _gene() -> MagicMock:
    gene = MagicMock(id=1, approved_symbol="PKD1", hgnc_id="HGNC:9008")
    return gene


def _source_without_hp_json(tmp_path: Path) -> HPOAnnotationSource:
    source = HPOAnnotationSource(MagicMock())
    source._bulk_data = HPOAnnotationSource.parse_bulk_file(
        source, FIXTURES / "genes_to_phenotype_golden.tsv"
    )
    source.ensure_bulk_data_loaded = AsyncMock()
    source._download_hp_json = AsyncMock(return_value=tmp_path / "missing_hp.json")
    return source


@pytest.mark.asyncio
async def test_missing_hp_json_fails_batch_and_writes_nothing(tmp_path):
    source = _source_without_hp_json(tmp_path)
    source.session.query.return_value.all.return_value = [_gene()]
    source.store_annotation = MagicMock()
    with pytest.raises(FileNotFoundError):
        await source.fetch_batch([_gene()])
    with patch.object(source, "_refresh_materialized_view"):
        await source.update_all_genes()
    source.store_annotation.assert_not_called()


@pytest.mark.asyncio
async def test_missing_hp_json_fails_per_gene_path_and_writes_nothing(tmp_path):
    source = _source_without_hp_json(tmp_path)
    source.store_annotation = MagicMock()
    cache = MagicMock(get=AsyncMock(return_value=None), set=AsyncMock())
    with patch("app.pipeline.sources.annotations.base.get_cache_service", return_value=cache):
        assert await source.update_gene(_gene()) is False
    source.store_annotation.assert_not_called()


@pytest.mark.asyncio
async def test_unparseable_hp_json_fails(tmp_path):
    broken = tmp_path / "hp.json"
    broken.write_text("<html>rate limited</html>")
    source = _source_without_hp_json(tmp_path)
    source._download_hp_json = AsyncMock(return_value=broken)
    with pytest.raises(ValueError):
        await source.fetch_batch([_gene()])


@pytest.mark.asyncio
async def test_missing_genes_to_phenotype_fails_instead_of_api_fallback(tmp_path):
    source = HPOAnnotationSource(MagicMock())
    source.ensure_bulk_data_loaded = AsyncMock(side_effect=OSError("download failed"))
    source._fetch_via_api = AsyncMock()
    with pytest.raises(OSError):
        await source.fetch_batch([_gene()])
    source._fetch_via_api.assert_not_called()


@pytest.mark.asyncio
async def test_cached_v1_classification_is_not_restored():
    source = HPOAnnotationSource(MagicMock())
    source.store_annotation = MagicMock()
    source.fetch_annotation = AsyncMock(return_value=None)
    v1 = {
        "gene_symbol": "PKD1",
        "phenotypes": [{"id": "HP:0000107"}],
        "classification": {"clinical_group": {"primary": "cakut", "scores": {"cakut": 1.0}}},
    }
    cache = MagicMock(get=AsyncMock(return_value=v1), set=AsyncMock())
    with patch("app.pipeline.sources.annotations.base.get_cache_service", return_value=cache):
        assert await source.update_gene(_gene()) is False
    source.store_annotation.assert_not_called()


# ---------- review fixes ----------


def _hp_json_cache_path(cache_dir: Path) -> Path:
    class _Probe(BulkDataSourceMixin):
        bulk_file_url = get_source_parameter("HPO", "hp_json_url")
        bulk_file_format = "json"
        bulk_cache_dir = cache_dir

    return _Probe()._bulk_cache_path()


@pytest.mark.asyncio
async def test_truncated_cached_genes_to_phenotype_raises_writes_nothing_and_is_deleted(tmp_path):
    source = HPOAnnotationSource(MagicMock())
    source.bulk_cache_dir = tmp_path
    cached = source._bulk_cache_path()
    # A fresh but truncated cache file (would otherwise be reused for 7 days)
    cached.write_text((FIXTURES / "genes_to_phenotype_golden.tsv").read_text()[:2000])
    source._download_hp_json = AsyncMock(return_value=FIXTURES / "hp_golden_subset.json")
    source.session.query.return_value.all.return_value = [_gene()]
    source.store_annotation = MagicMock()
    with pytest.raises(ValueError, match="sha256"):
        await source.fetch_batch([_gene()])
    assert not cached.exists()
    with patch.object(source, "_refresh_materialized_view"):
        await source.update_all_genes()
    source.store_annotation.assert_not_called()


@pytest.mark.asyncio
async def test_corrupted_cached_hp_json_raises_and_is_deleted(tmp_path):
    source = HPOAnnotationSource(MagicMock())
    source.bulk_cache_dir = tmp_path
    source._bulk_data = source.parse_bulk_file(FIXTURES / "genes_to_phenotype_golden.tsv")
    source.ensure_bulk_data_loaded = AsyncMock()
    cached = _hp_json_cache_path(tmp_path)
    cached.write_text((FIXTURES / "hp_golden_subset.json").read_text())  # valid JSON, wrong file
    with pytest.raises(ValueError, match="sha256"):
        await source.fetch_batch([_gene()])
    assert not cached.exists()


def _jax_source(response: MagicMock) -> HPOAnnotationSource:
    source = HPOAnnotationSource(MagicMock())
    source.apply_rate_limit = AsyncMock()
    source.get_http_client = AsyncMock(return_value=MagicMock(get=AsyncMock(return_value=response)))
    source._load_clinical_group_classifier = AsyncMock()
    source._bulk_data = {}
    return source


@pytest.mark.asyncio
async def test_jax_outage_is_not_stored_as_no_hpo_data():
    import httpx

    request = httpx.Request("GET", "https://ontology.jax.org/api/network/search/gene")
    source = _jax_source(httpx.Response(503, request=request))
    source.store_annotation = MagicMock()
    cache = MagicMock(get=AsyncMock(return_value=None), set=AsyncMock())
    with (
        patch("app.core.retry_utils.asyncio.sleep", AsyncMock()),
        patch("app.pipeline.sources.annotations.base.get_cache_service", return_value=cache),
    ):
        assert await source.fetch_annotation(_gene()) is None
        assert await source.update_gene(_gene()) is False
    source.store_annotation.assert_not_called()


@pytest.mark.asyncio
async def test_jax_genuine_no_match_is_stored_as_no_hpo_data():
    import httpx

    request = httpx.Request("GET", "https://ontology.jax.org/api/network/search/gene")
    source = _jax_source(httpx.Response(200, json={"results": []}, request=request))
    result = await source.fetch_annotation(_gene())
    assert result["has_hpo_data"] is False
    assert result["classification"] == {}


@pytest.mark.asyncio
async def test_loaded_classifier_is_shared_across_instances(monkeypatch):
    monkeypatch.setattr(HPOAnnotationSource, "_loaded_classifiers", {})
    loads = 0

    async def fake_load(self):
        nonlocal loads
        loads += 1
        self._bulk_data = self.parse_bulk_file(FIXTURES / "genes_to_phenotype_golden.tsv")

    monkeypatch.setattr(HPOAnnotationSource, "ensure_bulk_data_loaded", fake_load)
    hp_json = AsyncMock(return_value=FIXTURES / "hp_golden_subset.json")
    monkeypatch.setattr(HPOAnnotationSource, "_download_hp_json", hp_json)
    first, second = HPOAnnotationSource(MagicMock()), HPOAnnotationSource(MagicMock())
    classifier = await first._load_clinical_group_classifier()
    assert await second._load_clinical_group_classifier() is classifier
    assert second.lookup_gene("PKD1") is not None
    # ontology + IC are built once; the parsed rows stay per instance (freed after a run)
    assert hp_json.await_count == 1
    assert loads == 2
    assert first._bulk_data is not second._bulk_data


# information_content_golden.json holds n(t) and N computed from the full pinned
# genes_to_phenotype.txt (2026-09-01) for the fixture terms; it cannot be refit from
# the 7-gene fixture. Set HPO_RELEASE_DIR to a local copy of the release to check it
# against fit_information_content.
@pytest.mark.skipif(not os.environ.get("HPO_RELEASE_DIR"), reason="needs HPO_RELEASE_DIR")
def test_golden_ic_matches_fit_on_full_pinned_corpus():
    release = Path(os.environ["HPO_RELEASE_DIR"])
    g2p = release / "genes_to_phenotype.txt"
    assert hashlib.sha256(g2p.read_bytes()).hexdigest() == get_source_parameter(
        "HPO", "genes_to_phenotype_sha256"
    )
    bulk = HPOAnnotationSource.parse_bulk_file(
        HPOAnnotationSource.__new__(HPOAnnotationSource), g2p
    )
    corpus: dict[str, set[str]] = {}
    for gene in bulk.values():
        for disease, terms in gene["disease_terms"].items():
            corpus.setdefault(disease, set()).update(terms)
    classifier = ClinicalGroupClassifier(load_hpo_parents(release / "hp.json"), {}, "2026-09-01")
    classifier.fit_information_content(corpus.values())
    counts = json.loads((FIXTURES / "information_content_golden.json").read_text())
    assert len(corpus) == counts["N"]
    for term in ("HP:0000107", "HP:0000093", "HP:0000787"):  # roots of three groups
        assert classifier.ic[term] == pytest.approx(-math.log(counts["n"][term] / counts["N"]))


# FANCA stays cakut without neoplasia: HPO 2026-09-01 has no FANCA annotation at or
# below Renal neoplasm (HP:0009726). This is an HPO-data limit, not a cut-off issue;
# never add annotations by hand.
@pytest.mark.skipif(not os.environ.get("HPO_RELEASE_DIR"), reason="needs HPO_RELEASE_DIR")
def test_fanca_has_no_renal_neoplasm_annotation_in_pinned_release():
    release = Path(os.environ["HPO_RELEASE_DIR"])
    bulk = HPOAnnotationSource.parse_bulk_file(
        HPOAnnotationSource.__new__(HPOAnnotationSource), release / "genes_to_phenotype.txt"
    )
    groups = {k: v["root_terms"] for k, v in get_source_parameter("HPO", "clinical_groups").items()}
    classifier = ClinicalGroupClassifier(
        load_hpo_parents(release / "hp.json"), groups, "2026-09-01"
    )
    terms = set().union(*bulk["FANCA"]["disease_terms"].values())
    assert not any("HP:0009726" in classifier.ancestors(t) for t in terms)
    classifier.ic = dict.fromkeys(classifier.parents, 1.0)  # IC irrelevant: no neoplasia term
    result = classifier.classify(bulk["FANCA"]["disease_terms"])
    assert result["primary"] == "cakut"
    assert "neoplasia" not in result["secondary"]
