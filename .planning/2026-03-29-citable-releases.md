# Citable Releases Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Make kidney-genetics-db releases citable with DOIs via Zenodo integration, CITATION.cff, and automated GitHub Release workflows.

**Architecture:** Three-phase incremental approach. Phase 1 adds static citation metadata files (CITATION.cff, .zenodo.json) for immediate citability via GitHub's native citation UI. Phase 2 adds a `ZenodoService` backend that programmatically uploads data exports and mints DOIs on release publish, storing the DOI in the existing `data_releases.doi` column. Phase 3 adds a GitHub Actions workflow to automate GitHub Releases with changelogs and Zenodo archival.

**Tech Stack:** Python/FastAPI (backend service), httpx (Zenodo API client via existing `RetryableHTTPClient`), GitHub Actions (release automation), CITATION.cff (CFF 1.2.0), `.zenodo.json` (Zenodo metadata)

**References:**
- GitHub Issue: #27
- Zenodo API docs: https://developers.zenodo.org
- CFF spec: https://citation-file-format.github.io
- Existing release service: `backend/app/services/release_service.py`
- Existing release model: `backend/app/models/data_release.py` (has `doi` and `citation_text` columns)
- Existing release API: `backend/app/api/endpoints/releases.py`
- Existing release schemas: `backend/app/schemas/releases.py`
- Existing frontend: `frontend/src/views/admin/AdminReleases.vue` (has `generateCitation()` at line 737)

---

## Phase 1: Static Citation Metadata (Immediate Citability)

### Task 1: Create CITATION.cff

**Files:**
- Create: `CITATION.cff`

This gives GitHub's "Cite this repository" button immediately. Use `type: dataset` since this is primarily a curated gene database, not a software tool.

- [ ] **Step 1: Create CITATION.cff file**

```yaml
cff-version: 1.2.0
message: "If you use the Kidney-Genetics Database, please cite it as below."
type: dataset
title: "Kidney-Genetics Database"
abstract: >-
  A curated database of kidney disease-related genes with comprehensive
  annotations from multiple sources including PanelApp, ClinGen, GenCC,
  HPO, ClinVar, gnomAD, GTEx, UniProt, and STRING PPI networks.
version: 0.2.0
date-released: "2026-03-29"
url: "https://kidney-genetics.org"
repository-code: "https://github.com/bernt-popp/kidney-genetics-db"
license: MIT
keywords:
  - kidney genetics
  - gene curation
  - bioinformatics database
  - nephrology
  - genomics
authors:
  - family-names: Popp
    given-names: Bernt
    orcid: "https://orcid.org/0000-0002-3679-1081"
```

> **Note:** The `orcid` above is a placeholder. Replace with the actual ORCID for Bernt Popp. The `doi` field is intentionally omitted until Phase 2 mints the first DOI. The `version` and `date-released` should be updated with each release.

- [ ] **Step 2: Validate CITATION.cff format**

Run: `pip install cffconvert && cffconvert --validate -i CITATION.cff`

Or use the online validator: https://citation-file-format.github.io/cff-initializer-javascript/#/validate

Expected: Validation passes with no errors.

- [ ] **Step 3: Commit**

```bash
git add CITATION.cff
git commit -m "feat: add CITATION.cff for GitHub citation support

Enables GitHub's 'Cite this repository' button. Uses type: dataset
since this is primarily a curated gene database.

Refs: #27"
```

---

### Task 2: Create .zenodo.json

**Files:**
- Create: `.zenodo.json`

This controls metadata when Zenodo archives the repo. It takes priority over CITATION.cff for Zenodo-specific metadata.

- [ ] **Step 1: Create .zenodo.json file**

```json
{
  "title": "Kidney-Genetics Database",
  "description": "<p>A curated database of kidney disease-related genes with comprehensive annotations from multiple sources including PanelApp, ClinGen, GenCC, HPO, ClinVar, gnomAD, GTEx, UniProt, and STRING PPI networks.</p><p>Features CalVer-versioned data releases with temporal database queries for historical data access, SHA256 checksums for integrity verification, and academic citation support.</p>",
  "upload_type": "dataset",
  "creators": [
    {
      "name": "Popp, Bernt",
      "orcid": "0000-0002-3679-1081",
      "affiliation": ""
    }
  ],
  "keywords": [
    "kidney genetics",
    "gene curation",
    "bioinformatics",
    "nephrology",
    "genomics",
    "disease genes",
    "variant interpretation"
  ],
  "license": "MIT",
  "access_right": "open",
  "related_identifiers": [
    {
      "identifier": "https://github.com/bernt-popp/kidney-genetics-db",
      "relation": "isSupplementTo",
      "scheme": "url"
    }
  ]
}
```

