"""Clinical-group primary must not depend on config dict order (#254)."""

from unittest.mock import MagicMock, patch

import pytest

from app.pipeline.sources.annotations.hpo import HPOAnnotationSource

CAKUT = {"signature_terms": ["HP:0000107", "HP:0000085"], "weight": 1.0}
CYST = {"signature_terms": ["HP:0000107", "HP:0005562"], "weight": 1.0}


async def _primary(config: dict, phenotype_ids: set[str]) -> str | None:
    source = HPOAnnotationSource(MagicMock())
    with patch("app.core.datasource_config.get_source_parameter", return_value=config):
        return (await source._classify_clinical_group(phenotype_ids))["primary"]


@pytest.mark.asyncio
async def test_equal_scores_pick_same_group_regardless_of_dict_order():
    # HP:0000107 (Renal cyst) is a signature term of both cakut and cyst_cilio.
    forward = await _primary({"cakut": CAKUT, "cyst_cilio": CYST}, {"HP:0000107"})
    reverse = await _primary({"cyst_cilio": CYST, "cakut": CAKUT}, {"HP:0000107"})
    assert forward == reverse == "cakut"


@pytest.mark.asyncio
async def test_higher_score_still_wins_over_priority():
    config = {"cakut": CAKUT, "cyst_cilio": CYST}
    assert await _primary(config, {"HP:0000107", "HP:0005562"}) == "cyst_cilio"


@pytest.mark.asyncio
async def test_unlisted_groups_tie_break_alphabetically_after_listed():
    group = {"signature_terms": ["HP:0000107"], "weight": 1.0}
    config = {"zeta": group, "alpha": group}
    assert await _primary(config, {"HP:0000107"}) == "alpha"
    assert await _primary({"zeta": group, "cakut": group}, {"HP:0000107"}) == "cakut"


@pytest.mark.asyncio
async def test_no_match_has_no_primary():
    assert await _primary({"cakut": CAKUT}, {"HP:9999999"}) is None
