"""/version reports the applied Alembic revision and the configured environment (#431)."""

from unittest.mock import MagicMock, patch

import pytest

from app.core.version import get_all_versions


@pytest.mark.unit
def test_reports_alembic_revision_and_configured_environment():
    db = MagicMock()
    db.execute.return_value.scalar.return_value = "0012"

    with patch("app.core.version.settings.ENVIRONMENT", "production"):
        versions = get_all_versions(db)

    assert "alembic_version" in str(db.execute.call_args.args[0])
    assert versions["database"] == {"version": "0012", "alembic_revision": "0012"}
    assert versions["environment"] == "production"


@pytest.mark.unit
def test_database_unknown_when_revision_unavailable():
    db = MagicMock()
    db.execute.side_effect = RuntimeError("no alembic_version table")

    assert get_all_versions(db)["database"] == {"version": "unknown"}