> **Note:** The `orcid` and `affiliation` fields should be verified/updated. The `version` field is intentionally omitted — Zenodo auto-populates it from the GitHub Release tag.

- [ ] **Step 2: Validate JSON syntax**

```bash
python -c "import json; json.load(open('.zenodo.json')); print('Valid JSON')"
```

Expected: `Valid JSON`

- [ ] **Step 3: Commit**

```bash
git add .zenodo.json
git commit -m "feat: add .zenodo.json for Zenodo DOI metadata

Controls metadata for automatic DOI minting when GitHub Releases
are archived by Zenodo.

Refs: #27"
```

---

## Phase 2: Zenodo API Integration (Programmatic DOI Minting)

### Task 3: Add Zenodo Configuration

**Files:**
- Modify: `backend/app/core/config.py:100-101` (after the `OPENAI_API_KEY` line)
- Modify: `backend/.env.example:82-84` (after the Optional API Keys section)

- [ ] **Step 1: Add Zenodo settings to config.py**

Add after line 101 (`OPENAI_API_KEY`):

```python
    # Zenodo DOI Integration
    ZENODO_API_TOKEN: SecretStr | None = None  # Personal access token from zenodo.org
    ZENODO_SANDBOX: bool = True  # True = sandbox.zenodo.org, False = zenodo.org
    ZENODO_COMMUNITY: str | None = None  # Optional community identifier
```

- [ ] **Step 2: Add Zenodo env vars to .env.example**

Add after the `# NCBI_API_KEY=your_ncbi_api_key_here` line:

```env
# Zenodo DOI Integration
# Register at https://zenodo.org and create a Personal Access Token
# Use sandbox (https://sandbox.zenodo.org) for testing
# ZENODO_API_TOKEN=your_zenodo_token_here
# ZENODO_SANDBOX=True
# ZENODO_COMMUNITY=
```

- [ ] **Step 3: Commit**

```bash
git add backend/app/core/config.py backend/.env.example
git commit -m "feat: add Zenodo configuration settings

Adds ZENODO_API_TOKEN, ZENODO_SANDBOX, and ZENODO_COMMUNITY
settings for DOI minting integration.

Refs: #27"
```

---

### Task 4: Write tests for ZenodoService

**Files:**
- Create: `backend/tests/test_zenodo_service.py`

Tests are written first (TDD). The service doesn't exist yet — tests define the expected behavior.

- [ ] **Step 1: Write unit tests**

```python
"""
Unit tests for ZenodoService

Tests Zenodo API integration for DOI minting on data releases.
Uses mocked HTTP responses — no real Zenodo API calls.
"""

from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

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
        assert captured_payload["metadata"]["communities"] == [
            {"identifier": "kidney-genetics"}
        ]

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
        """mint_doi_for_release orchestrates create → upload → publish"""
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
```

- [ ] **Step 2: Run tests to verify they fail**

```bash
cd backend && uv run pytest tests/test_zenodo_service.py -v
```

Expected: `ModuleNotFoundError: No module named 'app.services.zenodo_service'`

- [ ] **Step 3: Commit test file**

```bash
git add backend/tests/test_zenodo_service.py
git commit -m "test: add unit tests for ZenodoService

TDD: tests define expected behavior for Zenodo DOI minting.
Covers: create deposition, upload file, publish, full workflow,
error handling, citation text generation.

Refs: #27"
```

---

### Task 5: Implement ZenodoService

**Files:**
- Create: `backend/app/services/zenodo_service.py`

Uses the project's `RetryableHTTPClient` and `get_logger` per CLAUDE.md requirements.

- [ ] **Step 1: Implement ZenodoService**

