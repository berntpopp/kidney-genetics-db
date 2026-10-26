"""HPO/MPO descendant sets come from the pinned release and never shrink silently (#365.5)."""

from unittest.mock import AsyncMock, MagicMock, patch

import httpx
import pytest

from app.core.hpo.terms import HPOTerms
from app.pipeline.sources.annotations.hpo import ClinicalGroupClassifier, HPOAnnotationSource
from app.pipeline.sources.annotations.mpo_mgi import MPOMGIAnnotationSource

PARENTS = {"HP:A": {"HP:ROOT"}, "HP:A1": {"HP:A"}, "HP:A11": {"HP:A1"}, "HP:B": {"HP:ROOT"}}


@pytest.mark.unit
def test_classifier_descendants_from_pinned_ontology() -> None:
    classifier = ClinicalGroupClassifier(PARENTS, {}, "test")
    assert classifier.descendants("HP:A") == {"HP:A", "HP:A1", "HP:A11"}
    with pytest.raises(ValueError):
        classifier.descendants("HP:9999999")


@pytest.mark.unit
@pytest.mark.asyncio
async def test_source_descendants_use_pinned_classifier_and_raise_on_unknown_root() -> None:
    source = HPOAnnotationSource.__new__(HPOAnnotationSource)
    source._descendants = {}
    source._load_clinical_group_classifier = AsyncMock(  # type: ignore[method-assign]
        return_value=ClinicalGroupClassifier(PARENTS, {}, "test")
    )
    config = {
        "onset_groups": {"adult": {"root_terms": ["HP:A", "HP:B"]}},
        "kidney_terms": ["HP:A1"],
    }
    with patch(
        "app.pipeline.sources.annotations.hpo.get_source_parameter",
        side_effect=lambda _s, key, default=None: config.get(key, default),
    ):
        assert await source.get_classification_term_descendants("onset_groups") == {
            "adult": {"HP:A", "HP:A1", "HP:A11", "HP:B"}
        }
        assert await source.get_kidney_term_descendants() == {"HP:A1", "HP:A11"}
        # Built once per source instance, not per gene
        assert await source.get_kidney_term_descendants() == {"HP:A1", "HP:A11"}
        assert source._load_clinical_group_classifier.await_count == 2
        source._descendants.clear()
        config["kidney_terms"] = ["HP:9999999"]
        with pytest.raises(ValueError):
            await source.get_kidney_term_descendants()


@pytest.mark.unit
@pytest.mark.asyncio
async def test_hpo_api_descendants_raise_instead_of_returning_root_only() -> None:
    terms = HPOTerms.__new__(HPOTerms)
    terms.ttl_stable = 1
    terms._get = AsyncMock(side_effect=httpx.ConnectError("down"))  # type: ignore[method-assign]
    with pytest.raises(httpx.ConnectError):
        await terms.get_descendants("HP:0010935")


@pytest.mark.unit
@pytest.mark.asyncio
async def test_mpo_terms_failure_raises_and_writes_no_partial_set() -> None:
    source = MPOMGIAnnotationSource(MagicMock())
    root = MagicMock()
    root.json.return_value = [
        {"children": [{"data": {"accID": "MP:1"}, "id": 2, "children": True}]}
    ]
    client = MagicMock(get=AsyncMock(side_effect=[root, httpx.ConnectError("down")]))
    with (
        patch.object(source, "get_http_client", AsyncMock(return_value=client)),
        patch.object(source, "apply_rate_limit", AsyncMock()),
        pytest.raises(httpx.ConnectError),
    ):
        await source.fetch_kidney_mpo_terms()
