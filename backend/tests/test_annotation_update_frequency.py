"""update_frequency says what next_update schedules (#370 item 7)."""

import pytest

from app.core.datasource_config import ANNOTATION_SOURCE_CONFIG
from app.pipeline.sources.annotations.clinvar import ClinVarAnnotationSource

DAYS = {"weekly": 7, "monthly": 30, "quarterly": 90}


@pytest.mark.unit
def test_configured_frequency_matches_cache_ttl_days():
    for name, cfg in ANNOTATION_SOURCE_CONFIG.items():
        if name != "common":
            assert DAYS[cfg["update_frequency"]] == cfg["cache_ttl_days"], name


@pytest.mark.integration
def test_source_record_takes_the_configured_frequency(db_session):
    # ClinVar hardcoded "weekly" while it was scheduled every 90 days
    source = ClinVarAnnotationSource(db_session)

    assert source.source_record.update_frequency == "quarterly"
    assert source.cache_ttl_days == DAYS["quarterly"]