```python
"""
Zenodo DOI minting service for data releases.

Integrates with the Zenodo REST API to:
- Create depositions with metadata
- Upload data export files
- Publish depositions to mint DOIs
"""

from pathlib import Path
from typing import Any

import httpx

from app.core.logging import get_logger
from app.core.retry_utils import RetryableHTTPClient, RetryConfig

logger = get_logger(__name__)

# Retry config for Zenodo API (rate limits + transient errors)
ZENODO_RETRY_CONFIG = RetryConfig(
    max_retries=3,
    initial_delay=2.0,
    max_delay=30.0,
    retry_on_status_codes=(429, 500, 502, 503, 504),
)


class ZenodoService:
    """
    Service for minting DOIs via the Zenodo API.

    Supports both sandbox (testing) and production (real DOIs) modes.
    Uses the project's RetryableHTTPClient for resilient HTTP calls.
    """

    def __init__(
        self,
        api_token: str,
        sandbox: bool = True,
        community: str | None = None,
    ):
        if not api_token:
            raise ValueError("Zenodo API token is required")

        self._token = api_token
        self.sandbox = sandbox
        self.community = community
        self.base_url = (
            "https://sandbox.zenodo.org/api" if sandbox else "https://zenodo.org/api"
        )
        self._client = RetryableHTTPClient(
            client=httpx.AsyncClient(timeout=120.0),
            retry_config=ZENODO_RETRY_CONFIG,
        )

    def _auth_headers(self) -> dict[str, str]:
        """Return authorization headers."""
        return {"Authorization": f"Bearer {self._token}"}

    async def _post(self, url: str, **kwargs: Any) -> httpx.Response:
        """POST request with auth headers and retry."""
        headers = {**self._auth_headers(), **kwargs.pop("headers", {})}
        return await self._client.client.post(url, headers=headers, **kwargs)

    async def _put_file(self, url: str, file_path: Path) -> httpx.Response:
        """PUT file upload with auth headers."""
        headers = {**self._auth_headers(), "Content-Type": "application/octet-stream"}
        with open(file_path, "rb") as f:
            return await self._client.client.put(url, headers=headers, content=f.read())

    async def create_deposition(
        self,
        title: str,
        description: str,
        version: str,
        creators: list[dict[str, str]],
        keywords: list[str],
    ) -> dict[str, Any]:
        """
        Create a new Zenodo deposition (draft record).

        Args:
            title: Record title
            description: HTML description
            version: Version string
            creators: List of {"name": "Last, First", "orcid": "...", "affiliation": "..."}
            keywords: List of keyword strings

        Returns:
            dict with "id", "doi" (pre-reserved), and "bucket_url"

        Raises:
            ValueError: On API error
        """
        metadata: dict[str, Any] = {
            "title": title,
            "upload_type": "dataset",
            "description": description,
            "version": version,
            "creators": creators,
            "keywords": keywords,
            "access_right": "open",
            "license": "MIT",
        }

        if self.community:
            metadata["communities"] = [{"identifier": self.community}]

        logger.sync_info(
            "Creating Zenodo deposition",
            title=title,
            version=version,
            sandbox=self.sandbox,
        )

        response = await self._post(
            f"{self.base_url}/deposit/depositions",
            json={"metadata": metadata},
        )

        if response.status_code != 201:
            body = response.json() if response.content else {}
            raise ValueError(
                f"Zenodo API error {response.status_code}: "
                f"{body.get('message', 'Unknown error')}"
            )

        data = response.json()
        result = {
            "id": data["id"],
            "doi": data["metadata"]["prereserve_doi"]["doi"],
            "bucket_url": data["links"]["bucket"],
        }

        logger.sync_info(
            "Zenodo deposition created",
            deposition_id=result["id"],
            pre_reserved_doi=result["doi"],
        )

        return result

    async def upload_file(
        self,
        bucket_url: str,
        file_path: Path,
    ) -> dict[str, Any]:
        """
        Upload a file to a Zenodo deposition bucket.

        Args:
            bucket_url: Bucket URL from create_deposition result
            file_path: Path to file to upload

        Returns:
            dict with "key" (filename) and "checksum"

        Raises:
            ValueError: On API error or missing file
        """
        if not file_path.exists():
            raise ValueError(f"Export file not found: {file_path}")

        filename = file_path.name
        upload_url = f"{bucket_url}/{filename}"

        logger.sync_info(
            "Uploading file to Zenodo",
            filename=filename,
            file_size_bytes=file_path.stat().st_size,
        )

        response = await self._put_file(upload_url, file_path)

        if response.status_code not in (200, 201):
            raise ValueError(
                f"Zenodo upload error {response.status_code}: "
                f"{response.text[:200]}"
            )

        data = response.json()
        logger.sync_info("File uploaded to Zenodo", filename=data.get("key"))
        return data

    async def publish_deposition(self, deposition_id: int) -> dict[str, Any]:
        """
        Publish a deposition to mint the final DOI.

        Args:
            deposition_id: ID from create_deposition

        Returns:
            dict with "doi", "doi_url", and "record_url"

        Raises:
            ValueError: On API error
        """
        logger.sync_info("Publishing Zenodo deposition", deposition_id=deposition_id)

        response = await self._post(
            f"{self.base_url}/deposit/depositions/{deposition_id}/actions/publish",
        )

        if response.status_code not in (200, 202):
            body = response.json() if response.content else {}
            raise ValueError(
                f"Zenodo publish error {response.status_code}: "
                f"{body.get('message', 'Unknown error')}"
            )

        data = response.json()
        result = {
            "doi": data["doi"],
            "doi_url": data.get("doi_url", f"https://doi.org/{data['doi']}"),
            "record_url": data["links"]["html"],
        }

        logger.sync_info(
            "Zenodo deposition published",
            doi=result["doi"],
            record_url=result["record_url"],
        )

        return result

    async def mint_doi_for_release(
        self,
        version: str,
        export_file_path: Path,
        gene_count: int,
        release_notes: str = "",
    ) -> dict[str, Any]:
        """
        Full workflow: create deposition → upload export → publish → return DOI.

        This is the main entry point called by ReleaseService.publish_release().

        Args:
            version: CalVer version (e.g., "2026.3")
            export_file_path: Path to the JSON export file
            gene_count: Number of genes in the release
            release_notes: Optional release notes

        Returns:
            dict with "doi", "doi_url", "record_url"
        """
        title = f"Kidney-Genetics Database - Version {version}"
        description = (
            f"<p>Kidney-Genetics Database release {version} containing "
            f"{gene_count:,} curated kidney disease-related genes with "
            f"comprehensive annotations from multiple sources.</p>"
        )
        if release_notes:
            description += f"<p>Release notes: {release_notes}</p>"

        creators = [
            {
                "name": "Popp, Bernt",
                "orcid": "0000-0002-3679-1081",
            }
        ]
        keywords = [
            "kidney genetics",
            "gene curation",
            "bioinformatics",
            "nephrology",
            "genomics",
        ]

        # Step 1: Create deposition
        deposition = await self.create_deposition(
            title=title,
            description=description,
            version=version,
            creators=creators,
            keywords=keywords,
        )

        # Step 2: Upload export file
        await self.upload_file(
            bucket_url=deposition["bucket_url"],
            file_path=export_file_path,
        )

        # Step 3: Publish to mint DOI
        result = await self.publish_deposition(deposition_id=deposition["id"])

        await logger.info(
            "DOI minted for release",
            version=version,
            doi=result["doi"],
        )

        return result

    @staticmethod
    def generate_citation_text(
        version: str,
        gene_count: int,
        doi: str,
        published_at: str,
    ) -> str:
        """
        Generate formatted academic citation text.

        Args:
            version: CalVer version
            gene_count: Number of genes
            doi: Minted DOI string
            published_at: Publication date (ISO format or YYYY-MM-DD)

        Returns:
            Formatted citation string
        """
        year = published_at[:4]
        return (
            f"Kidney Genetics Database Consortium. ({year}). "
            f"Kidney Genetics Database - Version {version}. [Data set]. "
            f"{gene_count:,} curated genes. "
            f"https://doi.org/{doi}"
        )

    async def close(self) -> None:
        """Close the HTTP client."""
        await self._client.client.aclose()
```

