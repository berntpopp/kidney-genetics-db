"""Annotation and unified HPO pipelines must score syndromic features alike (#254)."""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.core.datasource_config import get_source_parameter
from app.pipeline.sources.annotations.hpo import HPOAnnotationSource
from app.pipeline.sources.unified.hpo import HPOUnifiedSource

# Category -> descendant set, keyed by the real configured category names (config order).
DESCENDANTS = {
    "growth": {"HP:G1"},
    "skeletal": {"HP:S1"},
    "neurologic": {"HP:N1"},
    "head_neck": {"HP:H1"},
}
# Three categories matched once each out of 5 terms: sum 0.6 (syndromic) vs mean 0.2 (isolated).
PHENOTYPES = {"HP:N1", "HP:H1", "HP:G1", "HP:K1", "HP:K2"}


async def _annotation(phenotype_ids: set[str]) -> dict:
    source = HPOAnnotationSource(MagicMock())
    source.get_classification_term_descendants = AsyncMock(return_value=DESCENDANTS)
    return await source._assess_syndromic_features(phenotype_ids)


async def _unified(phenotype_ids: set[str]) -> dict:
    roots = get_source_parameter("HPO", "syndromic_indicators", {})
    by_root = {roots[category]: terms for category, terms in DESCENDANTS.items()}
    pipeline = MagicMock()
    pipeline.terms.get_descendants = AsyncMock(side_effect=lambda root, **_: by_root[root])
    source = HPOUnifiedSource(cache_service=MagicMock(), http_client=MagicMock())
    with patch("app.core.hpo.pipeline.HPOPipeline", return_value=pipeline):
        return await source._assess_syndromic_features(phenotype_ids)


def test_config_categories_match_fixture():
    assert list(get_source_parameter("HPO", "syndromic_indicators", {})) == list(DESCENDANTS)


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "phenotype_ids",
    [
        PHENOTYPES,
        {"HP:N1", "HP:K1", "HP:K2", "HP:K3"},  # one category, 0.25: below threshold
        {"HP:K1"},  # no extra-renal match
        set(),
    ],
)
async def test_both_pipelines_give_identical_assessment(phenotype_ids):
    assert await _annotation(phenotype_ids) == await _unified(phenotype_ids)


@pytest.mark.asyncio
async def test_multi_system_gene_is_syndromic_in_both():
    for result in (await _annotation(PHENOTYPES), await _unified(PHENOTYPES)):
        assert result["syndromic_score"] == 0.6
        assert result["is_syndromic"] is True
        assert result["extra_renal_term_counts"] == {"growth": 1, "neurologic": 1, "head_neck": 1}
