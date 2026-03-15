"""Tests for DataSourceProgress model schema alignment."""

import pytest
from sqlalchemy.dialects.postgresql import JSONB

from app.models.progress import DataSourceProgress


@pytest.mark.unit
class TestDataSourceProgressModel:
    def test_progress_metadata_is_jsonb(self):
        col = DataSourceProgress.__table__.columns["metadata"]
        assert isinstance(col.type, JSONB), (
            f"metadata column should be JSONB, got {type(col.type).__name__}"
        )

    def test_progress_metadata_maps_to_metadata_column(self):
        col = DataSourceProgress.__table__.columns["metadata"]
        assert col.name == "metadata", "Python attr progress_metadata should map to DB column 'metadata'"
