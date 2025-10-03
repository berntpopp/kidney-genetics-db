"""
Backup Service for production-grade PostgreSQL backups

Implements automated database backup and restore with:
- Non-blocking operations using ThreadPoolExecutor
- SHA256 checksum verification
- Flexible options (compression, parallel jobs, table exclusions)
- Safety backups before restore
- Post-restore ANALYZE for query optimizer
"""

import asyncio
import hashlib
import subprocess
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any

from sqlalchemy import text
from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.database import get_thread_pool_executor
from app.core.logging import get_logger
from app.models.backup_job import BackupJob, BackupStatus, BackupTrigger

logger = get_logger(__name__)


class BackupService:
    """Production-grade PostgreSQL backup service"""

    def __init__(self, db_session: Session | None = None):
        self.db = db_session
        self.backup_dir = Path(settings.BACKUP_DIR)
        self.backup_dir.mkdir(parents=True, exist_ok=True)
        # Use singleton thread pool to prevent resource exhaustion
        self._executor = get_thread_pool_executor()

    async def create_backup(
        self,
        user_id: int,
        description: str = "",
        include_logs: bool = False,
        include_cache: bool = False,
        compression_level: int | None = None,
        parallel_jobs: int | None = None,
        trigger_source: BackupTrigger = BackupTrigger.MANUAL_API
    ) -> BackupJob:
        """
        Create a PostgreSQL backup with configurable options.

        Args:
            user_id: ID of user triggering backup
            description: Optional description
            include_logs: Include log tables in backup
            include_cache: Include cache tables in backup
            compression_level: 0-9 (default from settings)
            parallel_jobs: Number of parallel jobs (default from settings)
            trigger_source: How backup was triggered

        Returns:
            BackupJob object with metadata
        """
        compression_level = compression_level or settings.BACKUP_COMPRESSION_LEVEL
        parallel_jobs = parallel_jobs or settings.BACKUP_PARALLEL_JOBS

        # Create backup job record
        timestamp = datetime.now(timezone.utc)
        filename = f"backup_{timestamp.strftime('%Y%m%d_%H%M%S')}.dump"
        file_path = self.backup_dir / filename

        backup_job = BackupJob(
            filename=filename,
            file_path=str(file_path),
            compression_level=compression_level,
            include_logs=include_logs,
            include_cache=include_cache,
            parallel_jobs=parallel_jobs,
            status=BackupStatus.PENDING,
            trigger_source=trigger_source,
            created_by_id=user_id,
            description=description,
            expires_at=timestamp + timedelta(days=settings.BACKUP_RETENTION_DAYS)
        )

        self.db.add(backup_job)
        self.db.commit()
        self.db.refresh(backup_job)

        try:
            # Update status to running
            backup_job.status = BackupStatus.RUNNING
            backup_job.started_at = datetime.now(timezone.utc)
            self.db.commit()

            await logger.info(
                "Starting backup",
                backup_id=backup_job.id,
                filename=filename,
                user_id=user_id
            )

            # Execute pg_dump in thread pool (blocking operation)
            loop = asyncio.get_event_loop()
            await loop.run_in_executor(
                self._executor,
                self._execute_pg_dump,
                backup_job
            )

            # Update job with results
            backup_job.status = BackupStatus.COMPLETED
            backup_job.completed_at = datetime.now(timezone.utc)
            backup_job.duration_seconds = int(
                (backup_job.completed_at - backup_job.started_at).total_seconds()
            )
            backup_job.file_size = file_path.stat().st_size
            backup_job.checksum_sha256 = await loop.run_in_executor(
                self._executor,
                self._calculate_checksum,
                file_path
            )
            # Run database queries in thread pool (non-blocking)
            backup_job.database_size_bytes = await loop.run_in_executor(
                self._executor,
                self._get_database_size
            )
            backup_job.tables_count = await loop.run_in_executor(
                self._executor,
                self._get_table_count
            )

            self.db.commit()

            await logger.info(
                "Backup completed successfully",
                backup_id=backup_job.id,
                file_size_mb=round(backup_job.file_size / (1024 * 1024), 2),
                duration_seconds=backup_job.duration_seconds
            )

            return backup_job

        except Exception as e:
            # Mark as failed
            backup_job.status = BackupStatus.FAILED
            backup_job.completed_at = datetime.now(timezone.utc)
            backup_job.error_message = str(e)
            backup_job.error_details = {"exception_type": type(e).__name__}
            self.db.commit()

            await logger.error(
                "Backup failed",
                backup_id=backup_job.id,
                error=str(e)
            )
            raise

    def _execute_pg_dump(self, backup_job: BackupJob) -> subprocess.CompletedProcess:
        """Execute pg_dump command (sync, runs in thread pool)"""

        # Build pg_dump command - output to stdout for hybrid mode compatibility
        pg_dump_args = [
            "pg_dump",
            "--host=localhost",  # Connect to local postgres in container
            "--port=5432",  # Internal container port
            f"--username={settings.POSTGRES_USER}",
            f"--dbname={settings.POSTGRES_DB}",
            "--format=custom",  # Best for restore flexibility
            f"--compress={backup_job.compression_level}",
            "--verbose",
            "--no-owner",  # Don't dump ownership
            "--no-acl",    # Don't dump access privileges
        ]

        # Note: --jobs (parallel backup) only works with directory format
        # Custom format doesn't support parallel backup, so we don't add --jobs here

        # Exclude tables based on options
        if not backup_job.include_logs:
            pg_dump_args.extend([
                "--exclude-table=system_logs",
            ])
        if not backup_job.include_cache:
            pg_dump_args.extend([
                "--exclude-table=cache_entries",
            ])

        # Use docker exec to run pg_dump inside the container (hybrid mode)
        # Find container name dynamically
        find_container = subprocess.run(
            ["docker", "ps", "--filter", "ancestor=postgres:14-alpine", "--format", "{{.Names}}"],
            capture_output=True,
            text=True
        )

        container_name = find_container.stdout.strip() or "kidney_genetics_postgres"

        # Build full docker exec command with PGPASSWORD environment variable
        # Use -e flag to set environment inside container
        cmd = [
            "docker", "exec", "-i",
            "-e", f"PGPASSWORD={settings.POSTGRES_PASSWORD}",
            container_name
        ] + pg_dump_args

        # Execute command and capture output
        result = subprocess.run(
            cmd,
            capture_output=True,
            timeout=3600  # 1 hour timeout
        )

        if result.returncode != 0:
            error_msg = result.stderr.decode() if isinstance(result.stderr, bytes) else result.stderr
            raise RuntimeError(f"pg_dump failed: {error_msg}")

        # Write the binary output to file
        with open(backup_job.file_path, 'wb') as f:
            f.write(result.stdout)

        return result

    async def restore_backup(
        self,
        backup_id: int,
        user_id: int,
        create_safety_backup: bool = True,
        drop_existing: bool = True,
        run_analyze: bool = True
    ) -> dict[str, Any]:
        """
        Restore database from backup.

        BEST PRACTICE: Always creates safety backup before restore.

        Args:
            backup_id: ID of backup to restore
            user_id: ID of user performing restore
            create_safety_backup: Create safety backup before restore (recommended)
            drop_existing: Drop existing database before restore
            run_analyze: Run ANALYZE after restore (recommended)

        Returns:
            Dictionary with restore results
        """
        backup_job = self.db.query(BackupJob).get(backup_id)
        if not backup_job:
            raise ValueError(f"Backup {backup_id} not found")

        if backup_job.status != BackupStatus.COMPLETED:
            raise ValueError("Can only restore completed backups")

        backup_path = Path(backup_job.file_path)
        if not backup_path.exists():
            raise FileNotFoundError(f"Backup file not found: {backup_path}")

        # Verify checksum
        loop = asyncio.get_event_loop()
        actual_checksum = await loop.run_in_executor(
            self._executor,
            self._calculate_checksum,
            backup_path
        )
        if actual_checksum != backup_job.checksum_sha256:
            raise ValueError("Backup file checksum mismatch - file may be corrupted")

        await logger.warning(
            "Starting database restore",
            backup_id=backup_id,
            user_id=user_id,
            create_safety_backup=create_safety_backup
        )

        safety_backup_job = None
        try:
            # Create safety backup
            if create_safety_backup:
                await logger.info("Creating safety backup before restore")
                safety_backup_job = await self.create_backup(
                    user_id=user_id,
                    description=f"Safety backup before restoring backup {backup_id}",
                    trigger_source=BackupTrigger.PRE_RESTORE_SAFETY
                )

            # Execute restore in thread pool
            start_time = datetime.now(timezone.utc)

            await loop.run_in_executor(
                self._executor,
                self._execute_pg_restore,
                backup_job,
                drop_existing
            )

            # Run ANALYZE for query optimizer (BEST PRACTICE)
            if run_analyze:
                await logger.info("Running ANALYZE on restored database")
                await loop.run_in_executor(self._executor, self._run_analyze)

            # Mark backup as restored
            backup_job.status = BackupStatus.RESTORED
            self.db.commit()

            duration = (datetime.now(timezone.utc) - start_time).total_seconds()

            await logger.info(
                "Database restore completed",
                backup_id=backup_id,
                duration_seconds=duration,
                safety_backup_id=safety_backup_job.id if safety_backup_job else None
            )

            return {
                "success": True,
                "backup_id": backup_id,
                "duration_seconds": duration,
                "safety_backup_id": safety_backup_job.id if safety_backup_job else None,
                "analyzed": run_analyze
            }

        except Exception as e:
            await logger.error(
                "Database restore failed",
                backup_id=backup_id,
                error=str(e),
                safety_backup_id=safety_backup_job.id if safety_backup_job else None
            )
            raise

    def _execute_pg_restore(
        self,
        backup_job: BackupJob,
        drop_existing: bool
    ) -> subprocess.CompletedProcess:
        """Execute pg_restore command (sync, runs in thread pool)"""

        if drop_existing:
            # Drop and recreate database
            self._recreate_database()

        # Build pg_restore command - read from stdin for hybrid mode compatibility
        pg_restore_args = [
            "pg_restore",
            "--host=localhost",  # Connect to local postgres in container
            "--port=5432",  # Internal container port
            f"--username={settings.POSTGRES_USER}",
            f"--dbname={settings.POSTGRES_DB}",
            "--verbose",
            "--no-owner",
            "--no-acl",
        ]

        # Add parallel jobs for faster restore
        if backup_job.parallel_jobs > 1:
            pg_restore_args.append(f"--jobs={backup_job.parallel_jobs}")

        # Find container dynamically
        find_container = subprocess.run(
            ["docker", "ps", "--filter", "ancestor=postgres:14-alpine", "--format", "{{.Names}}"],
            capture_output=True,
            text=True
        )
        container_name = find_container.stdout.strip() or "kidney_genetics_postgres"

        # Use docker exec to run pg_restore inside the container with PGPASSWORD
        cmd = [
            "docker", "exec", "-i",
            "-e", f"PGPASSWORD={settings.POSTGRES_PASSWORD}",
            container_name
        ] + pg_restore_args

        # Read backup file and pipe to pg_restore via stdin
        with open(backup_job.file_path, 'rb') as backup_file:
            result = subprocess.run(
                cmd,
                stdin=backup_file,
                capture_output=True,
                text=True,
                timeout=7200  # 2 hour timeout
            )

        if result.returncode != 0:
            raise RuntimeError(f"pg_restore failed: {result.stderr}")

        return result

    def _recreate_database(self):
        """Drop and recreate database (for hybrid mode via docker exec)"""
        # Find container dynamically
        find_container = subprocess.run(
            ["docker", "ps", "--filter", "ancestor=postgres:14-alpine", "--format", "{{.Names}}"],
            capture_output=True,
            text=True
        )
        container_name = find_container.stdout.strip() or "kidney_genetics_postgres"

        # Build psql commands for internal container connection
        psql_drop_args = [
            "psql",
            "--host=localhost",
            "--port=5432",
            f"--username={settings.POSTGRES_USER}",
            "--dbname=postgres",
            "-c", f"DROP DATABASE IF EXISTS {settings.POSTGRES_DB};"
        ]

        psql_create_args = [
            "psql",
            "--host=localhost",
            "--port=5432",
            f"--username={settings.POSTGRES_USER}",
            "--dbname=postgres",
            "-c", f"CREATE DATABASE {settings.POSTGRES_DB};"
        ]

        # Execute via docker exec with PGPASSWORD
        cmd_drop = [
            "docker", "exec", "-i",
            "-e", f"PGPASSWORD={settings.POSTGRES_PASSWORD}",
            container_name
        ] + psql_drop_args

        cmd_create = [
            "docker", "exec", "-i",
            "-e", f"PGPASSWORD={settings.POSTGRES_PASSWORD}",
            container_name
        ] + psql_create_args

        subprocess.run(cmd_drop, check=True, capture_output=True)
        subprocess.run(cmd_create, check=True, capture_output=True)

    def _run_analyze(self):
        """Run ANALYZE on all tables (BEST PRACTICE after restore)"""
        # Find container dynamically
        find_container = subprocess.run(
            ["docker", "ps", "--filter", "ancestor=postgres:14-alpine", "--format", "{{.Names}}"],
            capture_output=True,
            text=True
        )
        container_name = find_container.stdout.strip() or "kidney_genetics_postgres"

        # Build psql command for internal container connection
        psql_args = [
            "psql",
            "--host=localhost",
            "--port=5432",
            f"--username={settings.POSTGRES_USER}",
            f"--dbname={settings.POSTGRES_DB}",
            "-c", "ANALYZE;"
        ]

        # Execute via docker exec with PGPASSWORD
        cmd = [
            "docker", "exec", "-i",
            "-e", f"PGPASSWORD={settings.POSTGRES_PASSWORD}",
            container_name
        ] + psql_args
        subprocess.run(cmd, check=True, capture_output=True)

    def _calculate_checksum(self, file_path: Path) -> str:
        """Calculate SHA256 checksum of file"""
        sha256 = hashlib.sha256()
        with open(file_path, 'rb') as f:
            for chunk in iter(lambda: f.read(8192), b""):
                sha256.update(chunk)
        return sha256.hexdigest()

    def _get_database_size(self) -> int:
        """Get current database size in bytes"""
        result = self.db.execute(
            text("SELECT pg_database_size(:dbname)"),
            {"dbname": settings.POSTGRES_DB}
        )
        return result.scalar() or 0

    def _get_table_count(self) -> int:
        """Get count of tables in database"""
        result = self.db.execute(text(
            "SELECT COUNT(*) FROM information_schema.tables "
            "WHERE table_schema = 'public'"
        ))
        return result.scalar() or 0

    def _cleanup_old_backups_sync(self) -> int:
        """Delete backups older than retention period (sync for thread pool)"""
        cutoff_date = datetime.now(timezone.utc) - timedelta(days=settings.BACKUP_RETENTION_DAYS)

        old_backups = self.db.query(BackupJob).filter(
            BackupJob.status == BackupStatus.COMPLETED,
            BackupJob.expires_at < cutoff_date
        ).all()

        deleted_count = 0
        for backup in old_backups:
            try:
                # Delete file
                file_path = Path(backup.file_path)
                if file_path.exists():
                    file_path.unlink()

                # Delete database record
                self.db.delete(backup)
                deleted_count += 1

                logger.sync_info(
                    "Deleted expired backup",
                    backup_id=backup.id,
                    filename=backup.filename
                )
            except Exception as e:
                logger.sync_error(
                    "Failed to delete backup",
                    backup_id=backup.id,
                    error=str(e)
                )

        self.db.commit()
        return deleted_count

    async def cleanup_old_backups(self) -> int:
        """Delete backups older than retention period (non-blocking)"""
        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(
            self._executor,
            self._cleanup_old_backups_sync
        )

    def _list_backups_sync(
        self,
        limit: int = 50,
        status: BackupStatus | None = None
    ) -> list[BackupJob]:
        """List backups with optional filtering (sync for thread pool)"""
        query = self.db.query(BackupJob).order_by(BackupJob.created_at.desc())

        if status:
            query = query.filter(BackupJob.status == status)

        return query.limit(limit).all()

    async def list_backups(
        self,
        limit: int = 50,
        status: BackupStatus | None = None
    ) -> list[BackupJob]:
        """List backups with optional filtering (non-blocking)"""
        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(
            self._executor,
            self._list_backups_sync,
            limit,
            status
        )

    def _get_backup_stats_sync(self) -> dict[str, Any]:
        """Get backup statistics (sync method for thread pool)"""
        total_backups = self.db.query(BackupJob).count()
        completed_backups = self.db.query(BackupJob).filter(
            BackupJob.status == BackupStatus.COMPLETED
        ).count()

        # Total backup storage used
        total_size = self.db.execute(text(
            "SELECT COALESCE(SUM(file_size), 0) FROM backup_jobs WHERE status = 'COMPLETED'"
        )).scalar() or 0

        # Latest successful backup
        latest_backup = self.db.query(BackupJob).filter(
            BackupJob.status == BackupStatus.COMPLETED
        ).order_by(BackupJob.completed_at.desc()).first()

        return {
            "total_backups": total_backups,
            "completed_backups": completed_backups,
            "total_size_gb": round(total_size / (1024**3), 2),
            "latest_backup_date": latest_backup.completed_at if latest_backup else None,
            "retention_days": settings.BACKUP_RETENTION_DAYS,
            "backup_directory": str(self.backup_dir)
        }

    async def get_backup_stats(self) -> dict[str, Any]:
        """Get backup statistics (non-blocking)"""
        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(
            self._executor,
            self._get_backup_stats_sync
        )

    def _delete_backup_sync(self, backup_id: int, filename: str) -> None:
        """Delete backup file and record (sync for thread pool)"""
        backup_job = self.db.query(BackupJob).get(backup_id)
        if not backup_job:
            raise ValueError(f"Backup {backup_id} not found")

        # Delete file
        file_path = Path(backup_job.file_path)
        if file_path.exists():
            file_path.unlink()

        # Delete record
        self.db.delete(backup_job)
        self.db.commit()

        logger.sync_info(
            "Deleted backup",
            backup_id=backup_id,
            filename=filename
        )

    async def delete_backup(self, backup_id: int) -> bool:
        """Delete a specific backup by ID (non-blocking)"""
        # Get filename before deletion
        backup_job = self.db.query(BackupJob).get(backup_id)
        if not backup_job:
            raise ValueError(f"Backup {backup_id} not found")

        filename = backup_job.filename

        loop = asyncio.get_event_loop()
        await loop.run_in_executor(
            self._executor,
            self._delete_backup_sync,
            backup_id,
            filename
        )

        return True
