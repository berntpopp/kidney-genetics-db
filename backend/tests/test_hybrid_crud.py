"""
Tests for hybrid source CRUD functionality.

Covers file upload, deletion, and management endpoints for DiagnosticPanels
and Literature sources.
"""

import io
from datetime import datetime, timezone
from unittest.mock import AsyncMock, Mock, patch

import pytest
from fastapi import UploadFile
from sqlalchemy.orm import Session

from app.api.endpoints.ingestion import (
    delete_by_identifier,
    get_audit_trail,
    get_source_status,
    list_identifiers,
    list_uploads,
    soft_delete_upload,
    upload_evidence_file,
)
from app.core.exceptions import DataSourceError, ValidationError
from app.models.gene import Gene
from app.models.static_sources import (
    StaticEvidenceUpload,
    StaticSource,
    StaticSourceAudit,
)
from app.models.user import User


class TestUploadEndpoint:
    """Test file upload functionality."""

    @pytest.fixture
    def mock_db(self):
        """Create mock database session."""
        return Mock(spec=Session)

    @pytest.fixture
    def mock_user(self):
        """Create mock curator user."""
        return User(username="test_curator", role="curator")

    @pytest.fixture
    def mock_file(self):
        """Create mock upload file."""
        content = b'{"gene": "PKD1", "panel": "Test Panel"}'
        file_like = io.BytesIO(content)
        return UploadFile(filename="test_panel.json", file=file_like)

    @pytest.mark.asyncio
    async def test_upload_diagnostic_panels_merge_mode(self, mock_db, mock_user, mock_file):
        """Test uploading DiagnosticPanels file in merge mode."""
        with patch(
            "app.api.endpoints.ingestion.get_unified_source"
        ) as mock_source, patch(
            "app.api.endpoints.ingestion.normalize_genes_batch_async"
        ) as mock_normalize:
            # Setup mocks
            source_instance = Mock()
            source_instance.fetch_raw_data = AsyncMock(
                return_value={"PKD1": {"panels": ["Test Panel"]}}
            )
            source_instance.process_data = AsyncMock(
                return_value={"PKD1": {"panels": ["Test Panel"]}}
            )
            source_instance.store_evidence = AsyncMock(
                return_value={"created": 1, "merged": 0, "failed": 0, "filtered": 0}
            )
            source_instance._get_or_create_gene = AsyncMock(return_value=Mock(spec=Gene))
            mock_source.return_value = source_instance

            mock_normalize.return_value = {
                "PKD1": {"status": "normalized", "created": True, "hgnc_id": "HGNC:8827"}
            }

            # Execute
            result = await upload_evidence_file(
                source_name="DiagnosticPanels",
                file=mock_file,
                provider_name="TestProvider",
                mode="merge",
                db=mock_db,
                current_user=mock_user,
            )

            # Verify
            assert result["data"]["status"] == "success"
            assert result["data"]["source"] == "DiagnosticPanels"
            assert result["data"]["provider"] == "TestProvider"
            assert "storage_stats" in result["data"]
            assert result["data"]["storage_stats"]["created"] >= 0

    @pytest.mark.asyncio
    async def test_upload_replace_mode_deletes_existing(self, mock_db, mock_user, mock_file):
        """Test replace mode deletes existing data before upload."""
        with patch(
            "app.api.endpoints.ingestion.get_unified_source"
        ) as mock_source, patch(
            "app.api.endpoints.ingestion.get_source_manager"
        ) as mock_manager, patch(
            "app.api.endpoints.ingestion.normalize_genes_batch_async"
        ) as mock_normalize:
            # Setup mocks
            manager_instance = Mock()
            manager_instance.delete_by_identifier = AsyncMock(
                return_value={"deleted_evidence": 5}
            )
            mock_manager.return_value = manager_instance

            source_instance = Mock()
            source_instance.fetch_raw_data = AsyncMock(return_value={})
            source_instance.process_data = AsyncMock(return_value={})
            source_instance.store_evidence = AsyncMock(
                return_value={"created": 0, "merged": 0, "failed": 0, "filtered": 0}
            )
            mock_source.return_value = source_instance

            mock_normalize.return_value = {}

            # Mock savepoint
            mock_savepoint = Mock()
            mock_db.begin_nested.return_value = mock_savepoint

            # Execute
            result = await upload_evidence_file(
                source_name="DiagnosticPanels",
                file=mock_file,
                provider_name="TestProvider",
                mode="replace",
                db=mock_db,
                current_user=mock_user,
            )

            # Verify delete was called
            manager_instance.delete_by_identifier.assert_awaited_once_with(
                "TestProvider", "test_curator"
            )
            assert result["data"]["status"] == "success"

    @pytest.mark.asyncio
    async def test_upload_invalid_source_raises_error(self, mock_db, mock_user, mock_file):
        """Test uploading to invalid source raises DataSourceError."""
        with pytest.raises(DataSourceError) as exc_info:
            await upload_evidence_file(
                source_name="InvalidSource",
                file=mock_file,
                provider_name="Test",
                mode="merge",
                db=mock_db,
                current_user=mock_user,
            )

        assert "does not support file uploads" in str(exc_info.value)

    @pytest.mark.asyncio
    async def test_upload_invalid_mode_raises_error(self, mock_db, mock_user, mock_file):
        """Test uploading with invalid mode raises ValidationError."""
        with pytest.raises(ValidationError) as exc_info:
            await upload_evidence_file(
                source_name="DiagnosticPanels",
                file=mock_file,
                provider_name="Test",
                mode="invalid_mode",
                db=mock_db,
                current_user=mock_user,
            )

        assert "Mode must be 'merge' or 'replace'" in str(exc_info.value)

    @pytest.mark.asyncio
    async def test_upload_file_too_large_raises_error(self, mock_db, mock_user):
        """Test uploading file larger than 50MB raises ValidationError."""
        # Create large file (51MB)
        large_content = b"x" * (51 * 1024 * 1024)
        large_file = UploadFile(filename="large.json", file=io.BytesIO(large_content))

        with pytest.raises(ValidationError) as exc_info:
            await upload_evidence_file(
                source_name="DiagnosticPanels",
                file=large_file,
                provider_name="Test",
                mode="merge",
                db=mock_db,
                current_user=mock_user,
            )

        assert "File size exceeds 50MB limit" in str(exc_info.value)


