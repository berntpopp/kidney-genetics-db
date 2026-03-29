"""
Unit tests for ZenodoService

Tests Zenodo API integration for DOI minting on data releases.
Uses mocked HTTP responses — no real Zenodo API calls.
"""

from pathlib import Path
from unittest.mock import patch

import httpx
import pytest

from app.services.zenodo_service import ZenodoService


class TestZenodoService:
    """Test suite for ZenodoService"""

    @pytest.fixture
    def service(self):
        """Create a ZenodoService with sandbox config"""
        return ZenodoService(
            api_token="test-token-abc123",
            sandbox=True,
            community=None,
        )

    @pytest.fixture
    def service_with_community(self):
        """Create a ZenodoService with community config"""
        return ZenodoService(
            api_token="test-token-abc123",
            sandbox=True,
            community="kidney-genetics",
        )

    @pytest.mark.unit
    def test_base_url_sandbox(self, service):
        """Sandbox mode uses sandbox.zenodo.org"""
        assert service.base_url == "https://sandbox.zenodo.org/api"

    @pytest.mark.unit
    def test_base_url_production(self):
        """Production mode uses zenodo.org"""
        svc = ZenodoService(api_token="tok", sandbox=False, community=None)
        assert svc.base_url == "https://zenodo.org/api"

    @pytest.mark.unit
    def test_headers_include_token(self, service):
        """Auth headers include Bearer token"""
        headers = service._auth_headers()
        assert headers["Authorization"] == "Bearer test-token-abc123"

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_create_deposition_success(self, service):
        """create_deposition returns deposition ID and bucket URL"""
        mock_response = httpx.Response(
            201,
            json={
                "id": 12345,
                "links": {"bucket": "https://sandbox.zenodo.org/api/files/bucket-uuid"},
                "metadata": {"prereserve_doi": {"doi": "10.5281/zenodo.12345"}},
            },
            request=httpx.Request("POST", "https://sandbox.zenodo.org/api/deposit/depositions"),
        )
        with patch.object(service, "_post", return_value=mock_response):
            result = await service.create_deposition(
                title="Kidney-Genetics Database - Version 2026.3",
                description="Release 2026.3 with 5080 curated genes.",
                version="2026.3",
                creators=[{"name": "Popp, Bernt", "orcid": "0000-0002-3679-1081"}],
                keywords=["kidney genetics"],
            )
        assert result["id"] == 12345
        assert result["doi"] == "10.5281/zenodo.12345"
        assert "bucket" in result["bucket_url"]

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_create_deposition_with_community(self, service_with_community):
        """Deposition metadata includes community when configured"""
        captured_payload = {}

        async def mock_post(url, json=None, **kwargs):
            captured_payload.update(json or {})
            return httpx.Response(
                201,
                json={
                    "id": 99,
                    "links": {"bucket": "https://example.com/bucket"},
                    "metadata": {"prereserve_doi": {"doi": "10.5281/zenodo.99"}},
                },
                request=httpx.Request("POST", url),
            )

        with patch.object(service_with_community, "_post", side_effect=mock_post):
            await service_with_community.create_deposition(
                title="Test",
                description="Test",
                version="2026.1",
                creators=[{"name": "Test"}],
                keywords=["test"],
            )
        assert captured_payload["metadata"]["communities"] == [{"identifier": "kidney-genetics"}]

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_upload_file_success(self, service):
        """upload_file uploads file to bucket URL"""
        mock_response = httpx.Response(
            201,
            json={"key": "kidney-genetics-db_2026.3.json", "checksum": "md5:abc123"},
            request=httpx.Request("PUT", "https://example.com/bucket/file"),
        )
        tmp_file = Path("/tmp/test_export.json")
        tmp_file.write_text('{"test": true}')

        try:
            with patch.object(service, "_put_file", return_value=mock_response):
                result = await service.upload_file(
                    bucket_url="https://example.com/bucket",
                    file_path=tmp_file,
                )
            assert result["key"] == "kidney-genetics-db_2026.3.json"
        finally:
            tmp_file.unlink(missing_ok=True)

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_publish_deposition_success(self, service):
        """publish_deposition returns final DOI"""
        mock_response = httpx.Response(
            202,
            json={
                "id": 12345,
                "doi": "10.5281/zenodo.12345",
                "doi_url": "https://doi.org/10.5281/zenodo.12345",
                "links": {"html": "https://sandbox.zenodo.org/records/12345"},
            },
            request=httpx.Request("POST", "https://example.com/publish"),
        )
        with patch.object(service, "_post", return_value=mock_response):
            result = await service.publish_deposition(deposition_id=12345)
        assert result["doi"] == "10.5281/zenodo.12345"
        assert result["doi_url"] == "https://doi.org/10.5281/zenodo.12345"
        assert result["record_url"] == "https://sandbox.zenodo.org/records/12345"

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_create_deposition_api_error(self, service):
        """API errors raise ValueError with status and message"""
        mock_response = httpx.Response(
            400,
            json={"message": "Validation error", "errors": [{"field": "metadata.title"}]},
            request=httpx.Request("POST", "https://example.com"),
        )
        with patch.object(service, "_post", return_value=mock_response):
            with pytest.raises(ValueError, match="Zenodo API error 400"):
                await service.create_deposition(
                    title="", description="", version="", creators=[], keywords=[]
                )

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_mint_doi_for_release_full_workflow(self, service):
        """mint_doi_for_release orchestrates create -> upload -> publish"""
        with (
            patch.object(
                service,
                "create_deposition",
                return_value={
                    "id": 100,
                    "doi": "10.5281/zenodo.100",
                    "bucket_url": "https://example.com/bucket",
                },
            ) as mock_create,
            patch.object(
                service,
                "upload_file",
                return_value={"key": "file.json"},
            ) as mock_upload,
            patch.object(
                service,
                "publish_deposition",
                return_value={
                    "doi": "10.5281/zenodo.100",
                    "doi_url": "https://doi.org/10.5281/zenodo.100",
                    "record_url": "https://sandbox.zenodo.org/records/100",
                },
            ) as mock_publish,
        ):
            result = await service.mint_doi_for_release(
                version="2026.3",
                export_file_path=Path("/tmp/export.json"),
                gene_count=5080,
                release_notes="Monthly release",
            )

        mock_create.assert_called_once()
        mock_upload.assert_called_once()
        mock_publish.assert_called_once()
        assert result["doi"] == "10.5281/zenodo.100"
        assert result["doi_url"] == "https://doi.org/10.5281/zenodo.100"

    @pytest.mark.unit
    def test_service_requires_token(self):
        """ZenodoService raises if token is empty"""
        with pytest.raises(ValueError, match="API token"):
            ZenodoService(api_token="", sandbox=True, community=None)

    @pytest.mark.unit
    def test_generate_citation_text(self, service):
        """generate_citation_text produces formatted academic citation"""
        citation = service.generate_citation_text(
            version="2026.3",
            gene_count=5080,
            doi="10.5281/zenodo.12345",
            published_at="2026-03-15",
        )
        assert "2026.3" in citation
        assert "5,080" in citation or "5080" in citation
        assert "10.5281/zenodo.12345" in citation
        assert "Kidney Genetics Database" in citation


class TestReleaseServiceZenodoIntegration:
    """Test that ReleaseService calls ZenodoService when configured"""

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_data_release_model_has_doi_fields(self):
        """Verify the DataRelease model has doi and citation_text columns"""
        from app.models.data_release import DataRelease

        assert hasattr(DataRelease, "doi"), "DataRelease must have a doi column"
        assert hasattr(DataRelease, "citation_text"), "DataRelease must have citation_text"
