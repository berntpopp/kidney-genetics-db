"""Staging decisions name a real gene and only touch pending rows (#375)."""

from uuid import uuid4

import pytest
from httpx import AsyncClient

from app.core.security import create_access_token
from app.models.gene import Gene
from app.models.gene_staging import GeneNormalizationStaging
from tests.fixtures.auth import get_or_create_user

URL = "/api/staging/staging"


@pytest.fixture
def curator(db_session) -> dict[str, str]:
    user = get_or_create_user(
        db_session, "stage375", "stage375@example.com", "Pw-375-ok!", "curator"
    )
    return {"Authorization": f"Bearer {create_access_token(subject=user.username)}"}


def _stage(db_session, status: str = "pending_review", text: str | None = None) -> int:
    record = GeneNormalizationStaging(
        original_text=text or f"T375-{uuid4().hex[:8]}",
        source_name="test375",
        normalization_log={},
        status=status,
    )
    db_session.add(record)
    db_session.commit()
    return record.id


@pytest.mark.integration
@pytest.mark.parametrize(
    "body",
    [
        {"approved_symbol": "", "hgnc_id": "HGNC:7329"},
        {"approved_symbol": "MSH6", "hgnc_id": "not-an-id"},
        {"approved_symbol": "MSH6", "hgnc_id": None},
        {"approved_symbol": "MS 6", "hgnc_id": "HGNC:7329"},
    ],
)
async def test_approval_needs_a_symbol_and_an_hgnc_id(
    async_client: AsyncClient, db_session, curator, body
) -> None:
    resp = await async_client.post(
        f"{URL}/{_stage(db_session)}/approve", json=body, headers=curator
    )
    assert resp.status_code == 400, resp.text


@pytest.mark.integration
async def test_approval_must_match_a_known_gene(
    async_client: AsyncClient, db_session, curator
) -> None:
    db_session.add(Gene(approved_symbol="KG375REAL", hgnc_id="HGNC:99937501"))
    db_session.commit()
    wrong = {"approved_symbol": "KG375TYPO", "hgnc_id": "HGNC:99937501"}
    resp = await async_client.post(
        f"{URL}/{_stage(db_session)}/approve", json=wrong, headers=curator
    )
    assert resp.status_code == 422 and "KG375REAL" in resp.text  # domain validation error

    right = {"approved_symbol": "KG375REAL", "hgnc_id": "HGNC:99937501"}
    resp = await async_client.post(
        f"{URL}/{_stage(db_session)}/approve", json=right, headers=curator
    )
    assert resp.status_code == 200, resp.text


@pytest.mark.integration
@pytest.mark.parametrize("status", ["duplicate", "approved", "rejected"])
@pytest.mark.parametrize("action", ["approve", "reject"])
async def test_only_pending_rows_can_be_decided(
    async_client: AsyncClient, db_session, curator, status, action
) -> None:
    body = {"approved_symbol": "MSH6", "hgnc_id": "HGNC:7329"} if action == "approve" else {}
    resp = await async_client.post(
        f"{URL}/{_stage(db_session, status)}/{action}", json=body, headers=curator
    )
    assert resp.status_code == 409, resp.text
    assert "UniqueViolation" not in resp.text
