"""Pending staging pages through every item with server-side filters and a total (#422)."""

from uuid import uuid4

import pytest
from httpx import AsyncClient

from app.core.security import create_access_token
from app.models.gene_staging import GeneNormalizationStaging
from tests.fixtures.auth import get_or_create_user

URL = "/api/staging/staging/pending"


@pytest.fixture
def curator(db_session) -> dict[str, str]:
    user = get_or_create_user(
        db_session, "stage422", "stage422@example.com", "Pw-422-ok!", "curator"
    )
    return {"Authorization": f"Bearer {create_access_token(subject=user.username)}"}


@pytest.fixture
def staged(db_session) -> str:
    """Seven pending rows in a source of their own, all with one priority, plus noise."""
    source = f"src422-{uuid4().hex[:8]}"
    rows = [
        GeneNormalizationStaging(
            original_text=f"G422_{i}",
            source_name=source,
            original_data={},
            normalization_log={},
            status="pending_review",
            priority_score=50,
            requires_expert_review=i in (1, 4),
        )
        for i in range(7)
    ]
    rows.append(
        GeneNormalizationStaging(
            original_text="G422_done",
            source_name=source,
            original_data={},
            normalization_log={},
            status="rejected",
            priority_score=99,
        )
    )
    db_session.add_all(rows)
    db_session.commit()
    return source


async def _page(client: AsyncClient, headers: dict[str, str], **params) -> dict:
    resp = await client.get(URL, params=params, headers=headers)
    assert resp.status_code == 200, resp.text
    return resp.json()


@pytest.mark.integration
async def test_pages_cover_every_pending_row_once_in_stable_order(
    async_client: AsyncClient, curator, staged
) -> None:
    seen: list[int] = []
    for offset in (0, 3, 6):
        body = await _page(async_client, curator, source_filter=staged, limit=3, offset=offset)
        assert body["pagination"] == {
            "total": 7,
            "limit": 3,
            "offset": offset,
            "has_more": offset + 3 < 7,
        }
        seen += [item["id"] for item in body["items"]]

    # Equal priority falls back to id, so pages neither overlap nor skip rows
    assert seen == sorted(seen) and len(set(seen)) == 7


@pytest.mark.integration
async def test_filters_run_on_the_server(async_client: AsyncClient, curator, staged) -> None:
    expert = await _page(async_client, curator, source_filter=staged, requires_expert_review=True)
    assert expert["pagination"]["total"] == 2
    assert {i["original_text"] for i in expert["items"]} == {"G422_1", "G422_4"}

    routine = await _page(async_client, curator, source_filter=staged, requires_expert_review=False)
    assert routine["pagination"]["total"] == 5

    found = await _page(async_client, curator, source_filter=staged, search="g422_6")
    assert [i["original_text"] for i in found["items"]] == ["G422_6"]

    # LIKE wildcards in the search are literal text
    assert (await _page(async_client, curator, source_filter=staged, search="%"))["items"] == []

    other = await _page(async_client, curator, source_filter=f"{staged}-none")
    assert other == {
        "items": [],
        "pagination": {"total": 0, "limit": 50, "offset": 0, "has_more": False},
    }