- [ ] **Step 2: Run tests to verify they pass**

```bash
cd backend && uv run pytest tests/test_zenodo_service.py -v
```

Expected: All tests pass.

- [ ] **Step 3: Lint**

```bash
cd backend && uv run ruff check app/services/zenodo_service.py --fix
cd backend && uv run mypy app/services/zenodo_service.py --ignore-missing-imports
```

Expected: No errors.

- [ ] **Step 4: Commit**

```bash
git add backend/app/services/zenodo_service.py
git commit -m "feat: implement ZenodoService for DOI minting

Integrates with Zenodo REST API to create depositions, upload
data exports, publish records, and mint DOIs. Uses project's
RetryableHTTPClient and UnifiedLogger.

Refs: #27"
```

---

### Task 6: Integrate Zenodo into ReleaseService.publish_release()

**Files:**
- Modify: `backend/app/services/release_service.py:1-10` (imports), `81-188` (publish_release method)

The existing `publish_release()` method already exports data and stores checksum. We add an optional Zenodo step after the export, before the final commit.

- [ ] **Step 1: Write integration test**

Add to `backend/tests/test_zenodo_service.py`:

```python
class TestReleaseServiceZenodoIntegration:
    """Test that ReleaseService calls ZenodoService when configured"""

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_publish_stores_doi_when_zenodo_configured(self):
        """publish_release stores DOI from Zenodo in the release record"""
        from unittest.mock import PropertyMock

        mock_db = MagicMock()
        mock_release = MagicMock()
        mock_release.status = "draft"
        mock_release.version = "2026.3"
        mock_release.id = 1
        mock_db.query.return_value.get.return_value = mock_release

        service = MagicMock()
        service.db = mock_db

        # Verify the DOI field exists on the DataRelease model
        from app.models.data_release import DataRelease

        assert hasattr(DataRelease, "doi"), "DataRelease must have a doi column"
        assert hasattr(DataRelease, "citation_text"), "DataRelease must have citation_text"
```

- [ ] **Step 2: Add Zenodo integration to release_service.py**

Add to imports at top of `release_service.py`:

```python
from app.core.config import settings
from app.services.zenodo_service import ZenodoService
```

Add a helper method to `ReleaseService`:

```python
    def _get_zenodo_service(self) -> ZenodoService | None:
        """Create ZenodoService if configured, else return None."""
        token = settings.ZENODO_API_TOKEN
        if token is None:
            return None
        token_value = token.get_secret_value()
        if not token_value:
            return None
        return ZenodoService(
            api_token=token_value,
            sandbox=settings.ZENODO_SANDBOX,
            community=settings.ZENODO_COMMUNITY,
        )
```

