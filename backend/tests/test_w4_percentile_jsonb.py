"""STRING PPI percentiles survive the JSONB (L2 cache) round trip (#367)."""

import json
from unittest.mock import AsyncMock, MagicMock

import pytest
from sqlalchemy import text

from app.core.percentile_service import PercentileService


@pytest.mark.integration
async def test_percentile_lookup_after_jsonb_round_trip(db_session, monkeypatch):
    stored = db_session.execute(
        text("SELECT CAST(:v AS jsonb)"), {"v": json.dumps({42: 0.913})}
    ).scalar_one()
    assert stored == {"42": 0.913}  # JSONB object keys are always text

    cache = MagicMock(get=AsyncMock(return_value=stored))
    monkeypatch.setattr("app.core.percentile_service.get_cache_service", lambda _s: cache)
    service = PercentileService(db_session)
    assert await service.get_percentile_for_gene("string_ppi", 42) == 0.913
    assert await service.calculate_global_percentiles("string_ppi", "ppi_score") == {42: 0.913}
