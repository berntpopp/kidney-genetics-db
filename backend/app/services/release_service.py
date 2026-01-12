"""
Release Service for CalVer data releases

Handles creating and publishing versioned data snapshots with temporal database queries.
"""

import asyncio
import hashlib
import json
import re
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, cast

from sqlalchemy import text
from sqlalchemy.orm import Session

from app.core.database import get_thread_pool_executor
from app.core.logging import get_logger
from app.models.data_release import DataRelease

logger = get_logger(__name__)

# CalVer validation pattern (YYYY.MM format)
CALVER_PATTERN = re.compile(r'^\d{4}\.\d{1,2}$')


class ReleaseService:
    """
    Service for managing CalVer data releases.

    Features:
    - Thread pool for non-blocking file I/O
    - Timezone-aware temporal queries
    - Automatic checksum calculation
    - Export to JSON with metadata
    """

    def __init__(self, db_session: Session):
        self.db: Session = db_session
        self._executor = get_thread_pool_executor()
        self.export_dir = Path("exports")

    async def create_release(
        self,
        version: str,
        user_id: int,
        release_notes: str = ""
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
        await logger.info(
            "Creating draft release",
            version=version,
            user_id=user_id
        )

        # Validate CalVer format
        if not CALVER_PATTERN.match(version):
            raise ValueError(f"Version must be CalVer format YYYY.MM, got: {version}")

        # Check if version already exists
        existing = self.db.query(DataRelease).filter_by(version=version).first()
        if existing:
            raise ValueError(f"Release version {version} already exists")

        release = DataRelease(
            version=version,
            status="draft",
            release_notes=release_notes
        )
        self.db.add(release)
        self.db.commit()
        self.db.refresh(release)

        await logger.info(
            "Draft release created",
            version=version,
            release_id=release.id
        )

        return release

    async def publish_release(
        self,
        release_id: int,
        user_id: int
    ) -> DataRelease:
        """
        Publish a release by closing temporal ranges and exporting data.

        This performs the following steps:
        1. Validates release is in draft status
        2. Closes all current gene temporal ranges (sets valid_to)
        3. Exports genes to JSON file
        4. Calculates SHA256 checksum
        5. Updates release record with metadata

        All operations are wrapped in a single transaction for atomicity.

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
            "Publishing release",
            version=release.version,
            release_id=release_id,
            user_id=user_id
        )

        # Use timezone-aware timestamp
        publish_time = datetime.now(timezone.utc)

        try:
            # Step 1: Export current genes BEFORE closing ranges
            # This ensures we capture all genes with valid_to = 'infinity'
            loop = asyncio.get_event_loop()
            logger.sync_info(
                "Exporting current genes",
                version=release.version,
                publish_time=publish_time.isoformat()
            )

            export_path = await loop.run_in_executor(
                self._executor,
                self._export_release_sync,
                release.version,
                publish_time
            )

            # Step 2: Calculate checksum in thread pool
            checksum = await loop.run_in_executor(
                self._executor,
                self._calculate_checksum,
                export_path
            )

            # Step 3: Count genes before closing (still at infinity)
            gene_count = self._count_genes_current()

            # Step 4: Now close temporal ranges (NO COMMIT YET)
            logger.sync_info(
                "Closing temporal ranges",
                version=release.version,
                publish_time=publish_time.isoformat(),
                gene_count=gene_count
            )

            self.db.execute(
                text("""
                    UPDATE genes
                    SET valid_to = :publish_time
                    WHERE valid_to = 'infinity'::timestamptz
                """),
                {"publish_time": publish_time}
            )

            # Step 5: Update release record
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
                checksum=checksum[:16] + "..."
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

    def _export_release_sync(self, version: str, timestamp: datetime) -> Path:
        """
        Export genes to JSON file (sync version for thread pool).

        Exports all genes with valid_to = 'infinity' (current genes).
        This method is called BEFORE closing temporal ranges.

        Args:
            version: Release version
            timestamp: Timestamp for export metadata

        Returns:
            Path: Path to exported JSON file
        """
        # Ensure export directory exists
        self.export_dir.mkdir(exist_ok=True, parents=True)
        export_file = self.export_dir / f"kidney-genetics-db_{version}.json"

        logger.sync_info(
            "Exporting release to JSON",
            version=version,
            file_path=str(export_file)
        )

        # Query current genes (valid_to = 'infinity') with comprehensive data
        # This is called BEFORE we close the temporal ranges
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
                "description": "Kidney Genetics Database - Point-in-time snapshot with comprehensive evidence"
            },
            "genes": [
                {
                    "approved_symbol": row.approved_symbol,
                    "hgnc_id": row.hgnc_id,
                    "aliases": row.aliases,
                    "scores": {
                        "raw_score": float(row.raw_score) if row.raw_score else None,
                        "percentage_score": float(row.percentage_score) if row.percentage_score else None,
                        "evidence_tier": row.evidence_tier,
                        "evidence_group": row.evidence_group,
                        "source_scores": row.source_scores
                    } if row.raw_score is not None else None,
                    "evidence": row.evidence,
                    "annotations": row.annotations,
                    "temporal": {
                        "valid_from": row.valid_from.isoformat() if row.valid_from else None,
                        "valid_to": row.valid_to.isoformat() if (row.valid_to and str(row.valid_to) != "infinity") else "infinity"
                    }
                }
                for row in genes
            ]
        }

        # Write to file
        with open(export_file, 'w', encoding='utf-8') as f:
            json.dump(export_data, f, indent=2, ensure_ascii=False)

        logger.sync_info(
            "Export completed",
            version=version,
            gene_count=len(genes),
            file_size_bytes=export_file.stat().st_size
        )

        return export_file

    def _calculate_checksum(self, file_path: Path) -> str:
        """
        Calculate SHA256 checksum of file.

        Args:
            file_path: Path to file

        Returns:
            str: Hexadecimal SHA256 checksum
        """
        logger.sync_debug(f"Calculating checksum for {file_path}")

        sha256 = hashlib.sha256()
        with open(file_path, 'rb') as f:
            # Read in chunks to handle large files
            for chunk in iter(lambda: f.read(8192), b""):
                sha256.update(chunk)

        checksum = sha256.hexdigest()
        logger.sync_debug(f"Checksum calculated: {checksum[:16]}...")
        return checksum

    def _count_genes_current(self) -> int:
        """
        Count current genes (valid_to = 'infinity').

        Called before closing temporal ranges during publish.

        Returns:
            int: Number of current genes
        """
        result = self.db.execute(
            text("""
                SELECT COUNT(*)
                FROM genes
                WHERE valid_to = 'infinity'::timestamptz
            """)
        )
        count = result.scalar()
        return int(count) if count is not None else 0

    def _count_genes(self, timestamp: datetime) -> int:
        """
        Count genes at specific timestamp.

        Args:
            timestamp: Point-in-time for temporal query

        Returns:
            int: Number of genes valid at timestamp
        """
        result = self.db.execute(
            text("""
                SELECT COUNT(*)
                FROM genes
                WHERE tstzrange(valid_from, valid_to) @> :timestamp
            """),
            {"timestamp": timestamp}
        )
        count = result.scalar()
        return int(count) if count is not None else 0

    async def update_release(
        self,
        release_id: int,
        version: str | None = None,
        release_notes: str | None = None
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

        await logger.info(
            "Updating draft release",
            version=release.version,
            release_id=release_id
        )

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

        await logger.info(
            "Draft release updated",
            version=release.version,
            release_id=release_id
        )

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
            raise ValueError("Cannot delete published release - they are immutable for data integrity")

        await logger.info(
            "Deleting draft release",
            version=release.version,
            release_id=release_id
        )

        self.db.delete(release)
        self.db.commit()

        await logger.info(
            "Draft release deleted",
            version=release.version,
            release_id=release_id
        )

    async def get_release_genes(
        self,
        version: str,
        limit: int = 100,
        offset: int = 0
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
            ValueError: If release not found
        """
        release = self.db.query(DataRelease).filter_by(version=version).first()
        if not release:
            raise ValueError(f"Release {version} not found")

        if release.status != "published":
            raise ValueError(f"Release {version} not published yet")

        # Query genes at release timestamp
        result = self.db.execute(
            text("""
                SELECT
                    approved_symbol,
                    hgnc_id,
                    aliases
                FROM genes
                WHERE tstzrange(valid_from, valid_to) @> :timestamp
                ORDER BY approved_symbol
                LIMIT :limit OFFSET :offset
            """),
            {
                "timestamp": release.published_at,
                "limit": limit,
                "offset": offset
            }
        )
        genes = result.fetchall()

        return {
            "version": version,
            "release_date": release.published_at.isoformat() if release.published_at else None,
            "total": release.gene_count,
            "limit": limit,
            "offset": offset,
            "genes": [
                {
                    "approved_symbol": row.approved_symbol,
                    "hgnc_id": row.hgnc_id,
                    "aliases": row.aliases
                }
                for row in genes
            ]
        }
