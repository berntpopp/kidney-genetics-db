"""Tests for StaticSource, StaticSourceAudit, StaticEvidenceUpload model schema alignment."""

import pytest
from sqlalchemy import BigInteger

from app.models.static_sources import StaticEvidenceUpload, StaticSource, StaticSourceAudit


@pytest.mark.unit
class TestStaticSourceModel:
    """Verify StaticSource columns match design spec."""

    def test_is_active_not_nullable(self):
        col = StaticSource.__table__.columns["is_active"]
        assert col.nullable is False, "is_active should be NOT NULL"

    def test_created_at_has_timezone(self):
        col = StaticSource.__table__.columns["created_at"]
        assert col.type.timezone is True, "created_at should be DateTime(timezone=True)"

    def test_updated_at_has_timezone(self):
        col = StaticSource.__table__.columns["updated_at"]
        assert col.type.timezone is True, "updated_at should be DateTime(timezone=True)"

    def test_created_at_has_server_default(self):
        col = StaticSource.__table__.columns["created_at"]
        assert col.server_default is not None, "created_at should have server_default"

    def test_updated_at_has_server_default(self):
        col = StaticSource.__table__.columns["updated_at"]
        assert col.server_default is not None, "updated_at should have server_default"


@pytest.mark.unit
class TestStaticSourceAuditModel:
    """Verify StaticSourceAudit columns match design spec."""

    def test_source_id_has_cascade_delete(self):
        col = StaticSourceAudit.__table__.columns["source_id"]
        fk = list(col.foreign_keys)[0]
        assert fk.ondelete == "CASCADE", "source_id FK should CASCADE on delete"

    def test_user_id_has_foreign_key(self):
        col = StaticSourceAudit.__table__.columns["user_id"]
        fks = list(col.foreign_keys)
        assert len(fks) == 1, "user_id should have a ForeignKey"
        assert fks[0].column.table.name == "users"

    def test_user_id_fk_set_null_on_delete(self):
        col = StaticSourceAudit.__table__.columns["user_id"]
        fk = list(col.foreign_keys)[0]
        assert fk.ondelete == "SET NULL", "user_id FK should SET NULL on delete"

    def test_changes_has_server_default(self):
        col = StaticSourceAudit.__table__.columns["changes"]
        assert col.server_default is not None, "changes should have server_default"

    def test_performed_at_has_timezone(self):
        col = StaticSourceAudit.__table__.columns["performed_at"]
        assert col.type.timezone is True, "performed_at should be DateTime(timezone=True)"

    def test_performed_at_has_server_default(self):
        col = StaticSourceAudit.__table__.columns["performed_at"]
        assert col.server_default is not None, "performed_at should have server_default"


@pytest.mark.unit
class TestStaticEvidenceUploadModel:
    """Verify StaticEvidenceUpload columns match design spec."""

    def test_source_id_is_biginteger(self):
        col = StaticEvidenceUpload.__table__.columns["source_id"]
        assert isinstance(col.type, BigInteger) or col.type.__class__.__name__ == "BigInteger"

    def test_source_id_has_cascade_delete(self):
        col = StaticEvidenceUpload.__table__.columns["source_id"]
        fk = list(col.foreign_keys)[0]
        assert fk.ondelete == "CASCADE", "source_id FK should CASCADE on delete"

    def test_uploaded_by_has_set_null_delete(self):
        col = StaticEvidenceUpload.__table__.columns["uploaded_by"]
        fk = list(col.foreign_keys)[0]
        assert fk.ondelete == "SET NULL", "uploaded_by FK should SET NULL on delete"

    def test_processed_at_has_timezone(self):
        col = StaticEvidenceUpload.__table__.columns["processed_at"]
        assert col.type.timezone is True

    def test_created_at_has_timezone_and_server_default(self):
        col = StaticEvidenceUpload.__table__.columns["created_at"]
        assert col.type.timezone is True
        assert col.server_default is not None

    def test_updated_at_has_timezone_and_server_default(self):
        col = StaticEvidenceUpload.__table__.columns["updated_at"]
        assert col.type.timezone is True
        assert col.server_default is not None
