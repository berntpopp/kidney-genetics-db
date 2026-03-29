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

        data: dict[str, Any] = response.json()
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
        Full workflow: create deposition -> upload export -> publish -> return DOI.

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