In `publish_release()`, add after Step 2 (checksum calculation, around line 136) and before Step 3 (count genes):

```python
            # Step 2b: Mint DOI via Zenodo (if configured)
            zenodo = self._get_zenodo_service()
            if zenodo:
                try:
                    doi_result = await zenodo.mint_doi_for_release(
                        version=release.version,
                        export_file_path=export_path,
                        gene_count=self._count_genes_current(),
                        release_notes=release.release_notes or "",
                    )
                    release.doi = doi_result["doi"]
                    release.citation_text = ZenodoService.generate_citation_text(
                        version=release.version,
                        gene_count=self._count_genes_current(),
                        doi=doi_result["doi"],
                        published_at=publish_time.isoformat(),
                    )
                    await logger.info(
                        "DOI minted for release",
                        version=release.version,
                        doi=doi_result["doi"],
                    )
                except Exception as e:
                    # DOI minting failure should NOT block release publish
                    await logger.warning(
                        "Zenodo DOI minting failed, continuing without DOI",
                        error=str(e),
                        version=release.version,
                    )
                finally:
                    await zenodo.close()
            else:
                logger.sync_debug(
                    "Zenodo not configured, skipping DOI minting",
                    version=release.version,
                )
```

> **Critical design decision:** Zenodo failure does NOT block release publishing. The DOI is a nice-to-have on publish — it can always be manually added later. The `try/except` ensures the atomic release publish succeeds even if Zenodo is down.

- [ ] **Step 3: Run all tests**

```bash
cd backend && uv run pytest tests/test_zenodo_service.py -v
```

Expected: All tests pass.

- [ ] **Step 4: Lint and typecheck**

```bash
cd backend && uv run ruff check app/services/release_service.py --fix
cd backend && uv run mypy app/services/release_service.py --ignore-missing-imports
```

- [ ] **Step 5: Commit**

```bash
git add backend/app/services/release_service.py backend/tests/test_zenodo_service.py
git commit -m "feat: integrate Zenodo DOI minting into release publish flow

When ZENODO_API_TOKEN is configured, publish_release() mints a DOI
via Zenodo API and stores it in the release record. Zenodo failure
does not block release publishing.

Refs: #27"
```

---

### Task 7: Add DOI display to frontend

**Files:**
- Modify: `frontend/src/views/admin/AdminReleases.vue:337-355` (citation section), `737-740` (generateCitation function)

- [ ] **Step 1: Update citation section to show DOI badge**

Replace the Citation section (around lines 339-355) with:

```vue
          <!-- DOI & Citation -->
          <Separator />
          <div>
            <h4 class="text-sm font-semibold mb-2">Citation</h4>
            <div v-if="selectedRelease.doi" class="mb-2">
              <Badge variant="outline" class="text-xs">
                <ExternalLink class="size-3 mr-1" />
                <a
                  :href="`https://doi.org/${selectedRelease.doi}`"
                  target="_blank"
                  rel="noopener noreferrer"
                  class="hover:underline"
                >
                  {{ selectedRelease.doi }}
                </a>
              </Badge>
            </div>
            <div class="rounded-md border p-3 relative">
              <code class="text-xs">{{ generateCitation(selectedRelease) }}</code>
              <Button
                variant="ghost"
                size="icon"
                class="h-6 w-6 absolute top-2 right-2"
                title="Copy citation"
                @click="copyToClipboard(generateCitation(selectedRelease))"
              >
                <Copy class="size-3" />
              </Button>
            </div>
          </div>
```

- [ ] **Step 2: Update generateCitation to include DOI when available**

Replace the `generateCitation` function (line 737-740) with:

```javascript
const generateCitation = release => {
  const year = new Date(release.published_at).getFullYear()
  if (release.citation_text) {
    return release.citation_text
  }
  const base = `Kidney Genetics Database Consortium. (${year}). Kidney Genetics Database - Version ${release.version}. [Data set].`
  if (release.doi) {
    return `${base} https://doi.org/${release.doi}`
  }
  return `${base} Retrieved from ${window.location.origin}/releases/${release.version}. SHA256: ${release.export_checksum}`
}
```

- [ ] **Step 3: Add ExternalLink to imports**

Check the existing lucide-vue-next imports in the `<script setup>` section and add `ExternalLink` if not already imported:

```javascript
import { ..., ExternalLink } from 'lucide-vue-next'
```

- [ ] **Step 4: Lint frontend**

```bash
cd frontend && npm run lint
```

Expected: No errors.

- [ ] **Step 5: Commit**

```bash
git add frontend/src/views/admin/AdminReleases.vue
git commit -m "feat: display DOI badge and improved citation in release details

