"""AUTO_UPDATE_ENABLED=false keeps the annotation cron jobs off (#378)."""

import pytest

from app.core.config import settings
from app.core.scheduler import AnnotationScheduler


@pytest.mark.unit
async def test_flag_off_registers_no_cron_jobs(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(settings, "AUTO_UPDATE_ENABLED", False)
    scheduler = AnnotationScheduler()
    scheduler.start()
    assert not scheduler.is_running
    assert scheduler.get_jobs() == []
    assert scheduler.trigger_job("daily_incremental") is False


@pytest.mark.unit
async def test_flag_on_schedules_daily_and_weekly(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(settings, "AUTO_UPDATE_ENABLED", True)
    scheduler = AnnotationScheduler()
    scheduler.start()
    try:
        assert {j["id"] for j in scheduler.get_jobs()} == {"daily_incremental", "weekly_full"}
    finally:
        scheduler.stop()
