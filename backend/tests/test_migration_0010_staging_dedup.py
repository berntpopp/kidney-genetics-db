"""Migration 0010: staging duplicates folded into the reused row, then kept unique (#366)."""

import pytest
from sqlalchemy import text
from sqlalchemy.exc import IntegrityError

from tests.test_audit_migration_views import (  # noqa: F401 - baseline_db is a fixture
    _alembic,
    baseline_db,
)


def _stage(conn, original: str, status: str, reviewed_by: str | None = None) -> int:
    return int(
        conn.execute(
            text(
                "INSERT INTO gene_normalization_staging (original_text, source_name, "
                "normalization_log, status, reviewed_by, created_at, updated_at, priority_score, "
                "requires_expert_review, is_duplicate_submission) VALUES (:t, 'PubTator', '{}', "
                ":s, :r, now(), now(), 0, false, false) RETURNING id"
            ),
            {"t": original, "s": status, "r": reviewed_by},
        ).scalar_one()
    )


def _rows(conn, original: str) -> list[tuple[int, str]]:
    rows = conn.execute(
        text(
            "SELECT id, status FROM gene_normalization_staging WHERE original_text = :t ORDER BY id"
        ),
        {"t": original},
    )
    return [(r.id, r.status) for r in rows]


@pytest.mark.integration
def test_0010_folds_duplicates_without_losing_reviews(baseline_db):  # noqa: F811
    engine, url = baseline_db
    _alembic(url, "upgrade", "0009")
    with engine.begin() as conn:
        copies = [_stage(conn, "HLA_A", "pending_review") for _ in range(3)]
        pending = _stage(conn, "MIXED", "pending_review")
        approved = _stage(conn, "MIXED", "approved", reviewed_by="curator")
        rejected = _stage(conn, "MIXED", "rejected", reviewed_by="curator")
        in_review = _stage(conn, "MIXED", "in_review")

    _alembic(url, "upgrade", "head")
    with engine.begin() as conn:
        # Exact unreviewed copies go; the oldest stays
        assert _rows(conn, "HLA_A") == [(copies[0], "pending_review")]
        # The approved row is what the CRUD reuses; the rest is marked, not deleted
        assert _rows(conn, "MIXED") == [
            (pending, "duplicate"),
            (approved, "approved"),
            (rejected, "duplicate"),
            (in_review, "in_review"),
        ]

    with pytest.raises(IntegrityError), engine.begin() as conn:
        _stage(conn, "HLA_A", "rejected")

    _alembic(url, "downgrade", "0009")
    with engine.begin() as conn:
        _stage(conn, "HLA_A", "pending_review")  # no index after downgrade
        conn.execute(text("DELETE FROM gene_normalization_staging WHERE original_text = 'HLA_A'"))
    _alembic(url, "upgrade", "head")