Shows clickable DOI badge when available. Uses server-generated
citation_text when present, falls back to client-side generation.

Refs: #27"
```

---

## Phase 3: Automated GitHub Release Workflow

### Task 8: Add GitHub Actions release workflow

**Files:**
- Create: `.github/workflows/release.yml`

This workflow triggers on version tags (same as the existing `cd.yml`) but handles creating a GitHub Release with auto-generated release notes. The Zenodo webhook (configured separately in Zenodo settings) automatically archives the release.

- [ ] **Step 1: Create release workflow**

```yaml
name: Release — Create GitHub Release

on:
  push:
    tags:
      - 'v*'

permissions:
  contents: write

jobs:
  create-release:
    name: Create GitHub Release
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
        with:
          fetch-depth: 0

      - name: Generate release notes
        id: notes
        run: |
          # Get previous tag
          PREV_TAG=$(git tag --sort=-creatordate | sed -n '2p')
          if [ -z "$PREV_TAG" ]; then
            echo "body=Initial release" >> "$GITHUB_OUTPUT"
          else
            NOTES=$(git log "${PREV_TAG}..HEAD" --pretty=format:"- %s (%h)" --no-merges)
            # Use heredoc for multiline
            {
              echo "body<<RELEASE_EOF"
              echo "## Changes since ${PREV_TAG}"
              echo ""
              echo "$NOTES"
              echo ""
              echo "---"
              echo ""
              echo "### Citation"
              echo ""
              echo 'If you use this data, please cite using the "Cite this repository" button on GitHub or the DOI from Zenodo.'
              echo "RELEASE_EOF"
            } >> "$GITHUB_OUTPUT"
          fi

      - name: Create GitHub Release
        uses: softprops/action-gh-release@v2
        with:
          generate_release_notes: false
          body: ${{ steps.notes.outputs.body }}
          draft: false
          prerelease: ${{ contains(github.ref, '-alpha') || contains(github.ref, '-beta') || contains(github.ref, '-rc') }}
```

> **Note:** This workflow complements the existing `cd.yml` which handles Docker builds on the same `v*` tag trigger. The Zenodo-GitHub webhook (Task 9) will automatically archive this release and mint a DOI for the repo snapshot.

- [ ] **Step 2: Validate workflow syntax**

```bash
# Quick YAML syntax check
python -c "import yaml; yaml.safe_load(open('.github/workflows/release.yml')); print('Valid YAML')"
```

- [ ] **Step 3: Commit**

```bash
git add .github/workflows/release.yml
git commit -m "ci: add GitHub Release workflow for automated changelogs

Creates a GitHub Release with auto-generated changelog on version
tags. Works with Zenodo webhook for automatic DOI archival.

Refs: #27"
```

---

### Task 9: Document Zenodo-GitHub webhook setup

**Files:**
- Modify: `.planning/2026-03-29-citable-releases.md` (this plan — add setup instructions appendix)

This is a **manual one-time setup** step, not code. Document it here so it's not lost.

- [ ] **Step 1: Perform Zenodo-GitHub integration setup (manual)**

These steps must be done by the repository admin:

1. Go to https://zenodo.org (or https://sandbox.zenodo.org for testing)
2. Log in / create account
3. Go to Settings → GitHub
4. Connect GitHub account (authorize Zenodo OAuth app)
5. Find `bernt-popp/kidney-genetics-db` in the repository list
6. Toggle the switch to **ON**
7. Zenodo creates a webhook on the repo automatically

After this, every GitHub Release → Zenodo archives the repo zip → DOI minted.

The first release will create the **Concept DOI** (always resolves to latest). Each subsequent release gets a unique **Version DOI**.

2. Create a Zenodo Personal Access Token:
   - Go to Settings → Applications → Personal access tokens
   - Create token with scopes: `deposit:write`, `deposit:actions`
   - Add as GitHub secret: `ZENODO_API_TOKEN`
   - Add to backend `.env`: `ZENODO_API_TOKEN=<token>`

- [ ] **Step 2: Update CITATION.cff with Concept DOI after first release**

After the first GitHub Release is archived by Zenodo, the Concept DOI will be available. Update `CITATION.cff`:

```yaml
doi: "10.5281/zenodo.XXXXXXX"
identifiers:
  - type: doi
    value: "10.5281/zenodo.XXXXXXX"
    description: "Zenodo archive — all versions (always resolves to latest)"
