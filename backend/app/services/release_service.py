"""
Release Service for CalVer data releases

Handles creating and publishing versioned, immutable JSON data snapshots.
"""

import asyncio
import hashlib
import json
import os
import re
import threading
from collections.abc import Iterable, Iterator
from datetime import datetime, timezone
from functools import lru_cache
from pathlib import Path
from typing import Any, cast

from sqlalchemy import text
from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.database import get_thread_pool_executor
from app.core.logging import get_logger
from app.models.data_release import DataRelease
from app.services.zenodo_service import ZenodoService

logger = get_logger(__name__)


GENE_ID_FIELDS = ("approved_symbol", "hgnc_id", "aliases")
_sidecar_lock = threading.Lock()
_failed_snapshots: set[tuple[str, str | None]] = set()


class ReleaseSnapshotError(Exception):
    """A published release's export snapshot is missing or does not match its checksum."""


def _sidecar_path(export_path: str | Path) -> Path:
    """Small identifiers-only file served by the release genes endpoint."""
    return Path(export_path).with_suffix(".genes.json")


def _write_sidecar(export_path: str | Path, genes: Iterable[dict[str, Any]]) -> None:
    sidecar = _sidecar_path(export_path)
    tmp = sidecar.with_suffix(".tmp")
    with open(tmp, "w", encoding="utf-8") as f:
        json.dump([{k: g[k] for k in GENE_ID_FIELDS} for g in genes], f, ensure_ascii=False)
    os.replace(tmp, sidecar)


def _iter_export_genes(export_path: str | Path) -> Iterator[dict[str, Any]]:
    """Stream gene objects from a full export without loading the whole file."""
    decoder = json.JSONDecoder()
    marker = '"genes": ['
    with open(export_path, encoding="utf-8") as f:
        buf = ""
        while marker not in buf:
            chunk = f.read(1 << 16)
            if not chunk:
                raise ValueError("export has no genes array")
            buf += chunk
        buf = buf[buf.index(marker) + len(marker) :]
        while True:
            buf = buf.lstrip(" \t\r\n,")
            if buf.startswith("]"):
                return
            try:
                gene, end = decoder.raw_decode(buf)
            except json.JSONDecodeError:
                chunk = f.read(1 << 20)
                if not chunk:
                    raise
                buf += chunk
                continue
            yield gene
            buf = buf[end:]


@lru_cache(maxsize=8)
def _read_sidecar(sidecar: Path) -> tuple[dict[str, Any], ...]:
    with open(sidecar, encoding="utf-8") as f:
        return tuple(json.load(f))


def _load_release_genes(export_path: str, checksum: str | None) -> tuple[dict[str, Any], ...]:
    """Release gene identifiers, served from the sidecar.

    Releases published before the sidecar existed get it built once from the
    verified export (chunked checksum, streamed parse); the export is never
    modified. Failures are remembered so bad snapshots are not re-read per request.
    """
    sidecar = _sidecar_path(export_path)
    if not sidecar.exists():
        with _sidecar_lock:
            if (export_path, checksum) in _failed_snapshots:
                raise ReleaseSnapshotError(export_path)
            if not sidecar.exists():
                try:
                    if checksum and ReleaseService._calculate_checksum(export_path) != checksum:
                        raise ReleaseSnapshotError(f"checksum mismatch: {export_path}")
                    _write_sidecar(export_path, _iter_export_genes(export_path))
                except (OSError, ValueError, KeyError) as e:
                    _failed_snapshots.add((export_path, checksum))
                    raise ReleaseSnapshotError(export_path) from e
                except ReleaseSnapshotError:
                    _failed_snapshots.add((export_path, checksum))
                    raise
    return _read_sidecar(sidecar)


# CalVer validation pattern (YYYY.MM format)
CALVER_PATTERN = re.compile(r"^\d{4}\.\d{1,2}$")


