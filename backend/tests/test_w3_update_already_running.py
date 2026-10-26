"""Triggering a source that is already running answers 409, not "update triggered" (#366)."""

import asyncio

import pytest
from httpx import AsyncClient

from app.core import background_tasks
from app.core.background_tasks import task_manager
from app.core.security import create_access_token
from tests.fixtures.auth import get_or_create_user


@pytest.mark.integration
async def test_update_of_running_source_is_409(
    async_client: AsyncClient, db_session, monkeypatch: pytest.MonkeyPatch
) -> None:
    user = get_or_create_user(
        db_session, "w3_admin", "w3_admin@example.com", "Unused-Pw-1!", "admin"
    )
    headers = {"Authorization": f"Bearer {create_access_token(subject=user.username)}"}
    monkeypatch.setattr(background_tasks.settings, "USE_ARQ_WORKER", False)
    running = asyncio.get_running_loop().create_future()
    monkeypatch.setitem(task_manager.running_tasks, "PanelApp", running)

    try:
        resp = await async_client.post("/api/datasources/PanelApp/update", headers=headers)
    finally:
        running.cancel()

    assert resp.status_code == 409, resp.text
