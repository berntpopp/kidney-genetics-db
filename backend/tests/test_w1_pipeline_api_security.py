"""#361: reset honours ?gene_ids=, validate needs admin, the progress WebSocket needs admin auth."""

from contextlib import contextmanager
from unittest.mock import AsyncMock, patch

import pytest
from starlette.testclient import TestClient
from starlette.websockets import WebSocketDisconnect

from app.api.endpoints.progress import manager
from app.core.security import create_access_token
from app.main import app
from tests.fixtures.auth import get_or_create_user


def _admin_headers(db_session) -> dict[str, str]:
    admin = get_or_create_user(db_session, "w1_admin", "w1_admin@example.com", "Pw-1!", "admin")
    return {"Authorization": f"Bearer {create_access_token(subject=admin.username)}"}


@pytest.mark.asyncio
async def test_reset_limits_to_gene_ids_query(db_session, async_client):
    reset = "app.api.endpoints.annotation_updates._run_annotation_reset"
    with patch(reset, AsyncMock()) as run_reset:
        response = await async_client.delete(
            "/api/annotations/reset?source=gnomad&gene_ids=42&gene_ids=43",
            headers=_admin_headers(db_session),
        )

    assert response.status_code == 200
    assert run_reset.await_args.kwargs["gene_ids"] == [42, 43]


@pytest.mark.asyncio
async def test_validate_requires_login(async_client):
    response = await async_client.post("/api/annotations/pipeline/validate")

    assert response.status_code == 401


@contextmanager
def _ws_db(db_session, sessions_open: list[bool]):
    """Hand the endpoint the test session and record whether it is still held."""

    @contextmanager
    def session():
        sessions_open.append(True)
        yield db_session
        sessions_open[-1] = False

    with patch("app.api.endpoints.progress.SessionLocal", session):
        yield


def test_websocket_refuses_missing_or_bad_token(db_session):
    client = TestClient(app)  # no context manager: the app lifespan (startup tasks) must not run
    with _ws_db(db_session, []):
        for auth in ({"type": "auth"}, {"type": "auth", "token": "not-a-jwt"}):
            with client.websocket_connect("/api/progress/ws") as ws:
                ws.send_json(auth)
                with pytest.raises(WebSocketDisconnect) as closed:
                    ws.receive_json()
            assert closed.value.code == 4401
    assert not manager.active_connections


def test_websocket_admin_gets_status_without_holding_a_session(db_session):
    token = _admin_headers(db_session)["Authorization"].removeprefix("Bearer ")
    sessions_open: list[bool] = []
    client = TestClient(app)
    with _ws_db(db_session, sessions_open):
        with client.websocket_connect("/api/progress/ws") as ws:
            ws.send_json({"type": "auth", "token": token})
            assert ws.receive_json()["type"] == "initial_status"
            assert sessions_open == [False]  # the DB session closed before the socket idles
            assert len(manager.active_connections) == 1
    assert not manager.active_connections  # disconnect ran on the close path