class ReleaseService:
    """
    Service for managing CalVer data releases.

    Features:
    - Thread pool for non-blocking file I/O
    - Automatic checksum calculation
    - Export to JSON with metadata
    """

    def __init__(self, db_session: Session):
        self.db: Session = db_session
        self._executor = get_thread_pool_executor()
        self.export_dir = Path("exports")

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

    async def create_release(
        self, version: str, user_id: int, release_notes: str = ""
    ) -> DataRelease:
        """
        Create a draft release.

        Args:
            version: CalVer version string (e.g., "2025.10")
            user_id: ID of user creating the release
            release_notes: Optional release notes

        Returns:
            DataRelease: Created draft release

        Raises:
            ValueError: If version format is invalid or already exists
        """
        await logger.info("Creating draft release", version=version, user_id=user_id)

        # Validate CalVer format
        if not CALVER_PATTERN.match(version):
            raise ValueError(f"Version must be CalVer format YYYY.MM, got: {version}")

        # Check if version already exists
        existing = self.db.query(DataRelease).filter_by(version=version).first()
        if existing:
            raise ValueError(f"Release version {version} already exists")

        release = DataRelease(version=version, status="draft", release_notes=release_notes)
        self.db.add(release)
        self.db.commit()
        self.db.refresh(release)

        await logger.info("Draft release created", version=version, release_id=release.id)

        return release

    async def publish_release(self, release_id: int, user_id: int) -> DataRelease:
        """
        Publish a release by exporting an immutable snapshot of the current genes.

        This performs the following steps:
        1. Validates release is in draft status
        2. Exports current genes to a JSON file (the release's immutable snapshot)
        3. Calculates SHA256 checksum
        4. Updates release record with metadata

        Live gene rows are not modified: publishing must not retire current genes
        (#288). Release contents are served from the export file.

        Args:
            release_id: ID of release to publish
            user_id: ID of user publishing

        Returns:
            DataRelease: Published release with export metadata

        Raises:
            ValueError: If release not found or already published
        """
        release_result = self.db.query(DataRelease).get(release_id)
        if not release_result:
            raise ValueError(f"Release {release_id} not found")
        release = cast(DataRelease, release_result)

        if release.status == "published":
            raise ValueError(f"Release {release.version} already published")

        await logger.info(
            "Publishing release", version=release.version, release_id=release_id, user_id=user_id
        )

        # Use timezone-aware timestamp
        publish_time = datetime.now(timezone.utc)

        try:
            # Step 1: Export current genes (valid_to = 'infinity')
            loop = asyncio.get_event_loop()
            logger.sync_info(
                "Exporting current genes",
                version=release.version,
                publish_time=publish_time.isoformat(),
            )

            export_path, gene_count = await loop.run_in_executor(
                self._executor, self._export_release_sync, release.version, publish_time
            )

            # Step 2: Calculate checksum in thread pool
            checksum = await loop.run_in_executor(
                self._executor, self._calculate_checksum, export_path
            )

            # Step 2b: Mint DOI via Zenodo (if configured)
            zenodo = self._get_zenodo_service()
            if zenodo:
                try:
                    doi_result = await zenodo.mint_doi_for_release(
                        version=release.version,
                        export_file_path=export_path,
                        gene_count=gene_count,
                        release_notes=release.release_notes or "",
                    )
                    release.doi = doi_result["doi"]
                    release.citation_text = ZenodoService.generate_citation_text(
                        version=release.version,
                        gene_count=gene_count,
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

            # Step 3: Update release record
            release.status = "published"
            release.published_at = publish_time
            release.published_by_id = user_id
            release.export_file_path = str(export_path)
            release.export_checksum = checksum
            release.gene_count = gene_count

            # CRITICAL: Single atomic commit for all operations
            self.db.commit()
            self.db.refresh(release)

            await logger.info(
                "Release published successfully",
                version=release.version,
                gene_count=gene_count,
                checksum=checksum[:16] + "...",
            )

            return release

        except Exception as e:
            # Rollback on any failure to maintain database consistency
            self.db.rollback()
            await logger.error(
                "Release publish failed",
                error=e,
                version=release.version,
                release_id=release_id,
            )
            raise

    def _export_release_sync(self, version: str, timestamp: datetime) -> tuple[Path, int]:
        """
        Export genes to JSON file (sync version for thread pool).

        Exports all genes with valid_to = 'infinity' (current genes).
        Also writes the identifiers-only sidecar served by get_release_genes.

        Args:
            version: Release version
            timestamp: Timestamp for export metadata

        Returns:
            tuple: Path to exported JSON file and number of exported genes
        """
        # Ensure export directory exists
        self.export_dir.mkdir(exist_ok=True, parents=True)
        export_file = self.export_dir / f"kidney-genetics-db_{version}.json"

        logger.sync_info("Exporting release to JSON", version=version, file_path=str(export_file))

        # Query current genes (valid_to = 'infinity') with comprehensive data
        # Includes scores, evidence, and annotations for research reproducibility
        result = self.db.execute(
            text("""
                SELECT
                    g.id,
                    g.approved_symbol,
                    g.hgnc_id,
                    g.aliases,
                    g.valid_from,
                    g.valid_to,
                    -- Gene scores from materialized view
                    gs.raw_score,
                    gs.percentage_score,
                    gs.evidence_tier,
                    gs.evidence_group,
                    gs.source_scores,
                    -- Aggregate evidence from all sources
                    (
                        SELECT jsonb_agg(
                            jsonb_build_object(
                                'source_name', ge.source_name,
                                'source_detail', ge.source_detail,
                                'evidence_data', ge.evidence_data,
                                'evidence_date', ge.evidence_date,
                                'created_at', ge.created_at
                            )
                        )
                        FROM gene_evidence ge
                        WHERE ge.gene_id = g.id
                    ) as evidence,
                    -- Aggregate annotations from all sources
                    (
                        SELECT jsonb_agg(
                            jsonb_build_object(
                                'source', ga.source,
                                'annotations', ga.annotations,
                                'created_at', ga.created_at
                            )
                        )
                        FROM gene_annotations ga
                        WHERE ga.gene_id = g.id
                    ) as annotations
                FROM genes g
                LEFT JOIN gene_scores gs ON g.id = gs.gene_id
                WHERE g.valid_to = 'infinity'::timestamptz
                ORDER BY g.approved_symbol
            """)
        )
        genes = result.fetchall()

        # Build comprehensive export structure
        export_data = {
            "version": version,
            "release_date": timestamp.isoformat(),
            "gene_count": len(genes),
            "metadata": {
                "format": "CalVer",
                "schema_version": "2.0",
                "description": "Kidney Genetics Database - Point-in-time snapshot with comprehensive evidence",
            },
            "genes": [
                {
                    "approved_symbol": row.approved_symbol,
                    "hgnc_id": row.hgnc_id,
                    "aliases": row.aliases,
                    "scores": {
                        "raw_score": float(row.raw_score) if row.raw_score else None,
                        "percentage_score": float(row.percentage_score)
                        if row.percentage_score
                        else None,
                        "evidence_tier": row.evidence_tier,
                        "evidence_group": row.evidence_group,
                        "source_scores": row.source_scores,
                    }
                    if row.raw_score is not None
                    else None,
                    "evidence": row.evidence,
                    "annotations": row.annotations,
                    "temporal": {
                        "valid_from": row.valid_from.isoformat() if row.valid_from else None,
                        "valid_to": row.valid_to.isoformat()
                        if (row.valid_to and str(row.valid_to) != "infinity")
                        else "infinity",
                    },
                }
                for row in genes
            ],
        }

        # Write to file
        with open(export_file, "w", encoding="utf-8") as f:
            json.dump(export_data, f, indent=2, ensure_ascii=False)
        _write_sidecar(export_file, export_data["genes"])

        logger.sync_info(
            "Export completed",
            version=version,
            gene_count=len(genes),
            file_size_bytes=export_file.stat().st_size,
        )

        return export_file, len(genes)

    @staticmethod
    def _calculate_checksum(file_path: str | Path) -> str:
        """
        Calculate SHA256 checksum of file.

        Args:
            file_path: Path to file

        Returns:
            str: Hexadecimal SHA256 checksum
        """
        logger.sync_debug(f"Calculating checksum for {file_path}")

        sha256 = hashlib.sha256()
        with open(file_path, "rb") as f:
            # Read in chunks to handle large files
            for chunk in iter(lambda: f.read(8192), b""):
                sha256.update(chunk)

        checksum = sha256.hexdigest()
        logger.sync_debug(f"Checksum calculated: {checksum[:16]}...")
        return checksum

    async def update_release(
        self, release_id: int, version: str | None = None, release_notes: str | None = None
    ) -> DataRelease:
        """
        Update a draft release.

        Args:
            release_id: ID of release to update
            version: New CalVer version (optional)
            release_notes: New release notes (optional)

        Returns:
            DataRelease: Updated release

        Raises:
            ValueError: If release not found, already published, or version exists
        """
        release_result = self.db.query(DataRelease).get(release_id)
        if not release_result:
            raise ValueError(f"Release {release_id} not found")
        release = cast(DataRelease, release_result)

        if release.status == "published":
            raise ValueError("Cannot update published release")

        await logger.info("Updating draft release", version=release.version, release_id=release_id)

        # Update version if provided and validate uniqueness
        if version is not None and version != release.version:
            # Validate CalVer format
            if not CALVER_PATTERN.match(version):
                raise ValueError(f"Version must be CalVer format YYYY.MM, got: {version}")

            # Check if new version already exists
            existing = self.db.query(DataRelease).filter_by(version=version).first()
            if existing:
                raise ValueError(f"Release version {version} already exists")

            release.version = version

        # Update release notes if provided
        if release_notes is not None:
            release.release_notes = release_notes

        self.db.commit()
        self.db.refresh(release)

        await logger.info("Draft release updated", version=release.version, release_id=release_id)

        return release

    async def delete_release(self, release_id: int) -> None:
        """
        Delete a draft release.

        Args:
            release_id: ID of release to delete

        Raises:
            ValueError: If release not found or already published
        """
        release = self.db.query(DataRelease).get(release_id)
        if not release:
            raise ValueError(f"Release {release_id} not found")

        if release.status == "published":
            raise ValueError(
                "Cannot delete published release - they are immutable for data integrity"
            )

        await logger.info("Deleting draft release", version=release.version, release_id=release_id)

        self.db.delete(release)
        self.db.commit()

        await logger.info("Draft release deleted", version=release.version, release_id=release_id)

    async def get_release_genes(
        self, version: str, limit: int = 100, offset: int = 0
    ) -> dict[str, Any]:
        """
        Get genes from a specific release.

        Args:
            version: Release version
            limit: Maximum genes to return
            offset: Pagination offset

        Returns:
            dict: Release metadata and paginated genes

        Raises:
            ValueError: If release not found or not published
            ReleaseSnapshotError: If the export snapshot is missing or corrupt
        """
        release = self.db.query(DataRelease).filter_by(version=version).first()
        if not release:
            raise ValueError(f"Release {version} not found")

        if release.status != "published":
            raise ValueError(f"Release {version} not published yet")

        if not release.export_file_path:
            raise ReleaseSnapshotError(f"release {version} has no export path")

        # Serve the snapshot written at publish time, not live rows (#288)
        loop = asyncio.get_event_loop()
        genes = await loop.run_in_executor(
            self._executor,
            _load_release_genes,
            release.export_file_path,
            release.export_checksum,
        )

        return {
            "version": version,
            "release_date": release.published_at.isoformat() if release.published_at else None,
            "total": release.gene_count,
            "limit": limit,
            "offset": offset,
            "genes": [dict(gene) for gene in genes[offset : offset + limit]],
        }
