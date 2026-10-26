"""Regression tests for #286: gene, source-update and staging writes require roles."""

from unittest.mock import AsyncMock
from uuid import uuid4

import pytest
from httpx import AsyncClient

from app.api.endpoints import datasources
from app.core.security import create_access_token
from app.models.gene_staging import GeneNormalizationStaging
from tests.fixtures.auth import get_or_create_user

GENE = {"approved_symbol": "AUDITFAKE286", "hgnc_id": "HGNC:99999286"}


def _auth(db_session, role: str) -> dict[str, str]:
    user = get_or_create_user(
        db_session, f"audit286_{role}", f"audit286_{role}@example.com", "Unused-Pw-1!", role
    )
    return {"Authorization": f"Bearer {create_access_token(subject=user.username)}"}


def _staging(db_session) -> int:
    record = GeneNormalizationStaging(
        # One open record per text is allowed (migration 0010)
        original_text=f"AUDIT286-{uuid4().hex[:8]}",
        source_name="audit",
        original_data={},
        normalization_log={},
    )
    db_session.add(record)
    db_session.commit()
    return record.id


@pytest.fixture
def no_source_runs(monkeypatch: pytest.MonkeyPatch) -> AsyncMock:
    run = AsyncMock()
    monkeypatch.setattr(datasources.task_manager, "run_source", run)
    return run


def _routes(staging_id: int) -> list[tuple[str, dict]]:
    return [
        ("/api/genes/", GENE),
        ("/api/datasources/PanelApp/update", {}),
        ("/api/datasources/update-all", {}),
        (f"/api/staging/staging/{staging_id}/approve", {**GENE, "reviewer": "forged"}),
        (f"/api/staging/staging/{staging_id}/reject", {"reviewer": "forged"}),
    ]


@pytest.mark.integration
async def test_anonymous_and_viewer_rejected(
    async_client: AsyncClient, db_session, no_source_runs: AsyncMock
) -> None:
    viewer = _auth(db_session, "viewer")
    for url, body in _routes(_staging(db_session)):
        assert (await async_client.post(url, json=body)).status_code == 401, url
        assert (await async_client.post(url, json=body, headers=viewer)).status_code == 403, url
    no_source_runs.assert_not_called()


@pytest.mark.integration
async def test_curator_cannot_trigger_source_updates(
    async_client: AsyncClient, db_session, no_source_runs: AsyncMock
) -> None:
    curator = _auth(db_session, "curator")
    for url in ("/api/datasources/PanelApp/update", "/api/datasources/update-all"):
        assert (await async_client.post(url, headers=curator)).status_code == 403, url
    no_source_runs.assert_not_called()


@pytest.mark.integration
async def test_admin_triggers_source_updates(
    async_client: AsyncClient, db_session, no_source_runs: AsyncMock
) -> None:
    admin = _auth(db_session, "admin")
    resp = await async_client.post("/api/datasources/PanelApp/update", headers=admin)
    assert resp.status_code == 200, resp.text
    resp = await async_client.post("/api/datasources/update-all", headers=admin)
    assert resp.status_code == 200, resp.text
    assert no_source_runs.await_count >= 1


@pytest.mark.integration
async def test_curator_creates_gene_and_reviews_as_self(
    async_client: AsyncClient, db_session
) -> None:
    curator = _auth(db_session, "curator")
    resp = await async_client.post("/api/genes/", json=GENE, headers=curator)
    assert resp.status_code == 200, resp.text

    approve_id, reject_id = _staging(db_session), _staging(db_session)
    resp = await async_client.post(
        f"/api/staging/staging/{approve_id}/approve",
        json={**GENE, "reviewer": "forged"},
        headers=curator,
    )
    assert resp.status_code == 200, resp.text
    resp = await async_client.post(
        f"/api/staging/staging/{reject_id}/reject", json={"reviewer": "forged"}, headers=curator
    )
    assert resp.status_code == 200, resp.text

    for staging_id in (approve_id, reject_id):
        record = db_session.get(GeneNormalizationStaging, staging_id)
        db_session.refresh(record)
        assert record.reviewed_by == "audit286_curator"