class TestDeleteEndpoints:
    """Test deletion endpoints."""

    @pytest.fixture
    def mock_db(self):
        """Create mock database session."""
        return Mock(spec=Session)

    @pytest.fixture
    def mock_user(self):
        """Create mock curator user."""
        return User(username="test_curator", role="curator")

    @pytest.mark.asyncio
    async def test_delete_by_identifier_success(self, mock_db, mock_user):
        """Test successful deletion by identifier."""
        with patch("app.api.endpoints.ingestion.get_source_manager") as mock_manager:
            manager_instance = Mock()
            manager_instance.delete_by_identifier = AsyncMock(
                return_value={"deleted_evidence": 10, "affected_genes": 5}
            )
            mock_manager.return_value = manager_instance

            result = await delete_by_identifier(
                source_name="DiagnosticPanels",
                identifier="TestProvider",
                db=mock_db,
                current_user=mock_user,
            )

            assert result["data"]["source"] == "DiagnosticPanels"
            assert result["data"]["identifier"] == "TestProvider"
            assert result["data"]["deletion_stats"]["deleted_evidence"] == 10

    @pytest.mark.asyncio
    async def test_soft_delete_upload_success(self, mock_db, mock_user):
        """Test successful soft delete of upload record."""
        # Mock upload record
        upload_record = StaticEvidenceUpload(
            id=1,
            evidence_name="test_upload",
            file_hash="abc123",
            upload_status="completed",
        )

        # Mock static source
        static_source = StaticSource(id=1, source_name="DiagnosticPanels")

        mock_db.execute.return_value.scalar_one_or_none.return_value = upload_record
        mock_db.query.return_value.filter.return_value.first.return_value = static_source

        result = await soft_delete_upload(
            source_name="DiagnosticPanels",
            upload_id=1,
            db=mock_db,
            current_user=mock_user,
        )

        assert result["data"]["upload_id"] == 1
        assert result["data"]["status"] == "deleted"
        assert upload_record.upload_status == "deleted"


class TestListEndpoints:
    """Test list and query endpoints."""

    @pytest.fixture
    def mock_db(self):
        """Create mock database session."""
        return Mock(spec=Session)

    @pytest.mark.asyncio
    async def test_list_uploads(self, mock_db):
        """Test listing upload history."""
        # Mock static source
        static_source = StaticSource(id=1, source_name="DiagnosticPanels")
        mock_db.query.return_value.filter.return_value.first.return_value = static_source

        # Mock uploads
        mock_uploads = [
            StaticEvidenceUpload(
                id=1,
                source_id=1,
                evidence_name="upload1",
                file_hash="hash1",
                original_filename="file1.json",
                upload_status="completed",
                uploaded_by="user1",
                created_at=datetime.now(timezone.utc),
                gene_count=100,
                genes_normalized=95,
                genes_failed=5,
            )
        ]

        mock_db.execute.return_value.scalars.return_value.all.return_value = mock_uploads
        mock_db.execute.return_value.scalar.return_value = 1

        result = await list_uploads(
            source_name="DiagnosticPanels", limit=50, offset=0, db=mock_db
        )

        assert result["data"]["uploads"][0]["id"] == 1
        assert result["meta"]["total"] == 1

    @pytest.mark.asyncio
    async def test_get_audit_trail(self, mock_db):
        """Test getting audit trail."""
        # Mock static source
        static_source = StaticSource(id=1, source_name="Literature")
        mock_db.query.return_value.filter.return_value.first.return_value = static_source

        # Mock audit records
        mock_audits = [
            StaticSourceAudit(
                id=1,
                source_id=1,
                action="upload",
                user_id=1,
                performed_at=datetime.now(timezone.utc),
                changes={"file": "literature.json", "genes_processed": 50},
            )
        ]

        # Mock user lookup
        mock_db.execute.return_value.scalars.return_value.all.return_value = mock_audits
        mock_db.execute.return_value.scalar.return_value = 1
        mock_db.execute.return_value.scalar_one_or_none.return_value = "curator1"

        result = await get_audit_trail(
            source_name="Literature", limit=50, offset=0, db=mock_db
        )

        assert result["data"]["audit_records"][0]["action"] == "upload"
        assert result["meta"]["total"] == 1

    @pytest.mark.asyncio
    async def test_list_identifiers_diagnostic_panels(self, mock_db):
        """Test listing providers for DiagnosticPanels."""

        # Mock view query results
        mock_rows = [
            Mock(identifier="Provider1", gene_count=100, last_updated=datetime.now(timezone.utc)),
            Mock(identifier="Provider2", gene_count=50, last_updated=datetime.now(timezone.utc)),
        ]

        mock_db.execute.return_value.fetchall.return_value = mock_rows

        result = await list_identifiers(source_name="DiagnosticPanels", db=mock_db)

        assert len(result["data"]["identifiers"]) == 2
        assert result["data"]["identifiers"][0]["identifier"] == "Provider1"
        assert result["data"]["identifiers"][0]["gene_count"] == 100