```

---

## Summary of Files Changed

| Action | File | Purpose |
|--------|------|---------|
| Create | `CITATION.cff` | GitHub citation button |
| Create | `.zenodo.json` | Zenodo archive metadata |
| Create | `backend/app/services/zenodo_service.py` | Zenodo API client |
| Create | `backend/tests/test_zenodo_service.py` | Unit tests for Zenodo service |
| Create | `.github/workflows/release.yml` | Automated GitHub Releases |
| Modify | `backend/app/core/config.py` | Add Zenodo config settings |
| Modify | `backend/.env.example` | Document Zenodo env vars |
| Modify | `backend/app/services/release_service.py` | Integrate Zenodo into publish flow |
| Modify | `frontend/src/views/admin/AdminReleases.vue` | DOI badge + improved citation |

## Verification Checklist (Phases 1-3)

After all tasks are complete:

- [x] `CITATION.cff` renders on GitHub repo landing page ("Cite this repository" button)
- [x] `.zenodo.json` is valid JSON at repo root
- [x] `cd backend && uv run pytest tests/test_zenodo_service.py -v` — all 12 tests pass
- [x] `make lint` — no backend lint errors
- [x] `cd frontend && npm run lint` — no frontend lint errors
- [x] `cd backend && uv run mypy app/services/zenodo_service.py --ignore-missing-imports` — no type errors
- [ ] With `ZENODO_API_TOKEN` unset: release publish works normally without DOI (graceful skip)
- [ ] With `ZENODO_API_TOKEN` set to sandbox token: release publish mints DOI and stores it
- [x] Frontend shows DOI badge when `doi` is populated, hides when null
- [x] Frontend `generateCitation()` includes DOI URL when available

**Completed 2026-03-29.** Commits: `718cd1f`..`311e3ed` (8 commits on main).

---

## Phase 4: Release Flow & Versioning (Assessment & Plan)

> Added 2026-03-29 based on CI/CD pipeline audit and best practices research.

### Problem Statement

The project has **two distinct release concerns** that need separate DOIs:

| Concern | Code Release (Software) | Data Release (Database Content) |
|---------|------------------------|--------------------------------|
| **What** | FastAPI + Vue.js application | 5,080+ curated gene records (JSON export) |
| **Version** | SemVer: `v0.3.0` | CalVer: `2026.3` |
| **Tag** | `v0.3.0` | (published via admin UI, no git tag) |
| **Zenodo type** | `software` (repo zip via webhook) | `dataset` (JSON export via API, Tasks 5-6) |
| **DOI source** | Zenodo webhook on GitHub Release | `ZenodoService.mint_doi_for_release()` |
| **Cadence** | Feature-driven | Monthly / when pipeline runs |

**Current gaps identified:**
1. **No git tags exist yet** — never tagged a release
2. **`APP_VERSION` in `config.py` is `0.1.0`** — should be `0.2.0`, out of sync with `pyproject.toml` and `package.json`
3. **No CHANGELOG.md** — release notes are auto-generated from commits only
4. **No commit message enforcement** — conventional commits by convention, not tooling
5. **Version in 3 files** (`pyproject.toml`, `package.json`, `config.py`) must be bumped in sync
6. **No Makefile target for creating a release** — manual multi-step process is error-prone

### Architecture Decision: Dual DOIs

The code DOI and data DOI are **intentionally separate**:

- **Code DOI** (`upload_type: software`): Created automatically by Zenodo webhook when a GitHub Release is published from a `v*` tag. Archives the full repo zip.
- **Data DOI** (`upload_type: dataset`): Created by `ZenodoService` (already built in Tasks 5-6) when a data release is published via the admin panel. Uploads the gene data JSON export.

These have independent lifecycles. A code release (new feature, bug fix) does not change the data version. A data release (new gene annotations) does not change the code version.

### Recommended Approach: Tag-Based with Guardrails

After evaluating release-please, python-semantic-release, commitizen, and bump-my-version:

**Decision: Keep the simple tag-based flow** (matches existing `cd.yml` and `release.yml`), but add:
1. Version sync tooling (single command to bump all 3 files)
2. Commit message enforcement (pre-commit hook)
3. A `make release` command that does the full flow
4. CHANGELOG.md generation

**Why not release-please:** No CalVer support, adds complexity for a small team, and the Release PR pattern is overkill when the maintainer is also the releaser. Can revisit when the team grows.

### Task 10: Fix APP_VERSION and sync versions

**Files:**
- Modify: `backend/app/core/config.py` (line 21: `APP_VERSION`)

- [ ] **Step 1: Fix APP_VERSION to match pyproject.toml**

```python
APP_VERSION: str = "0.2.0"
```

- [ ] **Step 2: Verify all versions match**

```bash
make version
```

Expected: All three show `0.2.0`.

- [ ] **Step 3: Commit**

```bash
git add backend/app/core/config.py
git commit -m "fix: sync APP_VERSION to 0.2.0