class TestStatusEndpoint:
    """Test source status endpoint."""

    @pytest.fixture
    def mock_db(self):
        """Create mock database session."""
        return Mock(spec=Session)

    @pytest.mark.asyncio
    async def test_get_source_status(self, mock_db):
        """Test getting source status and statistics."""
        # Mock query results
        mock_result = Mock(evidence_records=250, unique_genes=150)
        mock_db.execute.return_value.first.return_value = mock_result

        # Mock evidence data for additional stats
        mock_evidence = [
            {"providers": ["Provider1", "Provider2"], "panels": ["Panel1"]},
            {"providers": ["Provider1"], "panels": ["Panel2", "Panel3"]},
        ]
        mock_db.execute.return_value.scalars.return_value.all.return_value = mock_evidence

        result = await get_source_status(source_name="DiagnosticPanels", db=mock_db)

        assert result["data"]["source"] == "DiagnosticPanels"
        assert result["data"]["evidence_records"] == 250
        assert result["data"]["unique_genes"] == 150
        assert result["data"]["supports_upload"] is True
        assert "sample_providers" in result["data"]


class TestEdgeCases:
    """Test edge cases and error handling."""

    @pytest.fixture
    def mock_db(self):
        """Create mock database session."""
        return Mock(spec=Session)

    @pytest.fixture
    def mock_user(self):
        """Create mock curator user."""
        return User(username="test_curator", role="curator")

    @pytest.mark.asyncio
    async def test_upload_without_provider_name_uses_filename(
        self, mock_db, mock_user
    ):
        """Test that missing provider name defaults to filename."""
        content = b'{"gene": "PKD1"}'
        test_file = UploadFile(filename="MyProvider.json", file=io.BytesIO(content))

        with patch(
            "app.api.endpoints.ingestion.get_unified_source"
        ) as mock_source, patch(
            "app.api.endpoints.ingestion.normalize_genes_batch_async"
        ) as mock_normalize:
            source_instance = Mock()
            source_instance.fetch_raw_data = AsyncMock(return_value={})
            source_instance.process_data = AsyncMock(return_value={})
            source_instance.store_evidence = AsyncMock(
                return_value={"created": 0, "merged": 0, "failed": 0, "filtered": 0}
            )
            mock_source.return_value = source_instance
            mock_normalize.return_value = {}

            result = await upload_evidence_file(
                source_name="DiagnosticPanels",
                file=test_file,
                provider_name=None,  # No provider name specified
                mode="merge",
                db=mock_db,
                current_user=mock_user,
            )

            # Verify provider was set to filename without extension
            assert result["data"]["provider"] == "MyProvider"

    @pytest.mark.asyncio
    async def test_soft_delete_nonexistent_upload_raises_error(self, mock_db, mock_user):
        """Test soft deleting nonexistent upload raises ValidationError."""
        mock_db.execute.return_value.scalar_one_or_none.return_value = None

        with pytest.raises(ValidationError) as exc_info:
            await soft_delete_upload(
                source_name="DiagnosticPanels",
                upload_id=999,
                db=mock_db,
                current_user=mock_user,
            )

        assert "Upload 999 not found" in str(exc_info.value)

    @pytest.mark.asyncio
    async def test_delete_with_rollback_on_error(self, mock_db, mock_user):
        """Test that delete operation rolls back on error."""
        with patch("app.api.endpoints.ingestion.get_source_manager") as mock_manager:
            manager_instance = Mock()
            manager_instance.delete_by_identifier = AsyncMock(
                side_effect=Exception("Database error")
            )
            mock_manager.return_value = manager_instance

            with pytest.raises(DataSourceError):
                await delete_by_identifier(
                    source_name="DiagnosticPanels",
                    identifier="TestProvider",
                    db=mock_db,
                    current_user=mock_user,
                )

            # Verify rollback was called
            mock_db.rollback.assert_called_once()