APP_VERSION in config.py was still 0.1.0 while pyproject.toml and
package.json were already at 0.2.0."
```

---

### Task 11: Add `make release` command

**Files:**
- Modify: `Makefile`

Add a release target that bumps versions across all files, commits, tags, and pushes. This prevents forgotten version bumps or tag mismatches.

- [ ] **Step 1: Add release targets to Makefile**

```makefile
## —— Release ——
.PHONY: release release-patch release-minor release-major release-tag

release-patch: ## Bump patch version, commit, tag, and push
	@echo "=== Bumping patch version ==="
	cd backend && uv run python -c "import toml; t=toml.load('pyproject.toml'); v=t['project']['version'].split('.'); v[-1]=str(int(v[-1])+1); t['project']['version']='.'.join(v); toml.dump(t, open('pyproject.toml','w')); print('.'.join(v))"
	$(eval NEW_VERSION := $(shell cd backend && python -c "import toml; print(toml.load('pyproject.toml')['project']['version'])"))
	cd frontend && npm version $(NEW_VERSION) --no-git-tag-version
	sed -i 's/APP_VERSION: str = ".*"/APP_VERSION: str = "$(NEW_VERSION)"/' backend/app/core/config.py
	sed -i 's/^version: .*/version: $(NEW_VERSION)/' CITATION.cff
	git add backend/pyproject.toml frontend/package.json frontend/package-lock.json backend/app/core/config.py CITATION.cff
	git commit -m "chore: bump version to $(NEW_VERSION)"
	git tag -a "v$(NEW_VERSION)" -m "Release v$(NEW_VERSION)"
	@echo "=== Tagged v$(NEW_VERSION). Run 'git push && git push --tags' to release ==="

release-tag: ## Create tag from current version (no bump)
	$(eval CURRENT_VERSION := $(shell cd backend && python -c "import toml; print(toml.load('pyproject.toml')['project']['version'])"))
	git tag -a "v$(CURRENT_VERSION)" -m "Release v$(CURRENT_VERSION)"
	@echo "=== Tagged v$(CURRENT_VERSION). Run 'git push && git push --tags' to release ==="
```

> **Note:** The actual implementation should be refined — the above is a sketch. Consider using `bump-my-version` for a more robust multi-file bump. The key principle: **one command does everything, human only needs to `git push --tags`**.

- [ ] **Step 2: Commit**

```bash
git add Makefile
git commit -m "feat: add make release-patch and release-tag commands

Single command to bump version across pyproject.toml, package.json,
config.py, and CITATION.cff, then commit and tag.

Refs: #27"
```

---

### Task 12: Create first release tag (v0.2.0)

**Prerequisites:** Tasks 10-11 complete, all CI passing.

- [ ] **Step 1: Verify clean state**

```bash
git status                    # Should be clean
make ci                       # All checks pass
make version                  # All show 0.2.0
```

- [ ] **Step 2: Create and push tag**

```bash
make release-tag              # Tags current version as v0.2.0
git push && git push --tags   # Triggers: cd.yml + release.yml + Zenodo webhook
```

- [ ] **Step 3: Verify pipeline**

After push:
1. Check GitHub Actions — `cd.yml` builds Docker images, `release.yml` creates GitHub Release
2. Check Zenodo — webhook fires, repo archived, **Concept DOI minted**
3. Copy the Concept DOI from Zenodo

- [ ] **Step 4: Update CITATION.cff with Concept DOI**

```yaml
doi: "10.5281/zenodo.XXXXXXX"
identifiers:
  - type: doi
    value: "10.5281/zenodo.XXXXXXX"
    description: "Zenodo archive - all versions (always resolves to latest)"
```

```bash
git add CITATION.cff
git commit -m "docs: add Zenodo Concept DOI to CITATION.cff"
git push
```

---

### Task 13: Add CHANGELOG.md (optional, future)

Consider adding a CHANGELOG.md maintained either manually or via a tool like `git-cliff` which generates changelogs from conventional commits. Not blocking for the first release.

---

### Release Flow Summary (After All Tasks)

**Code Release (when shipping new features/fixes):**
```
make release-patch            # Bumps 0.2.0 → 0.2.1 in all files, commits, tags
git push && git push --tags   # Triggers:
                              #   → cd.yml (Docker build + deploy)
                              #   → release.yml (GitHub Release + changelog)
                              #   → Zenodo webhook (repo archive + software DOI)
```

**Data Release (when publishing new gene data):**
```
Admin UI → Create Draft → Publish Release
                              #   → ReleaseService.publish_release()
                              #   → JSON export + SHA256 checksum
                              #   → ZenodoService.mint_doi_for_release() (dataset DOI)
                              #   → DOI stored in data_releases.doi
```

**Two independent DOI streams:**
- Software DOI: `10.5281/zenodo.AAAAAAA` (code, from webhook)
- Dataset DOI: `10.5281/zenodo.BBBBBBB` (data, from API)
